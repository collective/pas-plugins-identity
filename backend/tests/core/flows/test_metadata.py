"""Unit tests for provider metadata resolution.

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
from pas.plugins.identity.core.interfaces import JSONDict
from plone import api
from plone.registry.interfaces import IRegistry
from zope.component import getUtility

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

    def __init__(self, payload: JSONDict | str, status_code: int = 200) -> None:
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

    def json(self) -> JSONDict:
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


@pytest.fixture
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

        def fake_get(url: str, **kwargs: object) -> StubResponse:
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


@pytest.fixture
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

    @pytest.fixture(autouse=True)
    def _setup(self, portal, http) -> None:
        self.portal = portal
        self.http = http

    def test_github_endpoints_are_constants(self):
        """GitHub is plain OAuth2 and publishes no discovery document."""
        requested = self.http({})
        provider = ProviderConfig.deserialize({
            "id": "gh",
            "driver": "github",
            "config": {"client_id": "x"},
        })

        metadata = md.metadata_for(provider)

        assert metadata["authorization_endpoint"].startswith("https://github.com/")
        assert metadata["userinfo_endpoint"] == "https://api.github.com/user"
        assert requested == []

    def test_caller_cannot_mutate_the_constant(self):
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
    @pytest.fixture(autouse=True)
    def _setup(self, portal, dex) -> None:
        self.portal = portal
        self.dex = dex

    def test_driver_fixed_issuer_wins(self):
        """Google's issuer is the driver's business, not the operator's."""
        provider = ProviderConfig.deserialize({
            "id": "g",
            "driver": "google",
            "config": {"issuer": "http://evil.test"},
        })

        assert md.issuer_for(provider) == "https://accounts.google.com"

    def test_configured_issuer_is_used(self):
        """A generic OIDC provider is whatever the operator configured."""
        assert md.issuer_for(self.dex) == ISSUER

    def test_trailing_slash_is_normalized(self):
        """``…/dex`` and ``…/dex/`` are one issuer, not two cache entries."""
        provider = ProviderConfig.deserialize({
            "id": "d",
            "driver": "oidc-generic",
            "config": {"issuer": f"{ISSUER}/ "},
        })

        assert md.issuer_for(provider) == ISSUER

    def test_missing_issuer_is_refused(self):
        """An unconfigured provider fails clearly, not with a request to ``/``."""
        provider = ProviderConfig.deserialize({
            "id": "d",
            "driver": "oidc-generic",
            "config": {},
        })

        with pytest.raises(FlowError, match="no issuer configured"):
            md.issuer_for(provider)

    def test_a_driver_subclass_discovers_like_its_parent(self):
        """``plone-identity`` *is* the generic OIDC driver with defaults on
        top, and it went a whole release refused for having "no
        authorization endpoints" -- because the resolver kept a list of
        driver ids and only the parent was on it."""
        provider = ProviderConfig.deserialize({
            "id": "peer",
            "driver": "plone-identity",
            "config": {"issuer": ISSUER},
        })

        assert md.issuer_for(provider) == ISSUER

    @pytest.mark.parametrize(
        ("driver_id", "asks"),
        [("oidc-generic", True), ("plone-identity", True), ("email", False)],
    )
    def test_the_driver_is_asked_rather_than_a_list_consulted(self, driver_id, asks):
        """The mechanism, not one driver of it. A driver declares an
        ``issuer`` field or it does not, and a driver this package has never
        heard of gets the same answer as one it ships -- which is what a
        list of driver ids could not do."""
        provider = ProviderConfig.deserialize({
            "id": "p",
            "driver": driver_id,
            "config": {},
        })

        assert md._asks_for_an_issuer(provider) is asks

    def test_a_provider_whose_driver_is_gone_is_refused(self):
        """Uninstalling the add-on that registered a driver leaves the
        provider behind. There is nowhere to discover from, and that is the
        same answer as a driver that never had one."""
        provider = ProviderConfig.deserialize({
            "id": "orphan",
            "driver": "no-such-driver",
            "config": {"issuer": ISSUER},
        })

        with pytest.raises(FlowError, match="no authorization endpoints"):
            md.issuer_for(provider)

    def test_driver_without_endpoints_is_refused(self):
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
    @pytest.fixture(autouse=True)
    def _setup(self, portal, dex, http) -> None:
        self.portal = portal
        self.dex = dex
        self.http = http

    def test_returns_the_endpoints(self):
        """The happy path: one document, one key set."""
        self.http(working_provider())

        metadata = md.metadata_for(self.dex)

        assert metadata["authorization_endpoint"] == DISCOVERY["authorization_endpoint"]
        assert metadata["token_endpoint"] == DISCOVERY["token_endpoint"]

    def test_attaches_the_key_set(self):
        """The flow layer validates id_tokens against ``jwks``."""
        self.http(working_provider())

        assert md.metadata_for(self.dex)["jwks"] == KEYS

    def test_document_without_jwks_still_resolves(self):
        """A provider with no key set can still do the userinfo path; the
        id_token path refuses on its own terms rather than here."""
        document = {k: v for k, v in DISCOVERY.items() if k != "jwks_uri"}
        self.http({f"{ISSUER}{md.DISCOVERY_PATH}": StubResponse(document)})

        metadata = md.metadata_for(self.dex)

        assert "jwks" not in metadata
        assert metadata["token_endpoint"] == DISCOVERY["token_endpoint"]

    def test_mismatched_issuer_is_refused(self):
        """RFC 8414 section 3.3 -- a document naming someone else is either a
        misconfiguration or an issuer substitution."""
        document = {**DISCOVERY, "issuer": "https://evil.example"}
        self.http({f"{ISSUER}{md.DISCOVERY_PATH}": StubResponse(document)})

        with pytest.raises(FlowError, match="declares issuer"):
            md.metadata_for(self.dex)

    def test_trailing_slash_in_declared_issuer_is_tolerated(self):
        """Providers are inconsistent about the trailing slash; that alone is
        not an issuer mismatch."""
        document = {**DISCOVERY, "issuer": f"{ISSUER}/"}
        self.http({
            f"{ISSUER}{md.DISCOVERY_PATH}": StubResponse(document),
            DISCOVERY["jwks_uri"]: StubResponse(KEYS),
        })

        assert (
            md.metadata_for(self.dex)["token_endpoint"] == DISCOVERY["token_endpoint"]
        )

    def test_unreachable_provider_is_a_flow_error(self):
        """A provider that is down fails the login, not the request handler."""
        self.http({})

        with pytest.raises(FlowError, match="could not fetch"):
            md.metadata_for(self.dex)

    def test_http_error_is_a_flow_error(self):
        """So does one answering 500."""
        self.http({f"{ISSUER}{md.DISCOVERY_PATH}": StubResponse({}, status_code=500)})

        with pytest.raises(FlowError, match="could not fetch"):
            md.metadata_for(self.dex)

    def test_undecodable_body_is_a_flow_error(self):
        """An HTML error page is not a discovery document."""
        self.http({
            f"{ISSUER}{md.DISCOVERY_PATH}": StubResponse(ValueError("not json")),
        })

        with pytest.raises(FlowError, match="could not fetch"):
            md.metadata_for(self.dex)

    def test_json_that_is_not_an_object_is_refused(self):
        """A JSON list decodes fine and is still not metadata."""
        self.http({f"{ISSUER}{md.DISCOVERY_PATH}": StubResponse([1, 2, 3])})

        with pytest.raises(FlowError, match="did not return a JSON object"):
            md.metadata_for(self.dex)

    def test_https_issuer_may_not_downgrade_its_jwks(self):
        """A compromised document must not be able to move key fetching onto
        plain HTTP, where it could be rewritten in flight."""
        issuer = "https://idp.example"
        document = {
            "issuer": issuer,
            "authorization_endpoint": f"{issuer}/auth",
            "token_endpoint": f"{issuer}/token",
            "jwks_uri": "http://idp.example/keys",
        }
        self.http({f"{issuer}{md.DISCOVERY_PATH}": StubResponse(document)})

        with pytest.raises(FlowError, match="refusing to downgrade"):
            md.discover(issuer)


