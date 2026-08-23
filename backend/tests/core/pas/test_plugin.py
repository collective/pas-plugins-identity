"""Integration tests for the PAS plugin."""

from . import CLAIMS
from . import DEX_IDENTITY
from . import GITHUB_IDENTITY
from . import OTHER_CLAIMS
from Acquisition import aq_base
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
from plone import api
from Products.PluggableAuthService.interfaces.plugins import IChallengePlugin

import pytest


@pytest.fixture
def credentials():
    """Return credentials as the callback view deposits them.

    :returns: The credentials mapping.
    """
    provider, subject = DEX_IDENTITY
    return {
        "extractor": EXTRACTOR,
        "provider": provider,
        "subject": subject,
        "claims": CLAIMS,
    }


def _of(name: str, events: list) -> list:
    """Return recorded events providing the named interface.

    :param name: Interface to filter by.
    :param events: Recorded events.
    :returns: Matching events.
    """
    return [e for e in events if name.providedBy(e)]


class TestUseridGenesis:
    """Userids are random and permanent."""

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
    @pytest.fixture(autouse=True)
    def _setup(self, acl_users, plugin: IdentityPlugin) -> None:
        self.acl_users = acl_users
        self.plugin = plugin

    def test_plugin_present(self):
        """The default profile added the plugin to PAS."""
        assert isinstance(self.plugin, IdentityPlugin)
        assert IIdentityPlugin.providedBy(self.plugin)

    @pytest.mark.parametrize("interface", ACTIVATED_INTERFACES)
    def test_interfaces_activated(self, interface):
        """Extraction, authentication and reset are live."""
        assert PLUGIN_ID in self.acl_users.plugins.listPluginIds(interface)

    def test_challenge_not_activated(self):
        """Challenge is opt-in and stays off."""
        assert PLUGIN_ID not in self.acl_users.plugins.listPluginIds(IChallengePlugin)

    def test_install_is_idempotent(self):
        """Re-running install keeps the same object -- and its store."""
        self.plugin.store.add(*DEX_IDENTITY, "userid-1", CLAIMS)

        again = install_plugin(self.acl_users)

        assert aq_base(again) is aq_base(self.plugin)
        assert len(again.store) == 1

    def test_uninstall_removes_plugin(self):
        """Uninstall leaves no plugin behind."""
        uninstall_plugin(self.acl_users)

        assert PLUGIN_ID not in self.acl_users.objectIds()

    def test_uninstall_deactivates_interfaces(self):
        """No dangling registrations after removal."""
        uninstall_plugin(self.acl_users)

        for interface in ACTIVATED_INTERFACES:
            assert PLUGIN_ID not in self.acl_users.plugins.listPluginIds(interface)

    def test_uninstall_is_idempotent(self):
        """Uninstalling twice is not an error."""
        uninstall_plugin(self.acl_users)
        uninstall_plugin(self.acl_users)

        assert PLUGIN_ID not in self.acl_users.objectIds()


class TestExtraction:
    """Extraction is a dict lookup, never network I/O."""

    @pytest.fixture(autouse=True)
    def _setup(self, plugin: IdentityPlugin, portal, http_request) -> None:
        self.plugin = plugin
        self.portal = portal
        self.request = http_request

    def test_ordinary_request_yields_nothing(self):
        """A normal request carries no identity credentials."""
        assert self.plugin.extractCredentials(self.request) == {}

    def test_callback_request_yields_credentials(self):
        """The callback view's deposit is picked up."""
        provider, subject = DEX_IDENTITY
        self.request.other[CREDENTIALS_KEY] = {
            "provider": provider,
            "subject": subject,
            "claims": CLAIMS,
        }

        extracted = self.plugin.extractCredentials(self.request)

        assert extracted["extractor"] == EXTRACTOR
        assert extracted["provider"] == provider
        assert extracted["subject"] == subject

    def test_claims_default_to_empty(self):
        """A deposit without claims is still usable."""
        provider, subject = DEX_IDENTITY
        self.request.other[CREDENTIALS_KEY] = {
            "provider": provider,
            "subject": subject,
        }

        assert self.plugin.extractCredentials(self.request)["claims"] == {}

    def test_request_without_other_is_safe(self):
        """A bare object is not a crash -- PAS passes odd things around."""
        assert self.plugin.extractCredentials(object()) == {}


