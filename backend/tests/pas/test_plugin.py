"""Integration tests for the PAS plugin (§4.1, I1/I3/I6/S4)."""

from Acquisition import aq_base
from . import CLAIMS
from . import DEX_IDENTITY
from . import GITHUB_IDENTITY
from . import OTHER_CLAIMS
from pas.plugins.identity.core.events import IExternalIdentityAuthenticated
from pas.plugins.identity.core.events import IIdentityLinked
from pas.plugins.identity.core.events import IIdentityUnlinked
from pas.plugins.identity.core.interfaces import IdentityCollision
from pas.plugins.identity.core.interfaces import IIdentityPlugin
from pas.plugins.identity.core.interfaces import LockoutRefused
from pas.plugins.identity.core.pas import CREDENTIALS_KEY
from pas.plugins.identity.core.pas import EXTRACTOR
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.core.pas.plugin import IdentityPlugin
from pas.plugins.identity.core.pas.plugin import mint_userid
from pas.plugins.identity.setuphandlers import ACTIVATED_INTERFACES
from pas.plugins.identity.setuphandlers import install_plugin
from pas.plugins.identity.setuphandlers import uninstall_plugin
from Products.PluggableAuthService.interfaces.plugins import IChallengePlugin
from zope.component import adapter
from zope.component import getGlobalSiteManager
from zope.interface import Interface

import pytest


@pytest.fixture()
def credentials():
    """Return credentials as the callback view deposits them."""
    provider, subject = DEX_IDENTITY
    return {
        "extractor": EXTRACTOR,
        "provider": provider,
        "subject": subject,
        "claims": CLAIMS,
    }


@pytest.fixture()
def recorded_events():
    """Record every identity event fired during a test."""
    events = []

    @adapter(Interface)
    def recorder(event):
        events.append(event)

    gsm = getGlobalSiteManager()
    gsm.registerHandler(recorder)
    yield events
    gsm.unregisterHandler(recorder)


def _of(name: str, events: list) -> list:
    """Return recorded events providing the named interface.

    :param name: Interface to filter by.
    :param events: Recorded events.
    :returns: Matching events.
    """
    return [e for e in events if name.providedBy(e)]


class TestUseridGenesis:
    """D10/I1 -- userids are random and permanent."""

    def test_is_uuid4_hex(self):
        """32 hex characters, as documented."""
        userid = mint_userid()

        assert len(userid) == 32
        assert set(userid) <= set("0123456789abcdef")

    def test_is_unique(self):
        """Minting twice never collides."""
        assert mint_userid() != mint_userid()

    def test_leaks_no_provider_information(self):
        """Nothing about the identity is derivable from the userid."""
        userid = mint_userid()

        assert "github" not in userid
        assert "erico" not in userid


class TestInstallation:
    def test_plugin_present(self, plugin: IdentityPlugin):
        """The default profile added the plugin to PAS."""
        assert isinstance(plugin, IdentityPlugin)
        assert IIdentityPlugin.providedBy(plugin)

    @pytest.mark.parametrize("interface", ACTIVATED_INTERFACES)
    def test_interfaces_activated(self, acl_users, interface):
        """Extraction, authentication and reset are live."""
        assert PLUGIN_ID in acl_users.plugins.listPluginIds(interface)

    def test_challenge_not_activated(self, acl_users):
        """Challenge is opt-in and stays off (§4.1)."""
        assert PLUGIN_ID not in acl_users.plugins.listPluginIds(IChallengePlugin)

    def test_install_is_idempotent(self, acl_users, plugin: IdentityPlugin):
        """Re-running install keeps the same object -- and its store."""
        plugin.store.add(*DEX_IDENTITY, "userid-1", CLAIMS)

        again = install_plugin(acl_users)

        assert aq_base(again) is aq_base(plugin)
        assert len(again.store) == 1

    def test_uninstall_removes_plugin(self, acl_users):
        """I8 -- uninstall leaves no plugin behind."""
        uninstall_plugin(acl_users)

        assert PLUGIN_ID not in acl_users.objectIds()

    def test_uninstall_deactivates_interfaces(self, acl_users):
        """No dangling registrations after removal."""
        uninstall_plugin(acl_users)

        for interface in ACTIVATED_INTERFACES:
            assert PLUGIN_ID not in acl_users.plugins.listPluginIds(interface)

    def test_uninstall_is_idempotent(self, acl_users):
        """Uninstalling twice is not an error."""
        uninstall_plugin(acl_users)
        uninstall_plugin(acl_users)

        assert PLUGIN_ID not in acl_users.objectIds()


