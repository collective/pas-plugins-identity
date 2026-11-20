"""The providers as options of plone.restapi's ``GET @login``.

Asked through plone.restapi's own service rather than the adapter, because
what a client sees is whatever ``getAdapters`` finds: an adapter that is
right but not registered would pass a test of the class and list nothing.
"""

from .. import body
from . import ADDRESS
from . import EMAIL_PROVIDER_RECORD
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.services.login.get import LoginProviders
from pas.plugins.identity.core.services.magiclink.post import MagicLinkSend
from plone.restapi.interfaces import ILoginProviders
from zope.component import getAdapters

import pytest


#: A second usable provider, so order and titles have something to compare.
SECOND_PROVIDER = {
    "id": "dex-second",
    "driver": "oidc-generic",
    "title": "Dex (second)",
    "enabled": True,
    "config": {
        "issuer": "http://dex:5556/dex",
        "client_id": "plone-second",
        "client_secret": "plone-second-secret",
        "scope": ["openid", "email", "profile"],
    },
}


def login_options(portal) -> list[dict]:
    """Collect the ``@login`` options the way plone.restapi's service does.

    plone.rest builds the service class itself, so it cannot be constructed
    here; its whole body is this lookup over every named adapter.

    :param portal: The Plone site.
    :returns: Every option, from every plugin.
    """
    options: list[dict] = []
    for _name, adapter in getAdapters((portal,), ILoginProviders):
        options.extend(adapter.get_providers())
    return options


def login_providers_service(portal, request, provider_id: str | None = None):
    """Build ``@login-providers``, optionally traversed to one provider.

    :param portal: The Plone site.
    :param request: The current request.
    :param provider_id: Provider to traverse to, if any.
    :returns: The service.
    """
    view = LoginProviders(portal, request)
    if provider_id is not None:
        view.publishTraverse(request, provider_id)
    return view


class TestLoginOptions:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, configured) -> None:
        self.portal = portal
        self.request = request_

    def options(self) -> list[dict]:
        """Return this package's entries in ``GET @login``.

        :returns: The options whose ``plugin`` is ours.
        """
        return [e for e in login_options(self.portal) if e["plugin"] == "identity"]

    def listing(self) -> list[dict]:
        """Return the ``@login-providers`` items.

        :returns: The listing's items.
        """
        return login_providers_service(self.portal, self.request).reply()["items"]

    def add(self, *records: dict) -> None:
        """Configure more providers after the fixture's.

        :param records: Provider records to append.
        """
        set_providers([
            *get_providers(),
            *(ProviderConfig.deserialize(record) for record in records),
        ])

    def test_lists_the_enabled_provider(self):
        """The ordinary case: Dex is enabled, GitHub is not."""
        assert [entry["id"] for entry in self.options()] == ["dex"]

    def test_entry_carries_what_a_button_needs(self):
        """The four keys ``ILoginProviders`` documents, plus ``flow`` and what
        the login page draws the button with: the driver, and the icon and
        colours grouped under ``style``. No configuration."""
        (entry,) = self.options()

        assert entry == {
            "id": "dex",
            "plugin": "identity",
            "title": "Dex",
            "url": f"{self.portal.absolute_url()}/@login-providers/dex",
            "flow": "redirect",
            "driver": "oidc-generic",
            "style": entry["style"],
        }
        assert set(entry["style"]) == {"icon", "background_color", "foreground_color"}

    def test_matches_the_login_page(self):
        """Same providers, order, titles, drivers and styles as
        ``@login-providers``: the login page could be drawn from either."""
        self.add(SECOND_PROVIDER, EMAIL_PROVIDER_RECORD)
        keys = ("id", "title", "driver")
        styles = ("icon", "background_color", "foreground_color")

        expected = [
            (*(item[k] for k in keys), {k: item[k] for k in styles})
            for item in self.listing()
        ]

        assert [(*(e[k] for k in keys), e["style"]) for e in self.options()] == (
            expected
        )
        assert [row[0] for row in expected] == ["dex", "dex-second", "email"]

    def test_the_email_provider_is_an_email_flow(self):
        """Magic link has nowhere to send the browser, so its ``url`` is the
        endpoint that mails the link, and ``flow`` says so."""
        self.add(EMAIL_PROVIDER_RECORD)

        entry = next(e for e in self.options() if e["id"] == "email")

        assert entry["flow"] == "email"
        assert entry["url"] == f"{self.portal.absolute_url()}/@magic-link"

    def test_the_email_url_mails_a_link(self, mailbox):
        """Following an email entry's ``url`` as documented sends a link."""
        self.add(EMAIL_PROVIDER_RECORD)
        entry = next(e for e in self.options() if e["id"] == "email")
        assert entry["url"].endswith("/@magic-link")

        body(self.request, {"email": ADDRESS})
        MagicLinkSend(self.portal, self.request).reply()

        assert self.request.response.getStatus() == 200
        assert [message["To"] for message in mailbox()] == [ADDRESS]

    def test_a_driver_with_no_way_to_start_is_left_out(self, monkeypatch):
        """A driver from another package with no endpoints and no mailbox has
        no URL to give; an entry for it could only fail."""
        from pas.plugins.identity.core.services.login import options

        self.add(SECOND_PROVIDER)
        monkeypatch.setattr(
            options, "has_endpoints", lambda p: p.provider_id != "dex-second"
        )

        assert [e["id"] for e in self.options()] == ["dex"]

    def test_a_provider_hidden_from_the_login_page_is_hidden_here(self):
        """``show_in_login`` answers both listings' question."""
        self.add({**SECOND_PROVIDER, "show_in_login": False})

        assert "dex-second" not in [item["id"] for item in self.listing()]
        assert "dex-second" not in [entry["id"] for entry in self.options()]

    def test_a_redirect_url_starts_a_flow(self, stub_metadata):
        """A client that follows a ``redirect`` entry's ``url`` gets somewhere
        to send the browser."""
        stub_metadata()
        (entry,) = self.options()
        provider_id = entry["url"].rsplit("/", 1)[-1]

        result = login_providers_service(self.portal, self.request, provider_id).reply()

        assert self.request.response.getStatus() == 200
        assert result["authorize_url"].startswith("http://dex:5556/dex/auth")


class TestLoginOptionsWithoutProviders:
    def test_an_empty_site_offers_nothing(self, portal, request_):
        """No providers, no options -- and no error in somebody else's
        endpoint."""
        assert [e for e in login_options(portal) if e["plugin"] == "identity"] == []
