"""Integration tests for ``@login-providers``."""

from . import CALLBACK_URL
from pas.plugins.identity.core.controlpanel import CALLBACK_URL_RECORD
from pas.plugins.identity.core.flows import SESSION_KEY
from pas.plugins.identity.core.flows.session import COOKIE_NAME
from pas.plugins.identity.core.flows.session import decode
from pas.plugins.identity.core.interfaces import FlowError
from pas.plugins.identity.core.services.login.get import LoginProviders
from plone import api
from urllib.parse import parse_qs
from urllib.parse import urlparse

import pytest


def service(portal, request, provider_id: str | None = None) -> LoginProviders:
    """Build the service, optionally traversed to one provider.

    :param portal: The Plone site.
    :param request: The current request.
    :param provider_id: Provider to traverse to, if any.
    :returns: The service.
    """
    view = LoginProviders(portal, request)
    if provider_id is not None:
        view.publishTraverse(request, provider_id)
    return view


class TestListing:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, configured) -> None:
        self.portal = portal
        self.request = request_

    def reply(self) -> dict:
        """Render the provider listing.

        :returns: The service's reply.
        """
        return service(self.portal, self.request).reply()

    def test_lists_enabled_providers(self):
        """The login page gets one entry per usable provider."""
        assert [item["id"] for item in self.reply()["items"]] == ["dex"]

    def test_entry_carries_a_label_and_a_link(self):
        """Enough to render a button and know where it goes."""
        item = self.reply()["items"][0]

        assert item["title"] == "Dex"
        assert item["driver"] == "oidc-generic"
        assert item["@id"].endswith("/@login-providers/dex")

    def test_leaks_no_configuration(self):
        """Nothing from the provider config leaves here, masked or not."""
        item = self.reply()["items"][0]

        assert set(item) == {"@id", "id", "title", "driver"}

    def test_listing_starts_no_flow(self):
        """Rendering the login page must not mint attempts: a login page is
        hit far more often than a login happens."""
        self.reply()

        assert COOKIE_NAME not in self.request.response.cookies


class TestListingWithoutProviders:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_) -> None:
        self.portal = portal
        self.request = request_

    def test_empty_site_lists_nothing(self):
        """A site with no providers renders an empty login page, not a 500."""
        assert service(self.portal, self.request).reply()["items"] == []


class TestStart:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, configured, stub_metadata) -> None:
        self.portal = portal
        self.request = request_
        self.stub_metadata = stub_metadata

    def start(self, provider_id: str = "dex") -> dict:
        """Start a flow against one provider.

        :param provider_id: The provider to start against.
        :returns: The service's reply.
        """
        return service(self.portal, self.request, provider_id).reply()

    def stored_attempt(self) -> dict:
        """Return the attempt stored in the flow cookie.

        :returns: The serialized attempt.
        """
        stored = decode(self.request.response.cookies[COOKIE_NAME]["value"])
        return next(iter(stored[SESSION_KEY].values()))

    def test_returns_the_authorize_url(self):
        """Clicking a button yields somewhere to send the browser."""
        self.stub_metadata()

        result = self.start()

        assert result["provider"] == "dex"
        assert result["authorize_url"].startswith("http://dex:5556/dex/auth")

    def test_redirect_uri_is_the_configured_callback(self):
        """The provider must be sent the frontend route, not the portal URL:
        with Volto the two need not even share an origin."""
        self.stub_metadata()

        result = self.start()

        query = parse_qs(urlparse(result["authorize_url"]).query)
        assert query["redirect_uri"] == [CALLBACK_URL]

    def test_stores_the_attempt_in_a_signed_cookie(self):
        """The attempt is bound to this browser."""
        self.stub_metadata()

        result = self.start()

        state = parse_qs(urlparse(result["authorize_url"]).query)["state"][0]
        stored = decode(self.request.response.cookies[COOKIE_NAME]["value"])
        assert state in stored[SESSION_KEY]

    def test_came_from_is_carried(self):
        """Where the user was headed survives the round trip."""
        self.stub_metadata()
        self.request.form["came_from"] = f"{self.portal.absolute_url()}/some/page"

        self.start()

        assert self.stored_attempt()["came_from"].endswith("/some/page")

    def test_hostile_came_from_is_dropped(self):
        """And it is dropped before it is ever stored."""
        self.stub_metadata()
        self.request.form["came_from"] = "https://evil.example/phish"

        self.start()

        assert self.stored_attempt()["came_from"] == ""

    @pytest.mark.parametrize("provider_id", ["nope", "github"])
    def test_unknown_and_disabled_look_the_same(self, provider_id: str):
        """Which providers a site has configured is not worth probing for, so
        a disabled one answers exactly like one that does not exist."""
        result = self.start(provider_id)

        assert self.request.response.getStatus() == 404
        assert result["error"]["type"] == "Unknown provider"

    def test_a_driver_with_no_endpoints_is_not_an_outage(self, email_configured):
        """The email provider is magic-link only: its "provider" is a
        mailbox, so there is no authorization endpoint and there never will
        be. Reporting that as a bad gateway told a client to try again at
        something that cannot work, which is how a broken button survives.
        """
        result = self.start("email")

        assert self.request.response.getStatus() == 400
        assert result["error"]["type"] == "Provider cannot start this flow"

    def test_unreachable_provider_is_a_bad_gateway(self):
        """A provider that is down is the provider's fault, not the caller's."""
        self.stub_metadata(FlowError("dex: could not fetch discovery"))

        result = self.start()

        assert self.request.response.getStatus() == 502
        assert result["error"]["type"] == "Provider unavailable"

    def test_an_unset_callback_url_falls_back_to_the_default(self):
        """It defaults to the route this package's own frontend registers,
        so a site that installs both halves configures nothing."""
        self.stub_metadata()
        api.portal.set_registry_record(CALLBACK_URL_RECORD, "")

        result = self.start()

        assert self.request.response.getStatus() == 200
        assert "%2Flogin-identity" in result["authorize_url"] or (
            "/login-identity" in result["authorize_url"]
        )

    def test_a_malformed_callback_url_is_reported(self):
        """Neither a path nor an absolute URL: the provider would answer an
        opaque rejection long after the useful moment.

        Not a bad gateway, which is what this used to answer: no provider was
        ever contacted, and no number of retries will fix a registry record.
        """
        self.stub_metadata()
        api.portal.set_registry_record(CALLBACK_URL_RECORD, "login-identity")

        result = self.start()

        assert self.request.response.getStatus() == 400
        assert result["error"]["type"] == "Provider cannot start this flow"
        assert "callback_url" in result["error"]["message"]
