"""Unit tests for provider metadata resolution (§4.4, C1).

No network: :func:`requests.get` is replaced with a recording stub, which is
also what lets the cache be tested -- a second call that does not reach the
stub is the whole point of the cache existing.
"""

from . import DEX_PROVIDER
from copy import deepcopy
from datetime import timedelta
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.flows import metadata as md
from pas.plugins.identity.core.interfaces import FlowError
from typing import Any

import pytest
import requests


#: The issuer the Dex fixture points at.
ISSUER = "http://dex:5556/dex"

#: A discovery document as Dex publishes one, trimmed to what is read.
DISCOVERY = {
    "issuer": ISSUER,
    "authorization_endpoint": f"{ISSUER}/auth",
    "token_endpoint": f"{ISSUER}/token",
    "userinfo_endpoint": f"{ISSUER}/userinfo",
    "jwks_uri": f"{ISSUER}/keys",
}

#: The key set behind ``jwks_uri``.
KEYS = {"keys": [{"kty": "RSA", "kid": "test-key", "n": "…", "e": "AQAB"}]}


class StubResponse:
    """The part of ``requests.Response`` that :func:`_fetch` touches."""

    def __init__(self, payload: Any, status_code: int = 200) -> None:
        """Hold a canned payload.

        :param payload: What :meth:`json` returns.
        :param status_code: HTTP status; 400 and up raises.
        """
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        """Raise when the provider answered with an error.

        :raises requests.HTTPError: When the status is 400 or above.
        """
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")

    def json(self) -> Any:
        """Return the canned payload.

        A fresh copy each call, as ``requests`` gives: the module under test
        adds ``jwks`` to the document it is handed, and handing it the test's
        own constant would let one test edit the next one's fixture.

        :returns: The payload.
        :raises ValueError: When the payload stands in for an undecodable body.
        """
        if isinstance(self.payload, ValueError):
            raise self.payload
        return deepcopy(self.payload)


@pytest.fixture(autouse=True)
def clean_cache():
    """Keep the module-level discovery cache from leaking between tests."""
    md.forget()
    yield
    md.forget()


@pytest.fixture()
def http(monkeypatch):
    """Return an installer replacing ``requests.get`` with a recorded stub.

    :returns: Callable taking a URL-to-response mapping and returning the list
        of URLs that were actually requested.
    """
    requested: list[str] = []

    def install(responses: dict[str, StubResponse]) -> list[str]:
        """Install the stub.

        :param responses: Mapping of URL to the response to answer with.
        :returns: The list URLs are appended to, in request order.
        """

        def fake_get(url: str, **kwargs: Any) -> StubResponse:
            """Answer from the mapping.

            :param url: Requested URL.
            :param kwargs: Ignored, beyond asserting a timeout is passed.
            :returns: The canned response.
            :raises AssertionError: When the call passes no timeout.
            :raises requests.ConnectionError: When the URL is not mapped.
            """
            assert kwargs.get("timeout"), "every provider call needs a timeout"
            requested.append(url)
            if url not in responses:
                raise requests.ConnectionError(f"unmapped {url}")
            return responses[url]

        monkeypatch.setattr(requests, "get", fake_get)
        return requested

    return install


@pytest.fixture()
def dex() -> ProviderConfig:
    """Return the Dex provider configuration."""
    return ProviderConfig.deserialize(DEX_PROVIDER)


def working_provider() -> dict[str, StubResponse]:
    """Return the response map of a healthy Dex.

    :returns: URL-to-response mapping.
    """
    return {
        f"{ISSUER}{md.DISCOVERY_PATH}": StubResponse(DISCOVERY),
        DISCOVERY["jwks_uri"]: StubResponse(KEYS),
    }


