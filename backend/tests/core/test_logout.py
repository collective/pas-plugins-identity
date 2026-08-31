"""Back-channel logout, received from a provider.

The provider tells this site that somebody's session there has ended. There is
no browser in the request, which is the whole point: it works after the user
has closed the tab.

The tokens here are minted with a key this test controls and the provider's
JWKS is stubbed to match, because the thing under test is what this package
does with a *valid* token and what it refuses. A real provider signing a real
logout token is what the Keycloak federation stack exercises, and is a
different kind of evidence.
"""

from datetime import datetime
from datetime import timedelta
from datetime import UTC
from pas.plugins.identity.core.browser.logout import BackChannelLogoutView
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.events import ISessionsRevoked
from pas.plugins.identity.core.flows import metadata as flow_metadata
from pas.plugins.identity.core.logout import LOGOUT_EVENT
from pas.plugins.identity.core.logout import LogoutError
from pas.plugins.identity.core.logout import revoke_sessions
from pas.plugins.identity.core.logout import validate_logout_token
from pas.plugins.identity.core.pas import PLUGIN_ID
from plone import api
from zope.component import adapter
from zope.component import getGlobalSiteManager

import json
import pytest


ISSUER = "https://idp.example.org"
CLIENT_ID = "plone-at-example"
PROVIDER_ID = "upstream"
SUBJECT = "provider-subject-42"


@pytest.fixture
def signing_key():
    """A key pair standing in for the provider's."""
    from authlib.jose import JsonWebKey

    return JsonWebKey.generate_key("RSA", 2048, is_private=True)


@pytest.fixture
def provider(portal, signing_key, monkeypatch):
    """Configure an upstream provider whose JWKS this test controls."""
    from authlib.jose import JsonWebKey

    set_providers([
        ProviderConfig.deserialize({
            "id": PROVIDER_ID,
            "title": "Upstream",
            "driver": "oidc-generic",
            "enabled": True,
            "config": {
                "client_id": CLIENT_ID,
                "client_secret": "not-used-here",
                "issuer": ISSUER,
            },
        })
    ])
    public = JsonWebKey.import_key_set({
        "keys": [signing_key.as_dict(is_private=False)]
    })
    monkeypatch.setattr(
        flow_metadata,
        "metadata_for",
        lambda config: {"issuer": ISSUER, "jwks": public},
    )
    yield PROVIDER_ID
    set_providers([])


@pytest.fixture
def mint(signing_key):
    """Return a factory minting logout tokens.

    :returns: Callable taking claim overrides and returning an encoded token.
    """
    from authlib.jose import JsonWebToken

    def factory(**overrides) -> str:
        """Mint a logout token.

        :param overrides: Claims to replace or, with ``None``, to omit.
        :returns: The encoded token.
        """
        now = datetime.now(UTC)
        claims = {
            "iss": ISSUER,
            "aud": CLIENT_ID,
            "sub": SUBJECT,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=2)).timestamp()),
            "jti": f"jti-{now.timestamp()}-{len(overrides)}",
            "events": {LOGOUT_EVENT: {}},
        }
        claims.update(overrides)
        claims = {k: v for k, v in claims.items() if v is not None}
        header = {"alg": "RS256", "kid": signing_key.as_dict()["kid"]}
        return (
            JsonWebToken(["RS256"]).encode(header, claims, signing_key).decode("ascii")
        )

    return factory


@pytest.fixture
def linked(portal):
    """A Plone user whose identity at the upstream provider is known."""
    plugin = portal.acl_users[PLUGIN_ID]
    userid, _login = plugin.authenticateCredentials({
        "extractor": "pas.plugins.identity",
        "provider": PROVIDER_ID,
        "subject": SUBJECT,
        "claims": {"email": "someone@example.org", "fullname": "Someone"},
    })
    return userid


def post(portal, **form):
    """Drive the logout view as a POST and return ``(status, body)``.

    :param portal: The Plone site.
    :param form: Form parameters.
    :returns: Status code and the raw body.
    """
    request = portal.REQUEST
    request.form.clear()
    request.form.update(form)
    request.environ["REQUEST_METHOD"] = "POST"
    body = BackChannelLogoutView(portal, request)()
    return request.response.getStatus(), body


