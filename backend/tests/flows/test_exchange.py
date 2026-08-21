"""Unit tests for the callback half of the authorization-code flow (§4.4, S1).

The two network calls -- the token request and the userinfo request -- are the
only things stubbed. Everything that matters for security is real: the client
is authlib's, and the ``id_token`` is a genuine RS256 JWT signed with a key
generated here, so signature, issuer, audience, expiry and nonce are validated
by authlib exactly as they would be against Dex.
"""

from . import DEX_METADATA
from . import DEX_PROVIDER
from . import PORTAL_URL
from . import REDIRECT_URI
from authlib.integrations.requests_client import OAuth2Session
from authlib.jose import JsonWebKey
from authlib.jose import JsonWebToken
from datetime import datetime
from datetime import timedelta
from datetime import UTC
from pas.plugins.identity.core import flows
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.flows import FlowManager
from pas.plugins.identity.core.flows import SESSION_KEY
from pas.plugins.identity.core.interfaces import FlowError
from typing import Any
from urllib.parse import parse_qs
from urllib.parse import urlparse

import pytest


#: The provider's signing key. Generated once per test run: RSA keygen is the
#: slowest thing in this module by an order of magnitude.
SIGNING_KEY = JsonWebKey.generate_key("RSA", 2048, {"kid": "test-key"}, True)

#: The JWKS a provider would publish, private half removed.
JWKS = {"keys": [SIGNING_KEY.as_dict(is_private=False)]}

#: Discovery metadata including the JWKS, for the OIDC path.
OIDC_METADATA = {**DEX_METADATA, "jwks": JWKS}

#: What Dex's userinfo endpoint answers.
USERINFO = {
    "sub": "CgVlcmljbxIFbG9jYWw",
    "email": "erico@plone.org",
    "email_verified": True,
    "name": "Érico Andrei",
}


def id_token(
    nonce: str,
    issuer: str = DEX_METADATA["issuer"],
    audience: str = DEX_METADATA["client_id"],
    lifetime: timedelta = timedelta(minutes=5),
    **extra: Any,
) -> str:
    """Sign an ``id_token`` the way a provider would.

    :param nonce: Nonce to embed; must match the attempt to validate.
    :param issuer: The ``iss`` claim.
    :param audience: The ``aud`` claim.
    :param lifetime: How far in the future ``exp`` sits; negative expires it.
    :param extra: Further claims to include.
    :returns: The encoded JWT.
    """
    now = datetime.now(UTC)
    payload = {
        "iss": issuer,
        "aud": audience,
        "sub": USERINFO["sub"],
        "iat": int(now.timestamp()),
        "exp": int((now + lifetime).timestamp()),
        "nonce": nonce,
        **extra,
    }
    token = JsonWebToken(["RS256"]).encode(
        {"alg": "RS256", "kid": "test-key"}, payload, SIGNING_KEY
    )
    return token.decode("utf-8")


class StubResponse:
    """The bit of ``requests.Response`` the userinfo call touches."""

    def __init__(self, payload: dict, status_code: int = 200) -> None:
        """Hold a canned payload.

        :param payload: What :meth:`json` returns.
        :param status_code: HTTP status; 400 and up raises.
        """
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        """Raise when the provider answered with an error.

        :raises RuntimeError: When the status is 400 or above.
        """
        if self.status_code >= 400:
            raise RuntimeError(f"userinfo returned {self.status_code}")

    def json(self) -> dict:
        """Return the canned payload.

        :returns: The payload.
        """
        return self.payload


@pytest.fixture()
def session() -> dict:
    """Return an empty session mapping."""
    return {}


@pytest.fixture()
def manager(session: dict) -> FlowManager:
    """Return a flow manager bound to an empty session."""
    return FlowManager(session, PORTAL_URL)


@pytest.fixture()
def provider() -> ProviderConfig:
    """Return the Dex provider configuration."""
    return ProviderConfig.deserialize(DEX_PROVIDER)


@pytest.fixture()
def stub_provider(monkeypatch):
    """Return an installer that stubs the provider's two endpoints.

    The stub subclasses authlib's own session, so everything the flow does
    besides the two network calls behaves as it does in production.

    :returns: Callable taking the token response and optional userinfo
        payload, and returning the dict recording what was requested.
    """
    recorded: dict[str, Any] = {}

    def install(token: dict, userinfo: StubResponse | None = None):
        """Install the stub.

        :param token: What the token endpoint answers.
        :param userinfo: What the userinfo endpoint answers, if reached.
        :returns: Mapping recording the outgoing requests.
        """

        class StubSession(OAuth2Session):
            """authlib's client with the network calls short-circuited."""

            def fetch_token(self, url: str, **kwargs: Any) -> dict:
                """Record the token request and answer it.

                :param url: The token endpoint.
                :param kwargs: The request parameters.
                :returns: The canned token response.
                """
                recorded["token_request"] = {"url": url, **kwargs}
                return token

            def get(self, url: str, **kwargs: Any) -> StubResponse:
                """Record the userinfo request and answer it.

                :param url: The userinfo endpoint.
                :param kwargs: Ignored.
                :returns: The canned response.
                """
                recorded["userinfo_url"] = url
                return userinfo or StubResponse(USERINFO)

        monkeypatch.setattr(flows, "OAuth2Session", StubSession)
        return recorded

    return install