class TestStaticMetadata:
    """Providers with published endpoints never touch the network."""

    def test_github_endpoints_are_constants(self, portal, http):
        """GitHub is plain OAuth2 and publishes no discovery document."""
        requested = http({})
        provider = ProviderConfig.deserialize({
            "id": "gh",
            "driver": "github",
            "config": {"client_id": "x"},
        })

        metadata = md.metadata_for(provider)

        assert metadata["authorization_endpoint"].startswith("https://github.com/")
        assert metadata["userinfo_endpoint"] == "https://api.github.com/user"
        assert requested == []

    def test_caller_cannot_mutate_the_constant(self, portal):
        """Handing out the module's own dict would let one login's metadata
        edit the next one's."""
        provider = ProviderConfig.deserialize({
            "id": "gh",
            "driver": "github",
            "config": {},
        })

        md.metadata_for(provider)["token_endpoint"] = "https://evil.example"

        assert md.STATIC_METADATA["github"]["token_endpoint"] == (
            "https://github.com/login/oauth/access_token"
        )


class TestIssuerResolution:
    def test_driver_fixed_issuer_wins(self, portal):
        """Google's issuer is the driver's business, not the operator's."""
        provider = ProviderConfig.deserialize({
            "id": "g",
            "driver": "google",
            "config": {"issuer": "http://evil.test"},
        })

        assert md.issuer_for(provider) == "https://accounts.google.com"

    def test_configured_issuer_is_used(self, portal, dex):
        """A generic OIDC provider is whatever the operator configured."""
        assert md.issuer_for(dex) == ISSUER

    def test_trailing_slash_is_normalized(self, portal):
        """``…/dex`` and ``…/dex/`` are one issuer, not two cache entries."""
        provider = ProviderConfig.deserialize({
            "id": "d",
            "driver": "oidc-generic",
            "config": {"issuer": f"{ISSUER}/ "},
        })

        assert md.issuer_for(provider) == ISSUER

    def test_missing_issuer_is_refused(self, portal):
        """An unconfigured provider fails clearly, not with a request to ``/``."""
        provider = ProviderConfig.deserialize({
            "id": "d",
            "driver": "oidc-generic",
            "config": {},
        })

        with pytest.raises(FlowError, match="no issuer configured"):
            md.issuer_for(provider)

    def test_driver_without_endpoints_is_refused(self, portal):
        """The email driver's magic link never leaves the site, so asking it
        for an authorize endpoint is a programming error, not a fetch."""
        provider = ProviderConfig.deserialize({
            "id": "mail",
            "driver": "email",
            "config": {},
        })

        with pytest.raises(FlowError, match="no authorization endpoints"):
            md.metadata_for(provider)


