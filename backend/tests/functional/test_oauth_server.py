"""Plone as an authorization server, driven by a third-party OAuth client.

The gate S1 check. Every other test of the ``[server]`` layer is this package
talking to itself: the requests are built by tests that were written against
the same reading of RFC 6749 as the endpoints, so the two agree about things
neither of them has any right to assume.

Here the client is `authlib`'s own ``OAuth2Session`` -- the same library
`pas.plugins.identity` uses when it is the *relying party*, but used here from
the other side, and it has never heard of this package. It builds the
authorization URL, generates the PKCE verifier, chooses the ``state``, posts
the token request, and parses the response. Everything it does is what a real
integrator's client would do; the test only supplies the browser in the
middle, because a redirect to a browser is the one thing a library cannot do
for itself.

No Docker here. Dex is a *provider* and is the right shape for testing this
package as a client; there is no equivalent container to point at Plone as a
server until the discovery document lands in Gate S2 and `oauth2-proxy`
becomes configurable without hand-wiring every endpoint. An off-the-shelf
client library is what the plan names as the alternative, and it is a real
one.
"""

from authlib.integrations.requests_client import OAuth2Session
from authlib.jose import JsonWebKey
from authlib.jose import JsonWebToken
from authlib.oidc.discovery import OpenIDProviderMetadata
from bs4 import BeautifulSoup
from pas.plugins.identity import PACKAGE_NAME
from pas.plugins.identity.server.controlpanel.clients import add_client
from pas.plugins.identity.server.grants.tokens import decode_access_token
from pas.plugins.identity.server.grants.tokens import ISSUER_RECORD
from plone import api
from plone.app.testing import applyProfile
from urllib.parse import parse_qs
from urllib.parse import urlparse

import pytest
import requests
import transaction


#: Nothing serves this. The test reads the code straight off the redirect the
#: way a real client's callback route would, which is also how the Dex-facing
#: flow tests treat the frontend callback URL.
CALLBACK = "https://rp.example.org/callback"

END_USER = "elena"
END_USER_PASSWORD = "a-password-for-the-browser"
SCOPE = "openid profile email"


@pytest.fixture
def server(functional):
    """A Plone site acting as an authorization server, with one client.

    :param functional: The functional layer.
    :returns: Mapping of the portal URL and the registered client's secret.
    """
    portal = functional["portal"]
    applyProfile(portal, f"{PACKAGE_NAME}.server:default")
    api.portal.set_registry_record(ISSUER_RECORD, portal.absolute_url())
    with api.env.adopt_roles(["Manager"]):
        api.user.create(
            email="elena@example.org",
            username=END_USER,
            password=END_USER_PASSWORD,
            properties={"fullname": "Elena Example"},
        )
    _client, secret = add_client(
        "third-party-app",
        title="A Third-Party App",
        redirect_uris=[CALLBACK],
        grant_types=["authorization_code", "refresh_token"],
        scope=SCOPE,
        public=False,
    )
    transaction.commit()
    return {"url": portal.absolute_url(), "secret": secret}


@pytest.fixture
def rp(server) -> OAuth2Session:
    """Return authlib's OAuth client, configured for our server.

    :param server: The authorization server.
    :returns: An ``OAuth2Session`` that knows nothing about this package.
    """
    return OAuth2Session(
        client_id="third-party-app",
        client_secret=server["secret"],
        redirect_uri=CALLBACK,
        scope=SCOPE,
        token_endpoint_auth_method="client_secret_post",
        code_challenge_method="S256",
    )


def consent(browser: requests.Session, authorize_url: str) -> dict[str, str]:
    """Play the browser: log in, read the consent form, click Allow.

    Nothing here is OAuth. It is the part of the flow a human performs, and
    the test performs it exactly as written on the page -- the form's own
    action, its own hidden fields, its own CSRF token -- so a template that
    stops carrying something fails here rather than being papered over.

    :param browser: A session authenticated as the end user.
    :param authorize_url: Where authlib says to send the browser.
    :returns: The query parameters of the redirect back to the callback.
    :raises AssertionError: When the server does not present a consent form,
        or does not come back to the registered callback.
    """
    page = browser.get(authorize_url, timeout=30)
    page.raise_for_status()

    form = BeautifulSoup(page.text, "html.parser").find("form")
    assert form is not None, f"No consent form; the server answered:\n{page.text[:400]}"
    fields = {
        field["name"]: field.get("value", "")
        for field in form.find_all("input", attrs={"type": "hidden"})
    }

    response = browser.post(
        form["action"],
        data={**fields, "consent": "allow"},
        allow_redirects=False,
        timeout=30,
    )
    location = response.headers.get("Location")
    assert location, f"Consent did not redirect; it answered {response.status_code}"
    assert location.startswith(CALLBACK), f"Redirected to {location}, not the callback"
    return {k: v[0] for k, v in parse_qs(urlparse(location).query).items()}


