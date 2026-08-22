"""Unit tests for the callback half of the authorization-code flow.

The two network calls -- the token request and the userinfo request -- are the
only things stubbed. Everything that matters for security is real: the client
is authlib's, and the ``id_token`` is a genuine RS256 JWT signed with a key
generated here, so signature, issuer, audience, expiry and nonce are validated
by authlib exactly as they would be against Dex.
"""

from . import DEX_METADATA
from . import DEX_PROVIDER
from . import REDIRECT_URI
from authlib.integrations.requests_client import OAuth2Session
from authlib.jose import JsonWebKey
from authlib.jose import JsonWebToken
from datetime import datetime
from datetime import timedelta
from datetime import UTC
from pas.plugins.identity.core import flows
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.flows import SESSION_KEY
from pas.plugins.identity.core.interfaces import FlowError
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
    **extra: object,
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


@pytest.fixture
def stub_provider(monkeypatch):
    """Return an installer that stubs the provider's two endpoints.

    The stub subclasses authlib's own session, so everything the flow does
    besides the two network calls behaves as it does in production.

    :returns: Callable taking the token response and optional userinfo
        payload, and returning the dict recording what was requested.
    """
    recorded: dict[str, object] = {}

    def install(token: dict, userinfo: StubResponse | None = None):
        """Install the stub.

        :param token: What the token endpoint answers.
        :param userinfo: What the userinfo endpoint answers, if reached.
        :returns: Mapping recording the outgoing requests.
        """

        class StubSession(OAuth2Session):
            """authlib's client with the network calls short-circuited."""

            def fetch_token(self, url: str, **kwargs: object) -> dict:
                """Record the token request and answer it.

                :param url: The token endpoint.
                :param kwargs: The request parameters.
                :returns: The canned token response.
                """
                recorded["token_request"] = {"url": url, **kwargs}
                return token

            def get(self, url: str, **kwargs: object) -> StubResponse:
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


class TestTokenExchange:
    """The token request itself -- what authlib is asked to send."""

    @pytest.fixture(autouse=True)
    def _setup(self, manager, provider, session, stub_provider) -> None:
        self.manager = manager
        self.provider = provider
        self.session = session
        self.stub_provider = stub_provider

    def start(self, metadata: dict = DEX_METADATA, **kwargs) -> str:
        """Start a flow and return its state.

        :param metadata: Provider metadata.
        :param kwargs: Extra arguments for :meth:`FlowManager.start`.
        :returns: The ``state`` value.
        """
        url = self.manager.start(self.provider, REDIRECT_URI, metadata, **kwargs)
        return parse_qs(urlparse(url).query)["state"][0]

    def finish(self, state: str, metadata: dict = DEX_METADATA):
        """Complete a flow.

        :param state: The attempt's state.
        :param metadata: Provider metadata.
        :returns: The consumed attempt and the claims.
        """
        return self.manager.finish(
            self.provider, REDIRECT_URI, metadata, state, "the-code"
        )

    def test_posts_to_the_discovered_endpoint(self):
        """The token endpoint comes from metadata, never from a guess."""
        state = self.start()
        recorded = self.stub_provider({"access_token": "at"})

        self.finish(state)

        assert recorded["token_request"]["url"] == DEX_METADATA["token_endpoint"]

    def test_sends_the_code_and_pkce_verifier(self):
        """The verifier stored at start is what redeems the code."""
        state = self.start()
        verifier = self.session[SESSION_KEY][state]["code_verifier"]
        recorded = self.stub_provider({"access_token": "at"})

        self.finish(state)

        assert recorded["token_request"]["code"] == "the-code"
        assert recorded["token_request"]["code_verifier"] == verifier

    def test_sends_the_same_redirect_uri(self):
        """The redirect URI must match the one used at authorize time."""
        state = self.start()
        recorded = self.stub_provider({"access_token": "at"})

        self.finish(state)

        assert recorded["token_request"]["redirect_uri"] == REDIRECT_URI

    def test_returns_the_consumed_attempt(self):
        """The caller gets the attempt back, carrying came_from and link_for."""
        state = self.start(came_from="/plone/page", link_for="userid-1")
        self.stub_provider({"access_token": "at"})

        attempt, _ = self.finish(state)

        assert attempt.state == state
        assert attempt.came_from == "/plone/page"
        assert attempt.link_for == "userid-1"

    def test_attempt_is_burnt_on_success(self):
        """A successful callback cannot be replayed either."""
        state = self.start()
        self.stub_provider({"access_token": "at"})

        self.finish(state)

        assert state not in self.session[SESSION_KEY]


