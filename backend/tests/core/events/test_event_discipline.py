"""Every event fires exactly once per triggering action.

The event contract is this package's public API, and the audit log is fed
from it. A double-fire duplicates audit entries and runs a subscriber's side
effects twice; a missing fire makes an action invisible to every integrator.
Neither shows up in an ordinary test, because both leave the *store* correct.
"""

from .. import body
from ..services import DEX_METADATA
from ..services import EMAIL_PROVIDER_RECORD
from ..services import USERINFO
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.events import IIdentityEvent
from pas.plugins.identity.core.flows import magiclink
from pas.plugins.identity.core.flows.session import COOKIE_NAME
from pas.plugins.identity.core.interfaces import IdentityCollision
from pas.plugins.identity.core.interfaces import LockoutRefused
from pas.plugins.identity.core.services.callback.post import IdentityCallback
from pas.plugins.identity.core.services.login.get import LoginProviders
from pas.plugins.identity.core.services.magiclink.confirm import MagicLinkConfirm
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from plone import api
from urllib.parse import parse_qs
from urllib.parse import urlparse
from zope.component import adapter
from zope.component import getGlobalSiteManager
from zope.interface import Interface

import pytest


@pytest.fixture
def fired():
    """Record every identity event fired during a test.

    :returns: The list the recorder appends to.
    """
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


class TestLogin:
    @pytest.fixture(autouse=True)
    def _setup(
        self, portal, request_, fired, configured, stub_metadata, stub_provider
    ) -> None:
        self.portal = portal
        self.request = request_
        self.fired = fired
        stub_metadata(DEX_METADATA)
        stub_provider(USERINFO)
        view = LoginProviders(portal, request_)
        view.publishTraverse(request_, "dex")
        url = view.reply()["authorize_url"]
        request_.cookies[COOKIE_NAME] = request_.response.cookies[COOKIE_NAME]["value"]
        self.flow = parse_qs(urlparse(url).query)["state"][0]

    def callback(self, state: str) -> None:
        """Post a callback with the given state.

        :param state: The state to send back.
        """
        body(self.request, {"provider": "dex", "code": "c", "state": state})
        IdentityCallback(self.portal, self.request).reply()

    def test_first_login_fires_exactly_one_event(self):
        """Minting an account is one action, not two."""
        self.callback(self.flow)

        assert kinds(self.fired) == ["ExternalIdentityAuthenticated"]

    def test_refused_login_fires_nothing(self):
        """A refusal is not an authentication, and must not look like one to
        a subscriber."""
        self.callback("forged")

        assert kinds(self.fired) == []


class TestLinking:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, fired) -> None:
        self.portal = portal
        self.fired = fired
        self.plugin = api.portal.get_tool("acl_users")["identity"]

    def test_link_fires_exactly_one_event(self):
        """Attaching an identity is one action."""
        self.plugin.link("userid-1", "github", "1234567", {})

        assert kinds(self.fired) == ["IdentityLinked"]

    def test_unlink_fires_exactly_one_event(self):
        """So is detaching one."""
        self.plugin.link("userid-1", "github", "1234567", {})
        self.plugin.link("userid-1", "google", "abc", {})
        self.fired.clear()

        self.plugin.unlink("userid-1", "github", "1234567")

        assert kinds(self.fired) == ["IdentityUnlinked"]

    def test_refused_unlink_fires_nothing(self):
        """A refused unlink left the account alone, and subscribers
        must not be told otherwise."""
        self.plugin.link("userid-1", "github", "1234567", {})
        self.fired.clear()

        with pytest.raises(LockoutRefused):
            self.plugin.unlink("userid-1", "github", "1234567")

        assert kinds(self.fired) == []

    def test_collision_fires_nothing(self):
        """Nothing was linked, so nothing is announced."""
        self.plugin.link("userid-1", "github", "1234567", {})
        self.fired.clear()

        with pytest.raises(IdentityCollision):
            self.plugin.link("userid-2", "github", "1234567", {})

        assert kinds(self.fired) == []


class TestMagicLink:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, fired, configured) -> None:
        self.portal = portal
        self.request = request_
        self.fired = fired
        self.plugin = api.portal.get_tool("acl_users")["identity"]
        set_providers([
            *get_providers(),
            ProviderConfig.deserialize(EMAIL_PROVIDER_RECORD),
        ])

    def confirm(self) -> None:
        """Issue a magic link and redeem it."""
        token, _ = magiclink.issue("erico@plone.org")
        body(self.request, {"token": token})
        MagicLinkConfirm(self.portal, self.request).reply()

    def test_confirm_fires_exactly_one_event(self):
        """A magic-link login is an authentication like any other."""
        token, _ = magiclink.issue("erico@plone.org")
        self.fired.clear()

        body(self.request, {"token": token})
        MagicLinkConfirm(self.portal, self.request).reply()

        assert kinds(self.fired) == ["ExternalIdentityAuthenticated"]

    def test_repeat_confirm_still_fires_once(self):
        """A returning user authenticates once per login, not once per
        identity they happen to own."""
        for _ in range(2):
            self.confirm()

        assert kinds(self.fired) == [
            "ExternalIdentityAuthenticated",
            "ExternalIdentityAuthenticated",
        ]
        assert len(self.plugin.store.identities_for(self.fired[0].userid)) == 1


class TestPayloads:
    """What a subscriber is entitled to read off each event."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, fired) -> None:
        self.portal = portal
        self.fired = fired
        self.plugin = api.portal.get_tool("acl_users")["identity"]

    def test_authentication_payload(self):
        """Every field the audit log and a claims-sync subscriber need."""
        self.plugin.authenticateCredentials({
            "extractor": "pas.plugins.identity",
            "provider": "dex",
            "subject": "subject-1",
            "claims": {"email": "erico@plone.org", "email_verified": True},
        })

        event = self.fired[0]
        assert event.provider == "dex"
        assert event.subject == "subject-1"
        assert event.claims["email"] == "erico@plone.org"
        assert event.is_new_user is True
        assert event.is_new_identity is True
        assert event.userid

    def test_link_payload(self):
        """Linking names the identity that was attached."""
        self.plugin.link("userid-1", EMAIL_PROVIDER, "Erico@Plone.ORG", {"a": 1})

        event = self.fired[0]
        assert event.userid == "userid-1"
        assert event.provider == EMAIL_PROVIDER
        assert event.claims == {"a": 1}

    def test_unlink_payload(self):
        """Unlinking names it too, and carries no claims."""
        self.plugin.link("userid-1", "github", "1234567", {})
        self.plugin.link("userid-1", "google", "abc", {})
        self.fired.clear()

        self.plugin.unlink("userid-1", "github", "1234567")

        event = self.fired[0]
        assert event.userid == "userid-1"
        assert event.provider == "github"
        assert event.subject == "1234567"
        assert not hasattr(event, "claims")