class TestAThirdPartyClientCompletesTheFlow:
    @pytest.fixture(autouse=True)
    def _setup(self, server, rp) -> None:
        self.url = server["url"]
        self.rp = rp
        self.browser = requests.Session()
        self.browser.auth = (END_USER, END_USER_PASSWORD)

    def authorize(self) -> tuple[dict[str, str], str, str]:
        """Run the authorization half of the flow.

        :returns: The callback query, the state authlib chose, and the PKCE
            verifier it generated.
        """
        verifier = "a-verifier-long-enough-to-satisfy-rfc-7636-minimums"
        url, state = self.rp.create_authorization_url(
            f"{self.url}/@@oauth-authorize",
            code_verifier=verifier,
        )
        return consent(self.browser, url), state, verifier

    def test_the_client_gets_a_code_back(self):
        query, state, _verifier = self.authorize()

        assert query["code"]
        assert query["state"] == state, "authlib's state did not survive the round trip"

    def test_the_client_redeems_the_code_for_a_token(self):
        """authlib posts the token request and parses the response. If this
        server's body were malformed, or the token type spelled differently,
        this is where a real integration would break."""
        query, _state, verifier = self.authorize()

        token = self.rp.fetch_token(
            f"{self.url}/@@oauth-token",
            code=query["code"],
            code_verifier=verifier,
        )

        assert token["token_type"] == "Bearer"
        assert token["expires_in"] > 0

    def test_the_token_speaks_for_the_user_who_consented(self):
        query, _state, verifier = self.authorize()

        token = self.rp.fetch_token(
            f"{self.url}/@@oauth-token",
            code=query["code"],
            code_verifier=verifier,
        )

        assert decode_access_token(token["access_token"])["sub"] == END_USER

    def test_the_token_authenticates_a_request_to_plone(self):
        """The end of the line: a third-party client holding nothing but a
        token it obtained itself reads Plone as the user who consented."""
        query, _state, verifier = self.authorize()
        self.rp.fetch_token(
            f"{self.url}/@@oauth-token",
            code=query["code"],
            code_verifier=verifier,
        )

        # authlib attaches the token itself, which is the point of asking it
        # rather than setting the header by hand.
        response = self.rp.get(
            f"{self.url}/@users/{END_USER}",
            headers={"Accept": "application/json"},
            timeout=30,
        )

        assert response.status_code == 200
        assert response.json()["id"] == END_USER

    def test_the_code_cannot_be_redeemed_twice(self):
        """Through a real client, so the refusal is one an integrator would
        actually see rather than one the test constructed."""
        query, _state, verifier = self.authorize()
        self.rp.fetch_token(
            f"{self.url}/@@oauth-token",
            code=query["code"],
            code_verifier=verifier,
        )

        with pytest.raises(Exception, match="invalid_grant"):
            OAuth2Session(
                client_id=self.rp.client_id,
                client_secret=self.rp.client_secret,
                redirect_uri=CALLBACK,
                token_endpoint_auth_method="client_secret_post",
            ).fetch_token(
                f"{self.url}/@@oauth-token",
                code=query["code"],
                code_verifier=verifier,
            )

    def test_the_second_authorization_is_silent(self):
        """Consent was recorded, so the same client asking for the same scope
        again gets a code without troubling the user. Without this the
        consent screen would appear on every login through the client, which
        is what having a session at the authorization server is meant to
        avoid."""
        self.authorize()

        url, _state = self.rp.create_authorization_url(
            f"{self.url}/@@oauth-authorize",
            code_verifier="another-verifier-long-enough-for-rfc-7636-limits",
        )
        response = self.browser.get(url, allow_redirects=False, timeout=30)

        assert response.status_code == 302
        assert "code=" in response.headers["Location"]