class TestUserinfoClaims:
    """Plain OAuth2 providers -- GitHub's shape -- have no ``id_token``."""

    @pytest.fixture(autouse=True)
    def _setup(self, manager, provider, session, stub_provider) -> None:
        self.manager = manager
        self.provider = provider
        self.session = session
        self.stub_provider = stub_provider

    def start(self, metadata: dict = DEX_METADATA, **kwargs) -> str:
        """Start a flow and return its state.

        :param metadata: Provider metadata.
        :param kwargs: Extra arguments for :meth:`FlowManager.start`.
        :returns: The ``state`` value.
        """
        url = self.manager.start(self.provider, REDIRECT_URI, metadata, **kwargs)
        return parse_qs(urlparse(url).query)["state"][0]

    def finish(self, state: str, metadata: dict = DEX_METADATA):
        """Complete a flow.

        :param state: The attempt's state.
        :param metadata: Provider metadata.
        :returns: The consumed attempt and the claims.
        """
        return self.manager.finish(
            self.provider, REDIRECT_URI, metadata, state, "the-code"
        )

    def test_falls_back_to_userinfo(self):
        """Without an id_token the userinfo endpoint supplies the claims."""
        state = self.start()
        recorded = self.stub_provider({"access_token": "at"})

        _, claims = self.finish(state)

        assert claims == USERINFO
        assert recorded["userinfo_url"] == DEX_METADATA["userinfo_endpoint"]

    def test_no_id_token_and_no_userinfo_is_refused(self):
        """A provider that offers neither cannot identify anyone."""
        metadata = {k: v for k, v in DEX_METADATA.items() if k != "userinfo_endpoint"}
        state = self.start(metadata)
        self.stub_provider({"access_token": "at"})

        with pytest.raises(FlowError, match="no id_token"):
            self.finish(state, metadata)

    def test_userinfo_error_is_not_swallowed(self):
        """A failed userinfo call must not read as an empty claim set."""
        state = self.start()
        self.stub_provider({"access_token": "at"}, StubResponse({}, status_code=500))

        with pytest.raises(RuntimeError, match="500"):
            self.finish(state)