class TestAuthentication:
    @pytest.fixture(autouse=True)
    def _setup(self, plugin: IdentityPlugin, acl_users, credentials) -> None:
        self.plugin = plugin
        self.acl_users = acl_users
        self.credentials = credentials

    def test_foreign_credentials_ignored(self):
        """Credentials from another extractor are not ours to authenticate."""
        assert self.plugin.authenticateCredentials({"extractor": "other"}) is None

    def test_first_login_mints_userid(self):
        """A never-seen identity yields a fresh principal."""
        userid, login = self.plugin.authenticateCredentials(self.credentials)

        assert len(userid) == 32
        assert login == userid

    def test_first_login_creates_plone_user(self):
        """Core decorates ``source_users`` rather than enumerating itself."""
        userid, _ = self.plugin.authenticateCredentials(self.credentials)

        assert self.acl_users.source_users.getUserById(userid) is not None

    def test_first_login_seeds_properties(self):
        """Fullname and email land in ``mutable_properties``."""
        userid, _ = self.plugin.authenticateCredentials(self.credentials)

        sheet = self.acl_users.mutable_properties.getPropertiesForUser(
            self.acl_users.getUserById(userid)
        )
        assert sheet.getProperty("fullname") == "Érico Andrei"
        assert sheet.getProperty("email") == "erico@plone.org"

    def test_first_login_stores_identity(self):
        """The identity is linked to the new userid."""
        userid, _ = self.plugin.authenticateCredentials(self.credentials)

        assert self.plugin.store.userid_for(*DEX_IDENTITY) == userid

    def test_repeat_login_same_userid(self):
        """The userid is permanent across logins."""
        first, _ = self.plugin.authenticateCredentials(self.credentials)
        second, _ = self.plugin.authenticateCredentials(self.credentials)

        assert first == second

    def test_repeat_login_creates_no_second_user(self):
        """Logging in twice does not fork the account."""
        self.plugin.authenticateCredentials(self.credentials)
        self.plugin.authenticateCredentials(self.credentials)

        assert len(self.plugin.store) == 1

    def test_repeat_login_stamps_last_login(self):
        """The second login is recorded on the identity."""
        self.plugin.authenticateCredentials(self.credentials)
        assert self.plugin.store.get(*DEX_IDENTITY).last_login is None

        self.plugin.authenticateCredentials(self.credentials)

        assert self.plugin.store.get(*DEX_IDENTITY).last_login is not None

    def test_userid_survives_changed_claims(self):
        """A renamed user keeps their userid."""
        first, _ = self.plugin.authenticateCredentials(self.credentials)

        renamed = {**self.credentials, "claims": {**CLAIMS, "email": "new@plone.org"}}
        second, _ = self.plugin.authenticateCredentials(renamed)

        assert first == second


class TestAuthenticationEvents:
    """Every successful login fires exactly one event."""

    @pytest.fixture(autouse=True)
    def _setup(self, plugin: IdentityPlugin, credentials, recorded_events) -> None:
        self.plugin = plugin
        self.credentials = credentials
        self.recorded_events = recorded_events

    def authenticated(self) -> list:
        """Return the recorded authentication events.

        :returns: Matching events, in order.
        """
        return _of(IExternalIdentityAuthenticated, self.recorded_events)

    def test_fires_once(self):
        """One login, one event."""
        self.plugin.authenticateCredentials(self.credentials)

        assert len(self.authenticated()) == 1

    def test_first_login_payload(self):
        """A brand new user is flagged as such."""
        userid, _ = self.plugin.authenticateCredentials(self.credentials)

        event = self.authenticated()[0]
        assert event.userid == userid
        assert event.provider == DEX_IDENTITY[0]
        assert event.subject == DEX_IDENTITY[1]
        assert event.is_new_user is True
        assert event.is_new_identity is True

    def test_repeat_login_payload(self):
        """A returning user is not flagged as new."""
        self.plugin.authenticateCredentials(self.credentials)
        self.plugin.authenticateCredentials(self.credentials)

        event = self.authenticated()[1]
        assert event.is_new_user is False
        assert event.is_new_identity is False

    def test_claims_travel_with_event(self):
        """Consumers read claims off the event, not out of the store."""
        self.plugin.authenticateCredentials(self.credentials)

        assert self.authenticated()[0].claims["fullname"] == "Érico Andrei"