class TestCache:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, dex, http) -> None:
        self.portal = portal
        self.dex = dex
        self.http = http

    def test_second_call_does_not_refetch(self):
        """One login costs one round trip, not three."""
        requested = self.http(working_provider())

        md.metadata_for(self.dex)
        md.metadata_for(self.dex)

        assert requested.count(f"{ISSUER}{md.DISCOVERY_PATH}") == 1

    def test_forget_one_issuer_refetches_it(self):
        """The control panel's test-connection action must see live state."""
        requested = self.http(working_provider())
        md.metadata_for(self.dex)

        md.forget(ISSUER)
        md.metadata_for(self.dex)

        assert requested.count(f"{ISSUER}{md.DISCOVERY_PATH}") == 2

    def test_forget_everything_refetches(self):
        """Clearing without an issuer clears the lot."""
        requested = self.http(working_provider())
        md.metadata_for(self.dex)

        md.forget()
        md.metadata_for(self.dex)

        assert requested.count(f"{ISSUER}{md.DISCOVERY_PATH}") == 2

    def test_forget_an_unknown_issuer_is_harmless(self):
        """Nothing cached is not an error."""
        md.forget("https://never-seen.example")

    def test_expired_entry_is_refetched(self, monkeypatch):
        """A document older than the TTL is fetched again."""
        requested = self.http(working_provider())
        md.metadata_for(self.dex)
        stamped, document = md._CACHE[ISSUER]
        md._CACHE[ISSUER] = (
            stamped - md.DISCOVERY_TTL - timedelta(seconds=1),
            document,
        )

        md.metadata_for(self.dex)

        assert requested.count(f"{ISSUER}{md.DISCOVERY_PATH}") == 2

    def test_caller_cannot_poison_the_cache(self):
        """Metadata handed to one login must not be the object the next one
        reads."""
        self.http(working_provider())
        md.metadata_for(self.dex)["token_endpoint"] = "https://evil.example/token"

        assert (
            md.metadata_for(self.dex)["token_endpoint"] == DISCOVERY["token_endpoint"]
        )


