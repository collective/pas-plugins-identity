"""Gate 4: every event fires exactly once per triggering action.

The event contract is this package's public API, and the audit log is fed
from it. A double-fire duplicates audit entries and runs a subscriber's side
effects twice; a missing fire makes an action invisible to every integrator.
Neither shows up in an ordinary test, because both leave the *store* correct.
"""

from ..services import DEX_METADATA
from ..services import USERINFO
from ..services.conftest import body
from pas.plugins.identity.core.events import IIdentityEvent
from pas.plugins.identity.core.flows.session import COOKIE_NAME
from pas.plugins.identity.core.services.callback import IdentityCallback
from pas.plugins.identity.core.services.login import LoginProviders
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from plone import api
from urllib.parse import parse_qs
from urllib.parse import urlparse
from zope.component import adapter
from zope.component import getGlobalSiteManager
from zope.interface import Interface

import pytest


@pytest.fixture()
def fired():
    """Record every identity event fired during a test."""
    events = []

    @adapter(Interface)
    def recorder(event):
        if IIdentityEvent.providedBy(event):
            events.append(event)

    gsm = getGlobalSiteManager()
    gsm.registerHandler(recorder)
    yield events
    gsm.unregisterHandler(recorder)


def kinds(events) -> list[str]:
    """Name each recorded event by its class.

    :param events: Recorded events.
    :returns: One class name per event, in order.
    """
    return [type(event).__name__ for event in events]


def plugin():
    """Return the identity plugin.

    :returns: The plugin.
    """
    return api.portal.get_tool("acl_users")["identity"]


class TestLogin:
    @pytest.fixture()
    def flow(self, portal, request_, configured, stub_metadata, stub_provider):
        """Start a flow and return its state."""
        stub_metadata(DEX_METADATA)
        stub_provider(USERINFO)
        view = LoginProviders(portal, request_)
        view.publishTraverse(request_, "dex")
        url = view.reply()["authorize_url"]
        request_.cookies[COOKIE_NAME] = request_.response.cookies[COOKIE_NAME]["value"]
        return parse_qs(urlparse(url).query)["state"][0]

    def test_first_login_fires_exactly_one_event(self, portal, request_, flow, fired):
        """Minting an account is one action, not two."""
        body(request_, {"provider": "dex", "code": "c", "state": flow})
        IdentityCallback(portal, request_).reply()

        assert kinds(fired) == ["ExternalIdentityAuthenticated"]

    def test_refused_login_fires_nothing(self, portal, request_, flow, fired):
        """A refusal is not an authentication, and must not look like one to
        a subscriber."""
        body(request_, {"provider": "dex", "code": "c", "state": "forged"})
        IdentityCallback(portal, request_).reply()

        assert kinds(fired) == []


class TestLinking:
    def test_link_fires_exactly_one_event(self, portal, fired):
        """Attaching an identity is one action."""
        plugin().link("userid-1", "github", "1234567", {})

        assert kinds(fired) == ["IdentityLinked"]

    def test_unlink_fires_exactly_one_event(self, portal, fired):
        """So is detaching one."""
        identity = plugin()
        identity.link("userid-1", "github", "1234567", {})
        identity.link("userid-1", "google", "abc", {})
        fired.clear()

        identity.unlink("userid-1", "github", "1234567")

        assert kinds(fired) == ["IdentityUnlinked"]

    def test_refused_unlink_fires_nothing(self, portal, fired):
        """S4 -- a refused unlink left the account alone, and subscribers
        must not be told otherwise."""
        from pas.plugins.identity.core.interfaces import LockoutRefused

        identity = plugin()
        identity.link("userid-1", "github", "1234567", {})
        fired.clear()

        with pytest.raises(LockoutRefused):
            identity.unlink("userid-1", "github", "1234567")

        assert kinds(fired) == []

    def test_collision_fires_nothing(self, portal, fired):
        """I3 -- nothing was linked, so nothing is announced."""
        from pas.plugins.identity.core.interfaces import IdentityCollision

        identity = plugin()
        identity.link("userid-1", "github", "1234567", {})
        fired.clear()

        with pytest.raises(IdentityCollision):
            identity.link("userid-2", "github", "1234567", {})

        assert kinds(fired) == []


class TestMagicLink:
    def test_confirm_fires_exactly_one_event(self, portal, request_, configured, fired):
        """A magic-link login is an authentication like any other."""
        from ..services.test_magiclink import EMAIL_PROVIDER_RECORD
        from pas.plugins.identity.core.controlpanel import get_providers
        from pas.plugins.identity.core.controlpanel import ProviderConfig
        from pas.plugins.identity.core.controlpanel import set_providers
        from pas.plugins.identity.core.flows import magiclink
        from pas.plugins.identity.core.services.magiclink import MagicLinkConfirm

        set_providers([
            *get_providers(),
            ProviderConfig.deserialize(EMAIL_PROVIDER_RECORD),
        ])
        token, _ = magiclink.issue("erico@plone.org")
        fired.clear()

        body(request_, {"token": token})
        MagicLinkConfirm(portal, request_).reply()

        assert kinds(fired) == ["ExternalIdentityAuthenticated"]

    def test_repeat_confirm_still_fires_once(self, portal, request_, configured, fired):
        """A returning user authenticates once per login, not once per
        identity they happen to own."""
        from ..services.test_magiclink import EMAIL_PROVIDER_RECORD
        from pas.plugins.identity.core.controlpanel import get_providers
        from pas.plugins.identity.core.controlpanel import ProviderConfig
        from pas.plugins.identity.core.controlpanel import set_providers
        from pas.plugins.identity.core.flows import magiclink
        from pas.plugins.identity.core.services.magiclink import MagicLinkConfirm

        set_providers([
            *get_providers(),
            ProviderConfig.deserialize(EMAIL_PROVIDER_RECORD),
        ])
        for _ in range(2):
            token, _ = magiclink.issue("erico@plone.org")
            body(request_, {"token": token})
            MagicLinkConfirm(portal, request_).reply()

        assert kinds(fired) == [
            "ExternalIdentityAuthenticated",
            "ExternalIdentityAuthenticated",
        ]
        assert len(plugin().store.identities_for(fired[0].userid)) == 1


class TestPayloads:
    """What a subscriber is entitled to read off each event."""

    def test_authentication_payload(self, portal, fired):
        """Every field the audit log and a claims-sync subscriber need."""
        plugin().authenticateCredentials({
            "extractor": "pas.plugins.identity",
            "provider": "dex",
            "subject": "subject-1",
            "claims": {"email": "erico@plone.org", "email_verified": True},
        })

        event = fired[0]
        assert event.provider == "dex"
        assert event.subject == "subject-1"
        assert event.claims["email"] == "erico@plone.org"
        assert event.is_new_user is True
        assert event.is_new_identity is True
        assert event.userid

    def test_link_payload(self, portal, fired):
        """Linking names the identity that was attached."""
        plugin().link("userid-1", EMAIL_PROVIDER, "Erico@Plone.ORG", {"a": 1})

        event = fired[0]
        assert event.userid == "userid-1"
        assert event.provider == EMAIL_PROVIDER
        assert event.claims == {"a": 1}

    def test_unlink_payload(self, portal, fired):
        """Unlinking names it too, and carries no claims."""
        identity = plugin()
        identity.link("userid-1", "github", "1234567", {})
        identity.link("userid-1", "google", "abc", {})
        fired.clear()

        identity.unlink("userid-1", "github", "1234567")

        event = fired[0]
        assert event.userid == "userid-1"
        assert event.provider == "github"
        assert event.subject == "1234567"
        assert not hasattr(event, "claims")