class TestLinking:
    """One human, several providers."""

    @pytest.fixture(autouse=True)
    def _setup(self, plugin: IdentityPlugin, credentials, recorded_events) -> None:
        self.plugin = plugin
        self.credentials = credentials
        self.recorded_events = recorded_events
        self.userid, _ = plugin.authenticateCredentials(credentials)

    def test_link_second_provider(self):
        """Both identities resolve to the same userid -- the whole point."""
        self.plugin.link(self.userid, *GITHUB_IDENTITY, CLAIMS)

        assert self.plugin.store.userid_for(*GITHUB_IDENTITY) == self.userid
        assert self.plugin.store.userid_for(*DEX_IDENTITY) == self.userid

    def test_link_fires_event(self):
        """``IdentityLinked`` carries the new identity."""
        self.plugin.link(self.userid, *GITHUB_IDENTITY, CLAIMS)

        events = _of(IIdentityLinked, self.recorded_events)
        assert len(events) == 1
        assert events[0].provider == "github"

    def test_link_collision_is_hard_error(self):
        """An identity is never moved between accounts."""
        other = {
            **self.credentials,
            "subject": "other-subject",
            "claims": OTHER_CLAIMS,
        }
        other_userid, _ = self.plugin.authenticateCredentials(other)
        self.plugin.link(other_userid, *GITHUB_IDENTITY, OTHER_CLAIMS)

        with pytest.raises(IdentityCollision):
            self.plugin.link(self.userid, *GITHUB_IDENTITY, CLAIMS)

    def test_login_via_linked_provider(self):
        """Logging in with the second provider lands on the same account."""
        self.plugin.link(self.userid, *GITHUB_IDENTITY, CLAIMS)
        provider, subject = GITHUB_IDENTITY

        again, _ = self.plugin.authenticateCredentials({
            **self.credentials,
            "provider": provider,
            "subject": subject,
        })

        assert again == self.userid


class TestUnlinking:
    """Unlinking must not lock anyone out."""

    @pytest.fixture(autouse=True)
    def _setup(self, plugin: IdentityPlugin, credentials, recorded_events) -> None:
        self.plugin = plugin
        self.recorded_events = recorded_events
        self.userid, _ = plugin.authenticateCredentials(credentials)
        plugin.link(self.userid, *GITHUB_IDENTITY, CLAIMS)

    def test_unlink_removes_identity(self):
        """The identity stops resolving."""
        self.plugin.unlink(self.userid, *GITHUB_IDENTITY)

        assert self.plugin.store.userid_for(*GITHUB_IDENTITY) is None

    def test_unlink_fires_event(self):
        """``IdentityUnlinked`` names what went away."""
        self.plugin.unlink(self.userid, *GITHUB_IDENTITY)

        events = _of(IIdentityUnlinked, self.recorded_events)
        assert len(events) == 1
        assert events[0].subject == GITHUB_IDENTITY[1]

    def test_unlink_keeps_other_identity(self):
        """The remaining way in is untouched."""
        self.plugin.unlink(self.userid, *GITHUB_IDENTITY)

        assert self.plugin.store.userid_for(*DEX_IDENTITY) == self.userid

    def test_unlink_last_identity_refused(self):
        """The last way in cannot be removed."""
        self.plugin.unlink(self.userid, *GITHUB_IDENTITY)

        with pytest.raises(LockoutRefused):
            self.plugin.unlink(self.userid, *DEX_IDENTITY)

    def test_refused_unlink_changes_nothing(self):
        """A refused unlink leaves the account intact."""
        self.plugin.unlink(self.userid, *GITHUB_IDENTITY)

        with pytest.raises(LockoutRefused):
            self.plugin.unlink(self.userid, *DEX_IDENTITY)

        assert self.plugin.store.userid_for(*DEX_IDENTITY) == self.userid

    def test_unlink_someone_elses_identity_refused(self):
        """A user cannot unlink an identity they do not own."""
        with pytest.raises(KeyError):
            self.plugin.unlink("some-other-userid", *GITHUB_IDENTITY)

    def test_unlink_unknown_identity_refused(self):
        """Unlinking something never linked is an error."""
        with pytest.raises(KeyError):
            self.plugin.unlink(self.userid, "google", "never-seen")

    def test_can_unlink_reports_true_with_sibling(self):
        """The guard agrees with what ``unlink`` does."""
        assert self.plugin.can_unlink(self.userid, *GITHUB_IDENTITY) is True

    def test_can_unlink_reports_false_for_last(self):
        """The guard refuses the last identity."""
        self.plugin.unlink(self.userid, *GITHUB_IDENTITY)

        assert self.plugin.can_unlink(self.userid, *DEX_IDENTITY) is False