class TestExtraction:
    """I6 -- extraction is a dict lookup, never network I/O."""

    def test_ordinary_request_yields_nothing(self, plugin: IdentityPlugin, portal):
        """A normal request carries no identity credentials."""
        assert plugin.extractCredentials(portal.REQUEST) == {}

    def test_callback_request_yields_credentials(self, plugin: IdentityPlugin, portal):
        """The callback view's deposit is picked up."""
        provider, subject = DEX_IDENTITY
        portal.REQUEST.other[CREDENTIALS_KEY] = {
            "provider": provider,
            "subject": subject,
            "claims": CLAIMS,
        }

        extracted = plugin.extractCredentials(portal.REQUEST)

        assert extracted["extractor"] == EXTRACTOR
        assert extracted["provider"] == provider
        assert extracted["subject"] == subject

    def test_claims_default_to_empty(self, plugin: IdentityPlugin, portal):
        """A deposit without claims is still usable."""
        provider, subject = DEX_IDENTITY
        portal.REQUEST.other[CREDENTIALS_KEY] = {
            "provider": provider,
            "subject": subject,
        }

        assert plugin.extractCredentials(portal.REQUEST)["claims"] == {}

    def test_request_without_other_is_safe(self, plugin: IdentityPlugin):
        """A bare object is not a crash -- PAS passes odd things around."""
        assert plugin.extractCredentials(object()) == {}


class TestAuthentication:
    def test_foreign_credentials_ignored(self, plugin: IdentityPlugin):
        """Credentials from another extractor are not ours to authenticate."""
        assert plugin.authenticateCredentials({"extractor": "other"}) is None

    def test_first_login_mints_userid(self, plugin: IdentityPlugin, credentials):
        """A never-seen identity yields a fresh principal."""
        userid, login = plugin.authenticateCredentials(credentials)

        assert len(userid) == 32
        assert login == userid

    def test_first_login_creates_plone_user(
        self, plugin: IdentityPlugin, acl_users, credentials
    ):
        """Core decorates ``source_users`` rather than enumerating itself (I5)."""
        userid, _ = plugin.authenticateCredentials(credentials)

        assert acl_users.source_users.getUserById(userid) is not None

    def test_first_login_seeds_properties(
        self, plugin: IdentityPlugin, acl_users, credentials
    ):
        """Fullname and email land in ``mutable_properties``."""
        userid, _ = plugin.authenticateCredentials(credentials)

        sheet = acl_users.mutable_properties.getPropertiesForUser(
            acl_users.getUserById(userid)
        )
        assert sheet.getProperty("fullname") == "Érico Andrei"
        assert sheet.getProperty("email") == "erico@plone.org"

    def test_first_login_stores_identity(self, plugin: IdentityPlugin, credentials):
        """The identity is linked to the new userid."""
        userid, _ = plugin.authenticateCredentials(credentials)

        assert plugin.store.userid_for(*DEX_IDENTITY) == userid

    def test_repeat_login_same_userid(self, plugin: IdentityPlugin, credentials):
        """I1 -- the userid is permanent across logins."""
        first, _ = plugin.authenticateCredentials(credentials)
        second, _ = plugin.authenticateCredentials(credentials)

        assert first == second

    def test_repeat_login_creates_no_second_user(
        self, plugin: IdentityPlugin, credentials
    ):
        """Logging in twice does not fork the account."""
        plugin.authenticateCredentials(credentials)
        plugin.authenticateCredentials(credentials)

        assert len(plugin.store) == 1

    def test_repeat_login_stamps_last_login(self, plugin: IdentityPlugin, credentials):
        """The second login is recorded on the identity."""
        plugin.authenticateCredentials(credentials)
        assert plugin.store.get(*DEX_IDENTITY).last_login is None

        plugin.authenticateCredentials(credentials)

        assert plugin.store.get(*DEX_IDENTITY).last_login is not None

    def test_userid_survives_changed_claims(self, plugin: IdentityPlugin, credentials):
        """I1 -- a renamed user keeps their userid."""
        first, _ = plugin.authenticateCredentials(credentials)

        renamed = {**credentials, "claims": {**CLAIMS, "email": "new@plone.org"}}
        second, _ = plugin.authenticateCredentials(renamed)

        assert first == second


