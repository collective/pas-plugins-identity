"""The Bearer plugin.

This is what makes a token worth issuing: until it landed, the flow ran end
to end and the thing it produced authenticated nothing.

Two halves, tested apart. Extraction runs on *every* request in the site, so
its tests are mostly about what it declines to do -- no parsing, no
cryptography, no work at all for a request that carries no token.
Authentication is where the refusals live, and there are more of them than the
signature check alone would suggest.
"""

from . import PROFILE_ID
from pas.plugins.identity.server.controlpanel.clients import get_clients
from pas.plugins.identity.server.controlpanel.clients import remove_client
from pas.plugins.identity.server.controlpanel.clients import set_clients
from pas.plugins.identity.server.grants.tokens import ISSUER_RECORD
from pas.plugins.identity.server.grants.tokens import mint_access_token
from pas.plugins.identity.server.pas import PLUGIN_ID
from plone import api

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])

ISSUER = "https://id.example.org"
USERID = "alice"


@pytest.fixture
def plugin(portal):
    """The server plugin, which is also the Bearer plugin."""
    return portal.acl_users[PLUGIN_ID]


@pytest.fixture
def issuer(portal):
    """Configure the issuer, without which nothing can be signed."""
    api.portal.set_registry_record(ISSUER_RECORD, ISSUER)
    return ISSUER


@pytest.fixture
def user(portal):
    """A real Plone user for tokens to name."""
    with api.env.adopt_roles(["Manager"]):
        return api.user.create(
            email="alice@example.org",
            username=USERID,
            password="irrelevant-to-a-token",
        )


@pytest.fixture
def client(portal, issuer, add_client):
    """An enabled client for tokens to be addressed to."""
    client, _secret = add_client("app", scope="read", public=False)
    return client


@pytest.fixture
def token(portal, client, user) -> str:
    """A live token for ``alice``, addressed to ``app``."""
    encoded, _ttl = mint_access_token("app", USERID, scope="read")
    return encoded


def credentials(plugin, header: str):
    """Extract credentials from a request carrying an Authorization header.

    :param plugin: The Bearer plugin.
    :param header: The raw header value.
    :returns: The extracted credentials mapping.
    """
    request = plugin.REQUEST
    request._auth = header
    return plugin.extractCredentials(request)


class TestExtraction:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin, token) -> None:
        self.portal = portal
        self.plugin = plugin
        self.token = token

    def test_a_bearer_token_is_extracted(self):
        assert credentials(self.plugin, f"Bearer {self.token}") == {
            "extractor": PLUGIN_ID,
            "token": self.token,
        }

    def test_the_scheme_is_case_insensitive(self):
        """RFC 7235 makes it so, and real clients do send `bearer`."""
        assert credentials(self.plugin, f"bearer {self.token}")["token"] == self.token

    def test_no_header_extracts_nothing(self):
        """The ordinary request. This is the path every request in the site
        takes, and it has to stay a lookup and a prefix test."""
        request = self.plugin.REQUEST
        request._auth = None

        assert self.plugin.extractCredentials(request) == {}

    def test_basic_auth_is_left_alone(self):
        """Somebody else's credentials, and not this plugin's business."""
        assert credentials(self.plugin, "Basic YWxpY2U6c2VjcmV0") == {}

    def test_an_empty_token_extracts_nothing(self):
        """`Authorization: Bearer` with nothing after it. Returning a blank
        token would send an empty string through the signature check for no
        reason."""
        assert credentials(self.plugin, "Bearer   ") == {}

    def test_extraction_does_not_validate(self):
        """Deliberately: a request carrying rubbish still extracts, and is
        refused at authentication. Doing the work here would put a signature
        check on every request that names the scheme."""
        assert credentials(self.plugin, "Bearer not-a-jwt")["token"] == "not-a-jwt"


class TestAuthentication:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin, token, user) -> None:
        self.portal = portal
        self.plugin = plugin
        self.token = token

    def authenticate(self, token: str = "", **overrides):
        """Authenticate a token as PAS would present it.

        :param token: The token; the fixture's live one by default.
        :param overrides: Credential keys to replace.
        :returns: The plugin's answer.
        """
        creds = {"extractor": PLUGIN_ID, "token": token or self.token}
        creds.update(overrides)
        return self.plugin.authenticateCredentials(creds)

    def test_a_live_token_authenticates_its_subject(self):
        assert self.authenticate() == (USERID, USERID)

    def test_another_extractors_credentials_are_ignored(self):
        """Plone's own `jwt_auth` reads the same header, so both plugins see
        both sets of credentials and each has to recognise its own."""
        assert self.authenticate(extractor="jwt_auth") is None

    def test_garbage_is_refused(self):
        assert self.authenticate("not-a-jwt") is None

    def test_an_expired_token_is_refused(self):
        expired, _ttl = mint_access_token("app", USERID, ttl=-1)

        assert self.authenticate(expired) is None

    def test_a_token_from_another_issuer_is_refused(self):
        """The site was renamed after the token was minted, or the token came
        from somewhere else entirely. Same answer either way."""
        api.portal.set_registry_record(ISSUER_RECORD, "https://elsewhere.example.org")

        assert self.authenticate() is None

    def test_a_token_for_a_removed_client_is_refused(self):
        """With no denylist (D3), unregistering the client is the only
        revocation this server has. The signature is still perfectly good."""
        remove_client("app")

        assert self.authenticate() is None

    def test_a_token_for_a_disabled_client_is_refused(self):
        """Same reasoning, without throwing the registration away."""
        clients = get_clients()
        for client in clients:
            client.enabled = False
        set_clients(clients)

        assert self.authenticate() is None

    def test_a_token_for_a_deleted_user_is_refused(self):
        """Authenticating them anyway would put a principal on the request
        that no roles plugin has ever heard of."""
        with api.env.adopt_roles(["Manager"]):
            api.user.delete(username=USERID)

        assert self.authenticate() is None

    def test_a_token_with_no_subject_is_refused(self):
        """Not reachable through this server's own minting, which always sets
        one -- but the plugin is what stands between a token and a session,
        and it does not get to assume the token came from here."""
        from authlib.jose import JsonWebToken
        from pas.plugins.identity.server.utils.keys import ALGORITHM
        from pas.plugins.identity.server.utils.keys import current_key

        key = current_key()
        forged = (
            JsonWebToken([ALGORITHM])
            .encode(
                {"alg": ALGORITHM, "kid": key["kid"], "typ": "at+jwt"},
                {"iss": ISSUER, "aud": "app", "exp": 9999999999},
                key,
            )
            .decode("ascii")
        )

        assert self.authenticate(forged) is None
