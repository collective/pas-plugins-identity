"""Integration tests for ``@login-providers`` (Gate 1)."""

from . import CALLBACK_URL
from pas.plugins.identity.core.controlpanel import CALLBACK_URL_RECORD
from pas.plugins.identity.core.flows import SESSION_KEY
from pas.plugins.identity.core.flows.session import COOKIE_NAME
from pas.plugins.identity.core.flows.session import decode
from pas.plugins.identity.core.interfaces import FlowError
from pas.plugins.identity.core.services.login import LoginProviders
from plone import api
from urllib.parse import parse_qs
from urllib.parse import urlparse

import pytest


def service(portal, request_, provider_id: str | None = None) -> LoginProviders:
    """Build the service, optionally traversed to one provider.

    :param portal: The Plone site.
    :param request_: The current request.
    :param provider_id: Provider to traverse to, if any.
    :returns: The service.
    """
    view = LoginProviders(portal, request_)
    if provider_id is not None:
        view.publishTraverse(request_, provider_id)
    return view


class TestListing:
    def test_lists_enabled_providers(self, portal, request_, configured):
        """The login page gets one entry per usable provider."""
        result = service(portal, request_).reply()

        assert [item["id"] for item in result["items"]] == ["dex"]

    def test_entry_carries_a_label_and_a_link(self, portal, request_, configured):
        """Enough to render a button and know where it goes."""
        item = service(portal, request_).reply()["items"][0]

        assert item["title"] == "Dex"
        assert item["driver"] == "oidc-generic"
        assert item["@id"].endswith("/@login-providers/dex")

    def test_leaks_no_configuration(self, portal, request_, configured):
        """I4 -- nothing from the provider config leaves here, masked or not."""
        item = service(portal, request_).reply()["items"][0]

        assert set(item) == {"@id", "id", "title", "driver"}

    def test_empty_site_lists_nothing(self, portal, request_):
        """A site with no providers renders an empty login page, not a 500."""
        assert service(portal, request_).reply()["items"] == []

    def test_listing_starts_no_flow(self, portal, request_, configured):
        """Rendering the login page must not mint attempts: a login page is
        hit far more often than a login happens."""
        service(portal, request_).reply()

        assert COOKIE_NAME not in request_.response.cookies


class TestStart:
    def test_returns_the_authorize_url(
        self, portal, request_, configured, stub_metadata
    ):
        """Clicking a button yields somewhere to send the browser."""
        stub_metadata()

        result = service(portal, request_, "dex").reply()

        assert result["provider"] == "dex"
        assert result["authorize_url"].startswith("http://dex:5556/dex/auth")

    def test_redirect_uri_is_the_configured_callback(
        self, portal, request_, configured, stub_metadata
    ):
        """The provider must be sent the frontend route, not the portal URL:
        with Volto the two need not even share an origin."""
        stub_metadata()

        result = service(portal, request_, "dex").reply()

        query = parse_qs(urlparse(result["authorize_url"]).query)
        assert query["redirect_uri"] == [CALLBACK_URL]

    def test_stores_the_attempt_in_a_signed_cookie(
        self, portal, request_, configured, stub_metadata
    ):
        """S1 -- the attempt is bound to this browser."""
        stub_metadata()

        result = service(portal, request_, "dex").reply()

        state = parse_qs(urlparse(result["authorize_url"]).query)["state"][0]
        stored = decode(request_.response.cookies[COOKIE_NAME]["value"])
        assert state in stored[SESSION_KEY]

    def test_came_from_is_carried(self, portal, request_, configured, stub_metadata):
        """Where the user was headed survives the round trip."""
        stub_metadata()
        request_.form["came_from"] = f"{portal.absolute_url()}/some/page"

        service(portal, request_, "dex").reply()

        stored = decode(request_.response.cookies[COOKIE_NAME]["value"])
        attempt = next(iter(stored[SESSION_KEY].values()))
        assert attempt["came_from"].endswith("/some/page")

    def test_hostile_came_from_is_dropped(
        self, portal, request_, configured, stub_metadata
    ):
        """S6 -- and it is dropped before it is ever stored."""
        stub_metadata()
        request_.form["came_from"] = "https://evil.example/phish"

        service(portal, request_, "dex").reply()

        stored = decode(request_.response.cookies[COOKIE_NAME]["value"])
        attempt = next(iter(stored[SESSION_KEY].values()))
        assert attempt["came_from"] == ""

    @pytest.mark.parametrize("provider_id", ["nope", "github"])
    def test_unknown_and_disabled_look_the_same(
        self, portal, request_, configured, provider_id: str
    ):
        """Which providers a site has configured is not worth probing for, so
        a disabled one answers exactly like one that does not exist."""
        result = service(portal, request_, provider_id).reply()

        assert request_.response.getStatus() == 404
        assert result["error"]["type"] == "Unknown provider"

    def test_unreachable_provider_is_a_bad_gateway(
        self, portal, request_, configured, stub_metadata
    ):
        """A provider that is down is the provider's fault, not the caller's."""
        stub_metadata(FlowError("dex: could not fetch discovery"))

        result = service(portal, request_, "dex").reply()

        assert request_.response.getStatus() == 502
        assert result["error"]["type"] == "Provider unavailable"

    def test_missing_callback_url_is_reported(
        self, portal, request_, configured, stub_metadata
    ):
        """An unconfigured callback URL would otherwise surface as an opaque
        rejection from the provider, long after the useful moment."""
        stub_metadata()
        api.portal.set_registry_record(CALLBACK_URL_RECORD, "")

        result = service(portal, request_, "dex").reply()

        assert request_.response.getStatus() == 502
        assert "callback URL" in result["error"]["message"]