class TestAuthenticationEvents:
    """§4.3 -- every successful login fires exactly one event."""

    def test_fires_once(self, plugin: IdentityPlugin, credentials, recorded_events):
        """One login, one event."""
        plugin.authenticateCredentials(credentials)

        assert len(_of(IExternalIdentityAuthenticated, recorded_events)) == 1

    def test_first_login_payload(
        self, plugin: IdentityPlugin, credentials, recorded_events
    ):
        """A brand new user is flagged as such."""
        userid, _ = plugin.authenticateCredentials(credentials)

        event = _of(IExternalIdentityAuthenticated, recorded_events)[0]
        assert event.userid == userid
        assert event.provider == DEX_IDENTITY[0]
        assert event.subject == DEX_IDENTITY[1]
        assert event.is_new_user is True
        assert event.is_new_identity is True

    def test_repeat_login_payload(
        self, plugin: IdentityPlugin, credentials, recorded_events
    ):
        """A returning user is not flagged as new."""
        plugin.authenticateCredentials(credentials)
        plugin.authenticateCredentials(credentials)

        event = _of(IExternalIdentityAuthenticated, recorded_events)[1]
        assert event.is_new_user is False
        assert event.is_new_identity is False

    def test_claims_travel_with_event(
        self, plugin: IdentityPlugin, credentials, recorded_events
    ):
        """Consumers read claims off the event, not out of the store."""
        plugin.authenticateCredentials(credentials)

        event = _of(IExternalIdentityAuthenticated, recorded_events)[0]
        assert event.claims["fullname"] == "Érico Andrei"


class TestLinking:
    """Gate 2 -- one human, several providers."""

    @pytest.fixture()
    def userid(self, plugin: IdentityPlugin, credentials) -> str:
        """Return a userid with one Dex identity already linked."""
        userid, _ = plugin.authenticateCredentials(credentials)
        return userid

    def test_link_second_provider(self, plugin: IdentityPlugin, userid: str):
        """Both identities resolve to the same userid -- the whole point."""
        plugin.link(userid, *GITHUB_IDENTITY, CLAIMS)

        assert plugin.store.userid_for(*GITHUB_IDENTITY) == userid
        assert plugin.store.userid_for(*DEX_IDENTITY) == userid

    def test_link_fires_event(
        self, plugin: IdentityPlugin, userid: str, recorded_events
    ):
        """``IdentityLinked`` carries the new identity."""
        plugin.link(userid, *GITHUB_IDENTITY, CLAIMS)

        events = _of(IIdentityLinked, recorded_events)
        assert len(events) == 1
        assert events[0].provider == "github"

    def test_link_collision_is_hard_error(
        self, plugin: IdentityPlugin, userid: str, credentials
    ):
        """I3/S3 -- an identity is never moved between accounts."""
        other = {
            **credentials,
            "subject": "other-subject",
            "claims": OTHER_CLAIMS,
        }
        other_userid, _ = plugin.authenticateCredentials(other)
        plugin.link(other_userid, *GITHUB_IDENTITY, OTHER_CLAIMS)

        with pytest.raises(IdentityCollision):
            plugin.link(userid, *GITHUB_IDENTITY, CLAIMS)

    def test_login_via_linked_provider(
        self, plugin: IdentityPlugin, userid: str, credentials
    ):
        """Logging in with the second provider lands on the same account."""
        plugin.link(userid, *GITHUB_IDENTITY, CLAIMS)
        provider, subject = GITHUB_IDENTITY

        again, _ = plugin.authenticateCredentials({
            **credentials,
            "provider": provider,
            "subject": subject,
        })

        assert again == userid