class TestDiscovery:
    """The Gate S2 check: an off-the-shelf OIDC client is given an issuer URL
    and nothing else, and everything it needs follows from that."""

    @pytest.fixture(autouse=True)
    def _setup(self, server, rp) -> None:
        self.url = server["url"]
        self.rp = rp
        self.browser = requests.Session()
        self.browser.auth = (END_USER, END_USER_PASSWORD)

    def discover(self) -> dict:
        """Fetch and validate the discovery document, as a client does.

        :returns: The provider metadata.
        """
        response = requests.get(
            f"{self.url}/.well-known/openid-configuration", timeout=30
        )
        response.raise_for_status()
        document = response.json()
        # authlib's own validator, not our assertions: it enforces the
        # required members and their types the way a conforming client would
        # before trusting any of them.
        OpenIDProviderMetadata(document).validate()
        return document

    def test_the_document_is_published_and_valid(self):
        assert self.discover()["issuer"] == self.url

    def test_the_issuer_matches_where_it_was_fetched_from(self):
        """A conforming client compares these byte for byte and refuses the
        document when they differ, which is what makes the configured issuer
        (rather than a derived portal URL) load-bearing."""
        document = self.discover()

        assert document["issuer"] == self.url

    def test_the_advertised_jwks_serves_the_signing_keys(self):
        keys = requests.get(self.discover()["jwks_uri"], timeout=30).json()

        assert keys["keys"]
        assert "d" not in keys["keys"][0], "a private key reached the JWKS"

    def test_a_client_validates_the_id_token_through_discovery_alone(self):
        """The whole gate in one test. Nothing here is configured by hand:
        the endpoints, the keys and the algorithm all come from the document,
        and the token is validated with the keys it pointed at."""
        document = self.discover()
        jwks = requests.get(document["jwks_uri"], timeout=30).json()
        nonce = "a-nonce-the-client-chose"

        url, _state = self.rp.create_authorization_url(
            document["authorization_endpoint"],
            code_verifier="a-verifier-long-enough-to-satisfy-rfc-7636-minimums",
            nonce=nonce,
        )
        query = consent(self.browser, url)
        token = self.rp.fetch_token(
            document["token_endpoint"],
            code=query["code"],
            code_verifier="a-verifier-long-enough-to-satisfy-rfc-7636-minimums",
        )

        claims = JsonWebToken(document["id_token_signing_alg_values_supported"]).decode(
            token["id_token"],
            key=JsonWebKey.import_key_set(jwks),
            claims_options={
                "iss": {"essential": True, "value": document["issuer"]},
                "aud": {"essential": True, "value": "third-party-app"},
                "nonce": {"essential": True, "value": nonce},
            },
        )
        claims.validate()

        assert claims["sub"] == END_USER
        assert claims["email"] == "elena@example.org"

    def test_the_advertised_userinfo_endpoint_answers(self):
        """The other half of the contract: a client that would rather ask
        than read the token gets the same answer."""
        document = self.discover()
        url, _state = self.rp.create_authorization_url(
            document["authorization_endpoint"],
            code_verifier="a-verifier-long-enough-to-satisfy-rfc-7636-minimums",
        )
        query = consent(self.browser, url)
        self.rp.fetch_token(
            document["token_endpoint"],
            code=query["code"],
            code_verifier="a-verifier-long-enough-to-satisfy-rfc-7636-minimums",
        )

        response = self.rp.get(document["userinfo_endpoint"], timeout=30)

        assert response.status_code == 200
        assert response.json()["sub"] == END_USER
        assert response.json()["name"] == "Elena Example"


class TestRefreshRotation:
    """Rotation driven by a real client, which is where it has to work."""

    @pytest.fixture(autouse=True)
    def _setup(self, server, rp) -> None:
        self.url = server["url"]
        self.rp = rp
        self.browser = requests.Session()
        self.browser.auth = (END_USER, END_USER_PASSWORD)

    def sign_in(self) -> dict:
        """Complete a full authorization and return the token response.

        :returns: The token, including its refresh token.
        """
        verifier = "a-verifier-long-enough-to-satisfy-rfc-7636-minimums"
        url, _state = self.rp.create_authorization_url(
            f"{self.url}/@@oauth-authorize", code_verifier=verifier
        )
        query = consent(self.browser, url)
        return self.rp.fetch_token(
            f"{self.url}/@@oauth-token", code=query["code"], code_verifier=verifier
        )

    def test_the_code_grant_hands_back_a_refresh_token(self):
        assert self.sign_in()["refresh_token"]

    def test_refreshing_yields_a_working_access_token(self):
        """The point of the whole mechanism: the client keeps working with no
        human anywhere near it."""
        original = self.sign_in()

        refreshed = self.rp.refresh_token(
            f"{self.url}/@@oauth-token", refresh_token=original["refresh_token"]
        )

        response = requests.get(
            f"{self.url}/@users/{END_USER}",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {refreshed['access_token']}",
            },
            timeout=30,
        )
        assert response.status_code == 200
        assert response.json()["id"] == END_USER

    def test_the_refresh_token_is_rotated(self):
        original = self.sign_in()

        refreshed = self.rp.refresh_token(
            f"{self.url}/@@oauth-token", refresh_token=original["refresh_token"]
        )

        assert refreshed["refresh_token"] != original["refresh_token"]

    def test_the_previous_refresh_token_stops_working(self):
        """The plan's check for this gate, through a real client."""
        original = self.sign_in()
        self.rp.refresh_token(
            f"{self.url}/@@oauth-token", refresh_token=original["refresh_token"]
        )

        with pytest.raises(Exception, match="invalid_grant"):
            self.rp.refresh_token(
                f"{self.url}/@@oauth-token", refresh_token=original["refresh_token"]
            )

    def test_a_replay_revokes_the_whole_chain(self):
        """Rotation without this is theatre: a thief who uses the stolen copy
        first simply becomes the client. Detecting that two parties hold one
        token, and cutting both off, is what the rotation is for."""
        original = self.sign_in()
        live = self.rp.refresh_token(
            f"{self.url}/@@oauth-token", refresh_token=original["refresh_token"]
        )

        with pytest.raises(Exception, match="invalid_grant"):
            self.rp.refresh_token(
                f"{self.url}/@@oauth-token", refresh_token=original["refresh_token"]
            )

        with pytest.raises(Exception, match="invalid_grant"):
            self.rp.refresh_token(
                f"{self.url}/@@oauth-token", refresh_token=live["refresh_token"]
            )