class TestDiscovery:
    def test_returns_the_endpoints(self, portal, dex, http):
        """The happy path: one document, one key set."""
        http(working_provider())

        metadata = md.metadata_for(dex)

        assert metadata["authorization_endpoint"] == DISCOVERY["authorization_endpoint"]
        assert metadata["token_endpoint"] == DISCOVERY["token_endpoint"]

    def test_attaches_the_key_set(self, portal, dex, http):
        """The flow layer validates id_tokens against ``jwks``."""
        http(working_provider())

        assert md.metadata_for(dex)["jwks"] == KEYS

    def test_document_without_jwks_still_resolves(self, portal, dex, http):
        """A provider with no key set can still do the userinfo path; the
        id_token path refuses on its own terms rather than here."""
        document = {k: v for k, v in DISCOVERY.items() if k != "jwks_uri"}
        http({f"{ISSUER}{md.DISCOVERY_PATH}": StubResponse(document)})

        metadata = md.metadata_for(dex)

        assert "jwks" not in metadata
        assert metadata["token_endpoint"] == DISCOVERY["token_endpoint"]

    def test_mismatched_issuer_is_refused(self, portal, dex, http):
        """RFC 8414 section 3.3 -- a document naming someone else is either a
        misconfiguration or an issuer substitution."""
        document = {**DISCOVERY, "issuer": "https://evil.example"}
        http({f"{ISSUER}{md.DISCOVERY_PATH}": StubResponse(document)})

        with pytest.raises(FlowError, match="declares issuer"):
            md.metadata_for(dex)

    def test_trailing_slash_in_declared_issuer_is_tolerated(self, portal, dex, http):
        """Providers are inconsistent about the trailing slash; that alone is
        not an issuer mismatch."""
        document = {**DISCOVERY, "issuer": f"{ISSUER}/"}
        http({
            f"{ISSUER}{md.DISCOVERY_PATH}": StubResponse(document),
            DISCOVERY["jwks_uri"]: StubResponse(KEYS),
        })

        assert md.metadata_for(dex)["token_endpoint"] == DISCOVERY["token_endpoint"]

    def test_unreachable_provider_is_a_flow_error(self, portal, dex, http):
        """A provider that is down fails the login, not the request handler."""
        http({})

        with pytest.raises(FlowError, match="could not fetch"):
            md.metadata_for(dex)

    def test_http_error_is_a_flow_error(self, portal, dex, http):
        """So does one answering 500."""
        http({f"{ISSUER}{md.DISCOVERY_PATH}": StubResponse({}, status_code=500)})

        with pytest.raises(FlowError, match="could not fetch"):
            md.metadata_for(dex)

    def test_undecodable_body_is_a_flow_error(self, portal, dex, http):
        """An HTML error page is not a discovery document."""
        http({
            f"{ISSUER}{md.DISCOVERY_PATH}": StubResponse(ValueError("not json")),
        })

        with pytest.raises(FlowError, match="could not fetch"):
            md.metadata_for(dex)

    def test_json_that_is_not_an_object_is_refused(self, portal, dex, http):
        """A JSON list decodes fine and is still not metadata."""
        http({f"{ISSUER}{md.DISCOVERY_PATH}": StubResponse([1, 2, 3])})

        with pytest.raises(FlowError, match="did not return a JSON object"):
            md.metadata_for(dex)

    def test_https_issuer_may_not_downgrade_its_jwks(self, portal, http):
        """A compromised document must not be able to move key fetching onto
        plain HTTP, where it could be rewritten in flight."""
        issuer = "https://idp.example"
        document = {
            "issuer": issuer,
            "authorization_endpoint": f"{issuer}/auth",
            "token_endpoint": f"{issuer}/token",
            "jwks_uri": "http://idp.example/keys",
        }
        http({f"{issuer}{md.DISCOVERY_PATH}": StubResponse(document)})

        with pytest.raises(FlowError, match="refusing to downgrade"):
            md.discover(issuer)


class TestCache:
    def test_second_call_does_not_refetch(self, portal, dex, http):
        """One login costs one round trip, not three."""
        requested = http(working_provider())

        md.metadata_for(dex)
        md.metadata_for(dex)

        assert requested.count(f"{ISSUER}{md.DISCOVERY_PATH}") == 1

    def test_forget_one_issuer_refetches_it(self, portal, dex, http):
        """The control panel's test-connection action must see live state."""
        requested = http(working_provider())
        md.metadata_for(dex)

        md.forget(ISSUER)
        md.metadata_for(dex)

        assert requested.count(f"{ISSUER}{md.DISCOVERY_PATH}") == 2

    def test_forget_everything_refetches(self, portal, dex, http):
        """Clearing without an issuer clears the lot."""
        requested = http(working_provider())
        md.metadata_for(dex)

        md.forget()
        md.metadata_for(dex)

        assert requested.count(f"{ISSUER}{md.DISCOVERY_PATH}") == 2

    def test_forget_an_unknown_issuer_is_harmless(self, portal):
        """Nothing cached is not an error."""
        md.forget("https://never-seen.example")

    def test_expired_entry_is_refetched(self, portal, dex, http, monkeypatch):
        """A document older than the TTL is fetched again."""
        requested = http(working_provider())
        md.metadata_for(dex)
        stamped, document = md._CACHE[ISSUER]
        md._CACHE[ISSUER] = (
            stamped - md.DISCOVERY_TTL - timedelta(seconds=1),
            document,
        )

        md.metadata_for(dex)

        assert requested.count(f"{ISSUER}{md.DISCOVERY_PATH}") == 2

    def test_caller_cannot_poison_the_cache(self, portal, dex, http):
        """Metadata handed to one login must not be the object the next one
        reads."""
        http(working_provider())
        md.metadata_for(dex)["token_endpoint"] = "https://evil.example/token"

        assert md.metadata_for(dex)["token_endpoint"] == DISCOVERY["token_endpoint"]