class TestIdTokenClaims:
    """OIDC providers -- the signed path, preferred whenever available."""

    @pytest.fixture(autouse=True)
    def _setup(self, manager, provider, session, stub_provider) -> None:
        self.manager = manager
        self.provider = provider
        self.session = session
        self.stub_provider = stub_provider

    def start(self, metadata: dict = DEX_METADATA, **kwargs) -> str:
        """Start a flow and return its state.

        :param metadata: Provider metadata.
        :param kwargs: Extra arguments for :meth:`FlowManager.start`.
        :returns: The ``state`` value.
        """
        url = self.manager.start(self.provider, REDIRECT_URI, metadata, **kwargs)
        return parse_qs(urlparse(url).query)["state"][0]

    def nonce(self, state: str) -> str:
        """Return the nonce minted for an attempt.

        :param state: The attempt's state.
        :returns: The nonce.
        """
        return self.session[SESSION_KEY][state]["nonce"]

    def finish(self, state: str, metadata: dict = DEX_METADATA):
        """Complete a flow.

        :param state: The attempt's state.
        :param metadata: Provider metadata.
        :returns: The consumed attempt and the claims.
        """
        return self.manager.finish(
            self.provider, REDIRECT_URI, metadata, state, "the-code"
        )

    def test_valid_id_token_is_accepted(self):
        """A correctly signed token yields its claims."""
        state = self.start(OIDC_METADATA)
        nonce = self.nonce(state)
        recorded = self.stub_provider({
            "access_token": "at",
            "id_token": id_token(nonce, email="e@x.test"),
        })

        _, claims = self.finish(state, OIDC_METADATA)

        assert claims["sub"] == USERINFO["sub"]
        assert claims["email"] == "e@x.test"
        assert "userinfo_url" not in recorded

    def test_missing_jwks_is_refused(self):
        """An unverifiable token is worse than none: refuse it."""
        state = self.start()
        nonce = self.nonce(state)
        self.stub_provider({"access_token": "at", "id_token": id_token(nonce)})

        with pytest.raises(FlowError, match="no JWKS"):
            self.finish(state)

    def test_wrong_nonce_is_refused(self):
        """The nonce ties the token to the session that started the
        flow; a token minted for someone else's session is rejected."""
        state = self.start(OIDC_METADATA)
        self.stub_provider({
            "access_token": "at",
            "id_token": id_token("someone-elses"),
        })

        with pytest.raises(FlowError, match="id_token rejected"):
            self.finish(state, OIDC_METADATA)

    def test_wrong_issuer_is_refused(self):
        """A token from another issuer does not authenticate here."""
        state = self.start(OIDC_METADATA)
        nonce = self.nonce(state)
        self.stub_provider({
            "access_token": "at",
            "id_token": id_token(nonce, issuer="https://evil.example"),
        })

        with pytest.raises(FlowError, match="id_token rejected"):
            self.finish(state, OIDC_METADATA)

    def test_wrong_audience_is_refused(self):
        """A token issued to a different client is not ours to accept."""
        state = self.start(OIDC_METADATA)
        nonce = self.nonce(state)
        self.stub_provider({
            "access_token": "at",
            "id_token": id_token(nonce, audience="another-client"),
        })

        with pytest.raises(FlowError, match="id_token rejected"):
            self.finish(state, OIDC_METADATA)

    def test_expired_id_token_is_refused(self):
        """Expiry is authlib's to enforce, and it is enforced."""
        state = self.start(OIDC_METADATA)
        nonce = self.nonce(state)
        self.stub_provider({
            "access_token": "at",
            "id_token": id_token(nonce, lifetime=timedelta(minutes=-5)),
        })

        with pytest.raises(FlowError, match="id_token rejected"):
            self.finish(state, OIDC_METADATA)

    def test_tampered_signature_is_refused(self):
        """The signature is what makes the id_token path the preferred one."""
        state = self.start(OIDC_METADATA)
        nonce = self.nonce(state)
        header, payload, signature = id_token(nonce).split(".")
        forged = f"{header}.{payload}.{signature[:-4]}AAAA"
        self.stub_provider({"access_token": "at", "id_token": forged})

        with pytest.raises(FlowError, match="id_token rejected"):
            self.finish(state, OIDC_METADATA)

    def test_audience_comes_from_the_provider_not_discovery(self):
        """A provider cannot widen its own audience by publishing a different
        ``client_id`` in its discovery document."""
        metadata = {**OIDC_METADATA, "client_id": "some-other-client"}
        state = self.start(metadata)
        nonce = self.nonce(state)
        self.stub_provider({
            "access_token": "at",
            "id_token": id_token(nonce, audience="some-other-client"),
        })

        with pytest.raises(FlowError, match="id_token rejected"):
            self.finish(state, metadata)

    def test_provider_without_client_id_refuses_the_token(self):
        """authlib reads an empty expected audience as "no constraint", so a
        provider with no client id must be refused outright rather than have
        its tokens accepted with the audience check quietly switched off."""
        config = {k: v for k, v in DEX_PROVIDER["config"].items() if k != "client_id"}
        self.provider = ProviderConfig.deserialize({**DEX_PROVIDER, "config": config})
        state = self.start(OIDC_METADATA)
        nonce = self.nonce(state)
        self.stub_provider({"access_token": "at", "id_token": id_token(nonce)})

        with pytest.raises(FlowError, match="no client_id configured"):
            self.finish(state, OIDC_METADATA)