class TestUnlinking:
    """S4 -- unlinking must not lock anyone out."""

    @pytest.fixture()
    def userid(self, plugin: IdentityPlugin, credentials) -> str:
        """Return a userid with two identities linked."""
        userid, _ = plugin.authenticateCredentials(credentials)
        plugin.link(userid, *GITHUB_IDENTITY, CLAIMS)
        return userid

    def test_unlink_removes_identity(self, plugin: IdentityPlugin, userid: str):
        """The identity stops resolving."""
        plugin.unlink(userid, *GITHUB_IDENTITY)

        assert plugin.store.userid_for(*GITHUB_IDENTITY) is None

    def test_unlink_fires_event(
        self, plugin: IdentityPlugin, userid: str, recorded_events
    ):
        """``IdentityUnlinked`` names what went away."""
        plugin.unlink(userid, *GITHUB_IDENTITY)

        events = _of(IIdentityUnlinked, recorded_events)
        assert len(events) == 1
        assert events[0].subject == GITHUB_IDENTITY[1]

    def test_unlink_keeps_other_identity(self, plugin: IdentityPlugin, userid: str):
        """The remaining way in is untouched."""
        plugin.unlink(userid, *GITHUB_IDENTITY)

        assert plugin.store.userid_for(*DEX_IDENTITY) == userid

    def test_unlink_last_identity_refused(self, plugin: IdentityPlugin, userid: str):
        """S4 -- the last way in cannot be removed."""
        plugin.unlink(userid, *GITHUB_IDENTITY)

        with pytest.raises(LockoutRefused):
            plugin.unlink(userid, *DEX_IDENTITY)

    def test_refused_unlink_changes_nothing(self, plugin: IdentityPlugin, userid: str):
        """A refused unlink leaves the account intact."""
        plugin.unlink(userid, *GITHUB_IDENTITY)

        with pytest.raises(LockoutRefused):
            plugin.unlink(userid, *DEX_IDENTITY)

        assert plugin.store.userid_for(*DEX_IDENTITY) == userid

    def test_unlink_someone_elses_identity_refused(
        self, plugin: IdentityPlugin, userid: str
    ):
        """A user cannot unlink an identity they do not own."""
        with pytest.raises(KeyError):
            plugin.unlink("some-other-userid", *GITHUB_IDENTITY)

    def test_unlink_unknown_identity_refused(self, plugin: IdentityPlugin, userid: str):
        """Unlinking something never linked is an error."""
        with pytest.raises(KeyError):
            plugin.unlink(userid, "google", "never-seen")

    def test_can_unlink_reports_true_with_sibling(
        self, plugin: IdentityPlugin, userid: str
    ):
        """The guard agrees with what ``unlink`` does."""
        assert plugin.can_unlink(userid, *GITHUB_IDENTITY) is True

    def test_can_unlink_reports_false_for_last(
        self, plugin: IdentityPlugin, userid: str
    ):
        """The guard refuses the last identity."""
        plugin.unlink(userid, *GITHUB_IDENTITY)

        assert plugin.can_unlink(userid, *DEX_IDENTITY) is False


class TestVerifiedEmail:
    """S4's other escape hatch: a verified email identity."""

    def test_absent_by_default(self, plugin: IdentityPlugin, credentials):
        """An OIDC-only account has no email identity."""
        userid, _ = plugin.authenticateCredentials(credentials)

        assert plugin.has_verified_email(userid) is False

    def test_present_after_email_link(self, plugin: IdentityPlugin, credentials):
        """Linking a magic-link identity is what satisfies the guard."""
        userid, _ = plugin.authenticateCredentials(credentials)
        plugin.link(userid, "email", "erico@plone.org", CLAIMS)

        assert plugin.has_verified_email(userid) is True

    def test_email_identity_permits_unlink_of_last_provider(
        self, plugin: IdentityPlugin, credentials
    ):
        """With an email identity present, the OIDC one can go."""
        userid, _ = plugin.authenticateCredentials(credentials)
        plugin.link(userid, "email", "erico@plone.org", CLAIMS)

        plugin.unlink(userid, *DEX_IDENTITY)

        assert plugin.store.userid_for(*DEX_IDENTITY) is None


class TestCredentialsReset:
    def test_reset_clears_deposit(self, plugin: IdentityPlugin, portal):
        """Logging out drops anything this plugin left on the request."""
        portal.REQUEST.other[CREDENTIALS_KEY] = {"provider": "x", "subject": "y"}

        plugin.resetCredentials(portal.REQUEST, portal.REQUEST.response)

        assert CREDENTIALS_KEY not in portal.REQUEST.other

    def test_reset_without_deposit_is_safe(self, plugin: IdentityPlugin, portal):
        """Resetting an ordinary request is a no-op."""
        plugin.resetCredentials(portal.REQUEST, portal.REQUEST.response)

        assert CREDENTIALS_KEY not in portal.REQUEST.other

    def test_reset_on_bare_object_is_safe(self, plugin: IdentityPlugin):
        """PAS passes odd things around; do not crash on them."""
        plugin.resetCredentials(object(), object())


class TestChallenge:
    """§4.1 -- opt-in, off by default."""

    def test_disabled_by_default(self, plugin: IdentityPlugin, portal):
        """The stock login form stays in charge."""
        assert plugin.challenge_enabled is False
        assert plugin.challenge(portal.REQUEST, portal.REQUEST.response) is False

    def test_enabled_redirects_to_picker(self, plugin: IdentityPlugin, portal):
        """Once on, an unauthorized request goes to the provider picker."""
        plugin.challenge_enabled = True

        handled = plugin.challenge(portal.REQUEST, portal.REQUEST.response)

        assert handled is True
        assert "@@identity-login" in portal.REQUEST.response.getHeader("Location")

    def test_came_from_is_preserved(self, plugin: IdentityPlugin, portal):
        """The user returns where they were headed."""
        plugin.challenge_enabled = True
        portal.REQUEST["ACTUAL_URL"] = f"{portal.absolute_url()}/some-page"

        plugin.challenge(portal.REQUEST, portal.REQUEST.response)

        assert "came_from=" in portal.REQUEST.response.getHeader("Location")