class TestTokenValidation:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, provider, mint) -> None:
        self.portal = portal
        self.mint = mint

    def test_a_good_token_names_its_provider(self):
        provider_id, claims = validate_logout_token(self.mint())

        assert provider_id == PROVIDER_ID
        assert claims["sub"] == SUBJECT

    def test_an_unknown_issuer_is_refused(self):
        """The issuer is how the verifying key is chosen. A token naming a
        provider this site has never configured cannot be checked at all."""
        with pytest.raises(LogoutError, match="No configured provider"):
            validate_logout_token(self.mint(iss="https://elsewhere.example.org"))

    def test_the_wrong_audience_is_refused(self):
        """A logout token addressed to a different client is not this site's
        to act on, even though the same provider signed it."""
        with pytest.raises(LogoutError):
            validate_logout_token(self.mint(aud="some-other-client"))

    def test_a_token_without_the_logout_event_is_refused(self):
        """Back-Channel Logout 1.0 §2.4. Without this an `id_token` would be
        accepted as a logout instruction, which is a way to log anybody out at
        will."""
        with pytest.raises(LogoutError, match="not a back-channel logout"):
            validate_logout_token(self.mint(events={"http://other/event": {}}))

    def test_a_token_carrying_a_nonce_is_refused(self):
        """Back-Channel Logout 1.0 §2.4 again, and the same attack from the
        other side: a nonce means somebody is passing an id_token off as a
        logout token."""
        with pytest.raises(LogoutError, match="carries no nonce"):
            validate_logout_token(self.mint(nonce="xyzzy"))

    def test_a_token_with_neither_sub_nor_sid_is_refused(self):
        with pytest.raises(LogoutError, match="neither sub nor sid"):
            validate_logout_token(self.mint(sub=None))

    def test_a_token_without_a_jti_is_refused(self):
        """Replay protection is impossible without one."""
        with pytest.raises(LogoutError):
            validate_logout_token(self.mint(jti=None))

    def test_a_forged_signature_is_refused(self):
        """The provider's JWKS is the only thing that makes any of this
        trustworthy."""
        from authlib.jose import JsonWebKey
        from authlib.jose import JsonWebToken

        other = JsonWebKey.generate_key("RSA", 2048, is_private=True)
        forged = (
            JsonWebToken(["RS256"])
            .encode(
                {"alg": "RS256", "kid": other.as_dict()["kid"]},
                {
                    "iss": ISSUER,
                    "aud": CLIENT_ID,
                    "sub": SUBJECT,
                    "iat": 1,
                    "jti": "forged",
                    "events": {LOGOUT_EVENT: {}},
                },
                other,
            )
            .decode("ascii")
        )

        with pytest.raises(LogoutError):
            validate_logout_token(forged)

    def test_garbage_is_refused(self):
        with pytest.raises(LogoutError):
            validate_logout_token("not-a-jwt")

    def test_a_misconfigured_provider_is_skipped_not_fatal(self):
        """One provider missing its issuer must not stop the search: it
        cannot be the one that signed this token, and the next one may be."""
        broken = ProviderConfig.deserialize({
            "id": "broken",
            "title": "Broken",
            "driver": "oidc-generic",
            "enabled": True,
            "config": {"client_id": "x", "issuer": ""},
        })
        working = ProviderConfig.deserialize({
            "id": PROVIDER_ID,
            "title": "Upstream",
            "driver": "oidc-generic",
            "enabled": True,
            "config": {"client_id": CLIENT_ID, "issuer": ISSUER},
        })
        set_providers([broken, working])

        provider_id, _claims = validate_logout_token(self.mint())

        assert provider_id == PROVIDER_ID

    def test_a_provider_exposing_no_jwks_is_refused(self, monkeypatch):
        """Nothing to verify the signature with, so nothing is trusted."""
        monkeypatch.setattr(
            flow_metadata, "metadata_for", lambda config: {"issuer": ISSUER}
        )

        with pytest.raises(LogoutError, match="no JWKS"):
            validate_logout_token(self.mint())

    def test_a_provider_with_no_client_id_is_refused(self):
        """The audience of a logout token is the client *we* registered as,
        and an empty one would match anything."""
        set_providers([
            ProviderConfig.deserialize({
                "id": PROVIDER_ID,
                "title": "Upstream",
                "driver": "oidc-generic",
                "enabled": True,
                "config": {"client_id": "", "issuer": ISSUER},
            })
        ])

        with pytest.raises(LogoutError, match="no client id"):
            validate_logout_token(self.mint())