def start(manager: FlowManager, provider: ProviderConfig, metadata: dict) -> str:
    """Start a flow and return its state.

    :param manager: The flow manager.
    :param provider: The configured provider.
    :param metadata: Provider metadata.
    :returns: The ``state`` value.
    """
    url = manager.start(provider, REDIRECT_URI, metadata)
    return parse_qs(urlparse(url).query)["state"][0]


class TestTokenExchange:
    """The token request itself -- what authlib is asked to send."""

    def test_posts_to_the_discovered_endpoint(self, manager, provider, stub_provider):
        """The token endpoint comes from metadata, never from a guess."""
        state = start(manager, provider, DEX_METADATA)
        recorded = stub_provider({"access_token": "at"})

        manager.finish(provider, REDIRECT_URI, DEX_METADATA, state, "the-code")

        assert recorded["token_request"]["url"] == DEX_METADATA["token_endpoint"]

    def test_sends_the_code_and_pkce_verifier(
        self, manager, provider, stub_provider, session
    ):
        """S1 -- the verifier stored at start is what redeems the code."""
        state = start(manager, provider, DEX_METADATA)
        verifier = session[SESSION_KEY][state]["code_verifier"]
        recorded = stub_provider({"access_token": "at"})

        manager.finish(provider, REDIRECT_URI, DEX_METADATA, state, "the-code")

        assert recorded["token_request"]["code"] == "the-code"
        assert recorded["token_request"]["code_verifier"] == verifier

    def test_sends_the_same_redirect_uri(self, manager, provider, stub_provider):
        """The redirect URI must match the one used at authorize time."""
        state = start(manager, provider, DEX_METADATA)
        recorded = stub_provider({"access_token": "at"})

        manager.finish(provider, REDIRECT_URI, DEX_METADATA, state, "the-code")

        assert recorded["token_request"]["redirect_uri"] == REDIRECT_URI

    def test_returns_the_consumed_attempt(self, manager, provider, stub_provider):
        """The caller gets the attempt back, carrying came_from and link_for."""
        url = manager.start(
            provider,
            REDIRECT_URI,
            DEX_METADATA,
            came_from="/plone/page",
            link_for="userid-1",
        )
        state = parse_qs(urlparse(url).query)["state"][0]
        stub_provider({"access_token": "at"})

        attempt, _ = manager.finish(
            provider, REDIRECT_URI, DEX_METADATA, state, "the-code"
        )

        assert attempt.state == state
        assert attempt.came_from == "/plone/page"
        assert attempt.link_for == "userid-1"

    def test_attempt_is_burnt_on_success(
        self, manager, provider, stub_provider, session
    ):
        """S1 -- a successful callback cannot be replayed either."""
        state = start(manager, provider, DEX_METADATA)
        stub_provider({"access_token": "at"})

        manager.finish(provider, REDIRECT_URI, DEX_METADATA, state, "the-code")

        assert state not in session[SESSION_KEY]


class TestUserinfoClaims:
    """Plain OAuth2 providers -- GitHub's shape -- have no ``id_token``."""

    def test_falls_back_to_userinfo(self, manager, provider, stub_provider):
        """Without an id_token the userinfo endpoint supplies the claims."""
        state = start(manager, provider, DEX_METADATA)
        recorded = stub_provider({"access_token": "at"})

        _, claims = manager.finish(
            provider, REDIRECT_URI, DEX_METADATA, state, "the-code"
        )

        assert claims == USERINFO
        assert recorded["userinfo_url"] == DEX_METADATA["userinfo_endpoint"]

    def test_no_id_token_and_no_userinfo_is_refused(
        self, manager, provider, stub_provider
    ):
        """A provider that offers neither cannot identify anyone."""
        metadata = {k: v for k, v in DEX_METADATA.items() if k != "userinfo_endpoint"}
        state = start(manager, provider, metadata)
        stub_provider({"access_token": "at"})

        with pytest.raises(FlowError, match="no id_token"):
            manager.finish(provider, REDIRECT_URI, metadata, state, "the-code")

    def test_userinfo_error_is_not_swallowed(self, manager, provider, stub_provider):
        """A failed userinfo call must not read as an empty claim set."""
        state = start(manager, provider, DEX_METADATA)
        stub_provider({"access_token": "at"}, StubResponse({}, status_code=500))

        with pytest.raises(RuntimeError, match="500"):
            manager.finish(provider, REDIRECT_URI, DEX_METADATA, state, "the-code")