class TestTheTimeoutIsASetting:
    """It was a module constant, so a site could not change it.

    How long a login may wait for a provider's metadata depends on where that
    provider is, and the number that suits a container on this host is not the
    one that suits an issuer across an ocean.
    """

    def timeouts(self, monkeypatch) -> list:
        """Record the timeout every fetch is given.

        :param monkeypatch: pytest's patcher.
        :returns: The list the recorder appends to, one entry per fetch.
        """
        seen: list = []

        def fake_get(url: str, **kwargs: object) -> StubResponse:
            """Record the timeout and answer as a healthy Dex would.

            :param url: Requested URL.
            :param kwargs: Where the timeout is.
            :returns: The canned response.
            :raises requests.ConnectionError: When the URL is not mapped.
            """
            seen.append(kwargs.get("timeout"))
            responses = working_provider()
            if url not in responses:
                raise requests.ConnectionError(f"unmapped {url}")
            return responses[url]

        monkeypatch.setattr(requests, "get", fake_get)
        return seen

    def test_without_a_site_it_is_the_schema_default(self, monkeypatch, dex):
        """This module is reachable with no portal at all -- most of the flow
        suite runs that way -- so a missing registry is an ordinary case."""
        seen = self.timeouts(monkeypatch)
        md.forget()

        md.metadata_for(dex)

        assert seen == [10, 10]

    def test_the_timeout_the_site_set_is_the_one_used(self, monkeypatch, portal, dex):
        api.portal.set_registry_record(md.DISCOVERY_TIMEOUT_RECORD, 3)
        seen = self.timeouts(monkeypatch)
        md.forget()

        md.metadata_for(dex)

        assert seen == [3, 3]

    def test_an_unset_timeout_falls_back_to_the_default(self, portal):
        """The record can hold ``None``, and waiting zero seconds for every
        provider is not what an empty field means."""
        # Through the registry rather than ``plone.api``, which refuses to
        # write ``None`` -- while the control-panel form writes exactly that
        # when an optional number is cleared.
        getUtility(IRegistry)[md.DISCOVERY_TIMEOUT_RECORD] = None

        assert md.discovery_timeout() == 10

    def test_the_shipped_timeout_is_what_the_profile_set(self, portal):
        assert md.discovery_timeout() == 10