class TestTheEndpoint:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, provider, mint, linked) -> None:
        self.portal = portal
        self.mint = mint
        self.userid = linked
        self.plugin = portal.acl_users[PLUGIN_ID]

    def test_a_good_token_is_accepted(self):
        status, body = post(self.portal, logout_token=self.mint())

        assert status == 200
        assert body == ""

    def test_get_is_refused(self):
        request = self.portal.REQUEST
        request.form.clear()
        request.environ["REQUEST_METHOD"] = "GET"

        BackChannelLogoutView(self.portal, request)()

        assert request.response.getStatus() == 405

    def test_no_token_is_refused(self):
        status, body = post(self.portal)

        assert status == 400
        assert json.loads(body)["error"] == "invalid_request"

    def test_a_bad_token_is_refused(self):
        status, _body = post(self.portal, logout_token="not-a-jwt")

        assert status == 400

    def test_a_replay_is_refused(self):
        """Back-Channel Logout 1.0 §2.6. The identifier is recorded before any
        work is done, so a token cannot be acted on twice even if the first
        attempt failed halfway through."""
        token = self.mint()
        post(self.portal, logout_token=token)

        status, body = post(self.portal, logout_token=token)

        assert status == 400
        assert "replayed" in json.loads(body)["error_description"]

    def test_an_unknown_subject_is_a_success(self):
        """Nothing to end. Answering differently would tell an
        unauthenticated caller which of a provider's subjects have accounts
        here."""
        status, _body = post(self.portal, logout_token=self.mint(sub="nobody"))

        assert status == 200

    def test_success_is_200_and_not_204(self):
        """Zope turns a 200 with an empty body and no content type into a
        204, and the specification lists 200. A provider is entitled to read
        an unlisted status as a failed delivery and retry."""
        status, _body = post(self.portal, logout_token=self.mint())

        assert status == 200

    def test_the_response_is_never_cached(self):
        post(self.portal, logout_token=self.mint())

        assert self.portal.REQUEST.response.getHeader("Cache-Control") == "no-store"


class TestTheEvent:
    """What lets the ``[server]`` layer hear about this without core
    importing it."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, provider, mint, linked) -> None:
        self.portal = portal
        self.mint = mint
        self.userid = linked
        self.recorded = []

        @adapter(ISessionsRevoked)
        def record(event):
            self.recorded.append(event)

        gsm = getGlobalSiteManager()
        gsm.registerHandler(record, (ISessionsRevoked,))
        yield
        gsm.unregisterHandler(record, (ISessionsRevoked,))

    def test_it_fires_for_a_known_identity(self):
        post(self.portal, logout_token=self.mint())

        assert len(self.recorded) == 1
        assert self.recorded[0].userid == self.userid
        assert self.recorded[0].provider == PROVIDER_ID
        assert self.recorded[0].subject == SUBJECT

    def test_it_does_not_fire_for_an_unknown_identity(self):
        post(self.portal, logout_token=self.mint(sub="nobody"))

        assert self.recorded == []

    def test_it_reports_that_sessions_could_not_be_ended(self):
        """`per_user_keyring` is off by default, so out of the box a site
        gets the event and an honest False rather than a silent no-op."""
        post(self.portal, logout_token=self.mint())

        assert self.recorded[0].sessions_ended is False


class TestSessionRevocation:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, linked) -> None:
        self.portal = portal
        self.userid = linked
        self.session = portal.acl_users.session

    def test_it_refuses_without_a_per_user_keyring(self):
        """Every ticket in the site is signed from one ring, so ending this
        user's would end everybody's. Refusing loudly beats doing that."""
        assert self.session.per_user_keyring is False

        assert revoke_sessions(self.userid) is False

    def test_it_succeeds_with_a_per_user_keyring(self):
        self.session.per_user_keyring = True

        assert revoke_sessions(self.userid) is True

    def test_a_user_who_never_signed_in_is_not_an_error(self):
        """No ring means no ticket was ever signed for them. Nothing to end,
        and nothing wrong."""
        self.session.per_user_keyring = True

        assert revoke_sessions("never-seen") is True

    def test_it_rotates_the_users_ring(self):
        """The actual mechanism: the secret their tickets were signed with
        stops existing."""
        from plone.keyring.interfaces import IKeyManager
        from zope.component import getUtility

        self.session.per_user_keyring = True
        # Signing once is what creates the ring in the first place.
        self.session._getSigningSecret(self.userid)
        manager = getUtility(IKeyManager)
        ring = self.session._getSecretKey(self.userid)
        before = manager.secret(ring=ring)

        revoke_sessions(self.userid)

        assert manager.secret(ring=ring) != before


class TestTheJTIStore:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.store = portal.acl_users[PLUGIN_ID].logout_jtis

    def test_an_unseen_identifier_is_not_a_replay(self):
        assert self.store.seen("fresh") is False

    def test_a_recorded_identifier_is_a_replay(self):
        self.store.record("spent")

        assert self.store.seen("spent") is True

    def test_it_forgets_identifiers_that_can_no_longer_be_replayed(self):
        self.store.record("old")
        self.store._seen["old"] = datetime.now(UTC) - timedelta(seconds=1)

        self.store.record("new")

        assert self.store.seen("old") is False
        assert self.store.count() == 1

    def test_it_survives_a_missing_attribute(self):
        """A plugin persisted before this store existed keeps working."""
        plugin = api.portal.get_tool("acl_users")[PLUGIN_ID]
        del plugin._logout_jtis

        assert plugin.logout_jtis.count() == 0