class TestVerifiedEmail:
    """The lockout guard's other escape hatch: a verified email identity."""

    @pytest.fixture(autouse=True)
    def _setup(self, plugin: IdentityPlugin, credentials) -> None:
        self.plugin = plugin
        self.userid, _ = plugin.authenticateCredentials(credentials)

    def test_absent_by_default(self):
        """An OIDC-only account has no email identity."""
        assert self.plugin.has_verified_email(self.userid) is False

    def test_present_after_email_link(self):
        """Linking a magic-link identity is what satisfies the guard."""
        self.plugin.link(self.userid, "email", "erico@plone.org", CLAIMS)

        assert self.plugin.has_verified_email(self.userid) is True

    def test_email_identity_permits_unlink_of_last_provider(self):
        """With an email identity present, the OIDC one can go."""
        self.plugin.link(self.userid, "email", "erico@plone.org", CLAIMS)

        self.plugin.unlink(self.userid, *DEX_IDENTITY)

        assert self.plugin.store.userid_for(*DEX_IDENTITY) is None


class TestLocalPassword:
    """The lockout guard's third escape hatch: a real ``source_users``
    password."""

    @pytest.fixture(autouse=True)
    def _setup(self, plugin: IdentityPlugin, portal, credentials) -> None:
        self.plugin = plugin
        self.portal = portal
        self.credentials = credentials
        with api.env.adopt_roles(["Manager"]):
            user = api.user.create(
                email="local@plone.org",
                username="local",
                password="s3cr3t-local",
            )
        self.member = user.getId()

    def test_password_permits_unlink_of_last_identity(self):
        """Someone who signed up locally and later linked a provider can
        unlink it again: they still have a password to log in with."""
        self.plugin.link(self.member, *DEX_IDENTITY, CLAIMS)

        assert self.plugin.can_unlink(self.member, *DEX_IDENTITY) is True

    def test_unlink_goes_through(self):
        """And the guard's answer is what ``unlink`` acts on."""
        self.plugin.link(self.member, *DEX_IDENTITY, CLAIMS)

        self.plugin.unlink(self.member, *DEX_IDENTITY)

        assert self.plugin.store.userid_for(*DEX_IDENTITY) is None

    def test_placeholder_password_does_not_count(self):
        """The placeholder seeded at first login is not a way in, so it must
        not satisfy the guard -- that was how a user could unlink their last
        identity and lose the account."""
        userid, _ = self.plugin.authenticateCredentials(self.credentials)

        assert self.plugin.can_unlink(userid, *DEX_IDENTITY) is False

    def test_userid_absent_from_source_users(self):
        """A userid ``source_users`` has never heard of has no password."""
        assert self.plugin.can_unlink("never-existed", *GITHUB_IDENTITY) is False