class TestIdTokenClaims:
    """OIDC providers -- the signed path, preferred whenever available."""

    def test_valid_id_token_is_accepted(
        self, manager, provider, stub_provider, session
    ):
        """A correctly signed token yields its claims."""
        state = start(manager, provider, OIDC_METADATA)
        nonce = session[SESSION_KEY][state]["nonce"]
        recorded = stub_provider({
            "access_token": "at",
            "id_token": id_token(nonce, email="e@x.test"),
        })

        _, claims = manager.finish(
            provider, REDIRECT_URI, OIDC_METADATA, state, "the-code"
        )

        assert claims["sub"] == USERINFO["sub"]
        assert claims["email"] == "e@x.test"
        assert "userinfo_url" not in recorded

    def test_missing_jwks_is_refused(self, manager, provider, stub_provider, session):
        """An unverifiable token is worse than none: refuse it."""
        state = start(manager, provider, DEX_METADATA)
        nonce = session[SESSION_KEY][state]["nonce"]
        stub_provider({"access_token": "at", "id_token": id_token(nonce)})

        with pytest.raises(FlowError, match="no JWKS"):
            manager.finish(provider, REDIRECT_URI, DEX_METADATA, state, "the-code")

    def test_wrong_nonce_is_refused(self, manager, provider, stub_provider, session):
        """S1 -- the nonce ties the token to the session that started the
        flow; a token minted for someone else's session is rejected."""
        state = start(manager, provider, OIDC_METADATA)
        stub_provider({"access_token": "at", "id_token": id_token("someone-elses")})

        with pytest.raises(FlowError, match="id_token rejected"):
            manager.finish(provider, REDIRECT_URI, OIDC_METADATA, state, "the-code")

    def test_wrong_issuer_is_refused(self, manager, provider, stub_provider, session):
        """A token from another issuer does not authenticate here."""
        state = start(manager, provider, OIDC_METADATA)
        nonce = session[SESSION_KEY][state]["nonce"]
        stub_provider({
            "access_token": "at",
            "id_token": id_token(nonce, issuer="https://evil.example"),
        })

        with pytest.raises(FlowError, match="id_token rejected"):
            manager.finish(provider, REDIRECT_URI, OIDC_METADATA, state, "the-code")

    def test_wrong_audience_is_refused(self, manager, provider, stub_provider, session):
        """A token issued to a different client is not ours to accept."""
        state = start(manager, provider, OIDC_METADATA)
        nonce = session[SESSION_KEY][state]["nonce"]
        stub_provider({
            "access_token": "at",
            "id_token": id_token(nonce, audience="another-client"),
        })

        with pytest.raises(FlowError, match="id_token rejected"):
            manager.finish(provider, REDIRECT_URI, OIDC_METADATA, state, "the-code")

    def test_expired_id_token_is_refused(
        self, manager, provider, stub_provider, session
    ):
        """Expiry is authlib's to enforce, and it is enforced."""
        state = start(manager, provider, OIDC_METADATA)
        nonce = session[SESSION_KEY][state]["nonce"]
        stub_provider({
            "access_token": "at",
            "id_token": id_token(nonce, lifetime=timedelta(minutes=-5)),
        })

        with pytest.raises(FlowError, match="id_token rejected"):
            manager.finish(provider, REDIRECT_URI, OIDC_METADATA, state, "the-code")

    def test_tampered_signature_is_refused(
        self, manager, provider, stub_provider, session
    ):
        """The signature is what makes the id_token path the preferred one."""
        state = start(manager, provider, OIDC_METADATA)
        nonce = session[SESSION_KEY][state]["nonce"]
        header, payload, signature = id_token(nonce).split(".")
        forged = f"{header}.{payload}.{signature[:-4]}AAAA"
        stub_provider({"access_token": "at", "id_token": forged})

        with pytest.raises(FlowError, match="id_token rejected"):
            manager.finish(provider, REDIRECT_URI, OIDC_METADATA, state, "the-code")

    def test_audience_comes_from_the_provider_not_discovery(
        self, manager, provider, stub_provider, session
    ):
        """A provider cannot widen its own audience by publishing a different
        ``client_id`` in its discovery document."""
        metadata = {**OIDC_METADATA, "client_id": "some-other-client"}
        state = start(manager, provider, metadata)
        nonce = session[SESSION_KEY][state]["nonce"]
        stub_provider({
            "access_token": "at",
            "id_token": id_token(nonce, audience="some-other-client"),
        })

        with pytest.raises(FlowError, match="id_token rejected"):
            manager.finish(provider, REDIRECT_URI, metadata, state, "the-code")

    def test_provider_without_client_id_refuses_the_token(
        self, manager, stub_provider, session
    ):
        """authlib reads an empty expected audience as "no constraint", so a
        provider with no client id must be refused outright rather than have
        its tokens accepted with the audience check quietly switched off."""
        config = {k: v for k, v in DEX_PROVIDER["config"].items() if k != "client_id"}
        provider = ProviderConfig.deserialize({**DEX_PROVIDER, "config": config})
        state = start(manager, provider, OIDC_METADATA)
        nonce = session[SESSION_KEY][state]["nonce"]
        stub_provider({"access_token": "at", "id_token": id_token(nonce)})

        with pytest.raises(FlowError, match="no client_id configured"):
            manager.finish(provider, REDIRECT_URI, OIDC_METADATA, state, "the-code")