class TestCredentialsReset:
    @pytest.fixture(autouse=True)
    def _setup(self, plugin: IdentityPlugin, portal, http_request) -> None:
        self.plugin = plugin
        self.portal = portal
        self.request = http_request

    def test_reset_clears_deposit(self):
        """Logging out drops anything this plugin left on the request."""
        self.request.other[CREDENTIALS_KEY] = {"provider": "x", "subject": "y"}

        self.plugin.resetCredentials(self.request, self.request.response)

        assert CREDENTIALS_KEY not in self.request.other

    def test_reset_without_deposit_is_safe(self):
        """Resetting an ordinary request is a no-op."""
        self.plugin.resetCredentials(self.request, self.request.response)

        assert CREDENTIALS_KEY not in self.request.other

    def test_reset_on_bare_object_is_safe(self):
        """PAS passes odd things around; do not crash on them."""
        self.plugin.resetCredentials(object(), object())


class TestChallenge:
    """Opt-in, off by default."""

    @pytest.fixture(autouse=True)
    def _setup(self, plugin: IdentityPlugin, portal, http_request) -> None:
        self.plugin = plugin
        self.portal = portal
        self.request = http_request

    def location(self) -> str:
        """Return the redirect the challenge issued.

        :returns: The ``Location`` header.
        """
        return self.request.response.getHeader("Location")

    def test_disabled_by_default(self):
        """The stock login form stays in charge."""
        assert self.plugin.challenge_enabled is False
        assert self.plugin.challenge(self.request, self.request.response) is False

    def test_enabled_redirects_to_picker(self):
        """Once on, an unauthorized request goes to the provider picker.

        ``/login`` rather than a name only this package knows: the Volto
        add-on overrides that route with the picker, and a Classic site serves
        Plone's own form there."""
        self.plugin.challenge_enabled = True

        handled = self.plugin.challenge(self.request, self.request.response)

        assert handled is True
        assert self.location().endswith("/login")

    def test_came_from_is_preserved(self):
        """The user returns where they were headed."""
        self.plugin.challenge_enabled = True
        self.request["ACTUAL_URL"] = f"{self.portal.absolute_url()}/some-page"

        self.plugin.challenge(self.request, self.request.response)

        assert "came_from=" in self.location()

    def test_the_query_string_is_carried_too(self):
        """Not decoration: an OAuth authorization request *is* its query
        string, so a came_from built from the path alone resumes a request
        with no client, no redirect URI and no PKCE challenge."""
        self.plugin.challenge_enabled = True
        self.request["ACTUAL_URL"] = f"{self.portal.absolute_url()}/@@oauth-authorize"
        self.request.environ["QUERY_STRING"] = "client_id=app&state=xyzzy"

        self.plugin.challenge(self.request, self.request.response)

        assert "client_id%3Dapp" in self.location()
        assert "state%3Dxyzzy" in self.location()

    def test_came_from_is_quoted(self):
        """Unquoted, the first `&` of the query string would be read as
        another parameter of the login URL rather than part of the return
        address."""
        self.plugin.challenge_enabled = True
        self.request["ACTUAL_URL"] = f"{self.portal.absolute_url()}/@@oauth-authorize"
        self.request.environ["QUERY_STRING"] = "a=1&b=2"

        self.plugin.challenge(self.request, self.request.response)

        assert self.location().count("came_from") == 1
        assert "&b=2" not in self.location()

    def test_came_from_is_reduced_to_a_local_url(self):
        """This value ends up in a redirect after login. An absolute one
        would make the login form an open redirect."""
        self.plugin.challenge_enabled = True
        self.request["ACTUAL_URL"] = "https://evil.example.org/steal"

        self.plugin.challenge(self.request, self.request.response)

        assert "evil.example.org" not in self.location()

    def test_no_came_from_when_there_is_nowhere_to_return_to(self):
        """A challenge with no originating URL sends a bare picker URL rather
        than an empty ``came_from`` for the picker to puzzle over."""
        self.plugin.challenge_enabled = True
        self.request["ACTUAL_URL"] = ""

        self.plugin.challenge(self.request, self.request.response)

        assert "came_from" not in self.location()
