"""First login and claims sync.

The subscriber is driven entirely by the event contract, so these tests
fire the events rather than driving a login. That is not a shortcut: it is the
contract the layer is built against, and a test that logged in would be
testing core's flow a second time.

The table in the subscriber's docstring has a row per situation; there is a
test per row.
"""

from Acquisition import aq_parent
from pas.plugins.identity.core import subscribers
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.events import ExternalIdentityAuthenticated
from pas.plugins.identity.core.events import IdentityLinked
from pas.plugins.identity.core.events import UserClaimsRefreshed
from plone import api
from zope.event import notify
from zope.lifecycleevent import modified

import pytest


#: What a provider sends for somebody signing up for the first time.
CLAIMS = {
    "fullname": "Alice Liddell",
    "email": "alice@example.com",
    "email_verified": True,
    "username": "alice",
    "raw": {},
}


def login(userid: str = "alice-userid", **claims) -> None:
    """Fire a successful-authentication event.

    :param userid: Canonical Plone userid.
    :param claims: Claim overrides on top of :data:`CLAIMS`.
    """
    notify(
        ExternalIdentityAuthenticated(
            userid=userid,
            provider="dex",
            subject="subject-1",
            claims={**CLAIMS, **claims},
            is_new_user=True,
            is_new_identity=True,
        )
    )


@pytest.fixture
def profile(portal):
    """Return the Profile created by a first login.

    :param portal: The Plone site.
    :returns: The Profile.
    """
    login()
    return subscribers.get_profile("alice-userid")


class TestProfileIsMinted:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, catalog, profile) -> None:
        self.portal = portal
        self.catalog = catalog
        self.profile = profile

    def test_first_login_creates_a_profile(self):
        """The headline: a first login mints a Profile."""
        login()

        assert self.catalog.unrestrictedSearchResults(userid="alice-userid")

    def test_it_lands_in_the_configured_container(self):
        """Where new Profiles go is the container setting, not a constant."""
        assert aq_parent(self.profile).getId() == "identity-profiles"

    def test_a_provider_that_sent_everything_completes_it(self):
        """The state describes the profile rather than its age.

        These claims carry an email, which is the one field the shipped type
        requires and a provider can withhold. Nothing is missing, so nothing
        should be asked of the user.
        """
        assert api.content.get_state(self.profile) == "complete"

    def test_the_id_is_the_userid(self):
        """Opaque and permanent, so the Profile is never renamed."""
        assert self.profile.getId() == "alice-userid"

    def test_the_userid_is_recorded(self):
        """The join back to the identity store."""
        assert self.profile.userid == "alice-userid"

    def test_the_login_comes_from_the_username_claim(self):
        """A provider that sends a username has named the account."""
        assert self.profile.login == "alice"

    def test_login_falls_back_to_the_email(self):
        """Plenty of providers send no username."""
        login(userid="bob-userid", username="")

        assert subscribers.get_profile("bob-userid").login == "alice@example.com"

    def test_login_falls_back_to_the_userid(self):
        """The field is required; a Profile that cannot be created is a login
        that fails."""
        login(userid="carol-userid", username="", email="")

        assert subscribers.get_profile("carol-userid").login == "carol-userid"

    def test_second_login_does_not_create_a_second(self):
        """Idempotent, which is what makes it safe on every login."""
        login()
        login()

        assert len(self.catalog.unrestrictedSearchResults(userid="alice-userid")) == 1

    def test_claims_are_seeded(self):
        """The Profile is usable straight away, not blank."""
        assert self.profile.fullname == "Alice Liddell"
        assert self.profile.email == "alice@example.com"

    def test_the_brain_is_up_to_date(self):
        """A Profile the catalog does not know about is invisible to PAS."""
        login()

        brain = self.catalog.unrestrictedSearchResults(userid="alice-userid")[0]

        assert brain.fullname == "Alice Liddell"


class TestClaimsRefresh:
    """One test per row of the table in the subscriber's docstring."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, profile) -> None:
        self.portal = portal
        self.profile = profile

    def test_fresh_field_is_written(self):
        """Row 1: nothing written yet."""
        assert self.profile.fullname == "Alice Liddell"

    def test_provider_change_is_applied(self):
        """Row 2: the provider still owns the field, so a rename lands."""
        login(fullname="Alice P. Liddell")

        assert self.profile.fullname == "Alice P. Liddell"

    def test_user_edit_is_never_clobbered(self):
        """Row 3: the whole point of the refresh policy."""
        self.profile.fullname = "Alice from Accounts"
        modified(self.profile)

        login(fullname="Alice P. Liddell")

        assert self.profile.fullname == "Alice from Accounts"

    def test_a_cleared_field_stays_cleared(self):
        """Row 4: clearing is an edit.

        A value that reappears at the next login is indistinguishable from a
        bug, and this is the row a flag-based design usually gets wrong.
        """
        self.profile.fullname = ""
        modified(self.profile)

        login(fullname="Alice P. Liddell")

        assert self.profile.fullname == ""

    def test_an_absent_claim_does_not_clear_the_field(self):
        """A provider that stops sending a name has not said there is none."""
        login(fullname="")

        assert self.profile.fullname == "Alice Liddell"

    def test_ownership_is_per_field(self):
        """Editing the name must not freeze the email as well."""
        self.profile.fullname = "Alice from Accounts"
        modified(self.profile)

        login(fullname="Ignored", email="alice@example.org")

        assert self.profile.fullname == "Alice from Accounts"
        assert self.profile.email == "alice@example.org"

    def test_login_is_never_synced(self):
        """A provider renaming somebody must not move their account.

        ``login`` is half of the case-folded index the enumeration plugin
        queries; letting a claim rewrite it would move a working account.
        """
        login(username="alice-renamed")

        assert self.profile.login == "alice"

    def test_unchanged_claims_report_no_change(self):
        """Nothing to reindex means nothing gets reindexed."""
        assert subscribers.sync_claims(self.profile, CLAIMS) == []


class TestHandTypedValues:
    """A Profile an administrator created before the user ever logged in."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, catalog) -> None:
        self.portal = portal
        self.catalog = catalog

    def test_hand_typed_value_is_never_clobbered(self):
        """Row 5: an administrator who typed it in owns it."""
        api.content.create(
            container=self.portal["identity-profiles"],
            type=PROFILE_PORTAL_TYPE,
            id="alice-userid",
            userid="alice-userid",
            login="alice",
            fullname="Alice, on the third floor",
        )

        login()

        profile = subscribers.get_profile("alice-userid")
        assert profile.fullname == "Alice, on the third floor"


class TestOtherEvents:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, catalog, profile) -> None:
        self.portal = portal
        self.catalog = catalog
        self.profile = profile

    def test_linking_fills_a_field_the_provider_still_owns(self):
        """Signing up somewhere anonymous then linking GitHub should help."""
        login(userid="dave-userid", fullname="", username="dave")

        notify(
            IdentityLinked(
                userid="dave-userid",
                provider="github",
                subject="99",
                claims={**CLAIMS, "fullname": "Dave Lister"},
            )
        )

        assert subscribers.get_profile("dave-userid").fullname == "Dave Lister"

    def test_linking_still_respects_a_user_edit(self):
        """A second provider is not a way around the refresh policy."""
        self.profile.fullname = "Alice from Accounts"
        modified(self.profile)

        notify(
            IdentityLinked(
                userid="alice-userid",
                provider="github",
                subject="99",
                claims={**CLAIMS, "fullname": "Alice P. Liddell"},
            )
        )

        assert self.profile.fullname == "Alice from Accounts"

    def test_claims_refresh_applies(self):
        """A refresh fired outside the login path lands the same way."""
        notify(
            UserClaimsRefreshed(
                userid="alice-userid",
                provider="dex",
                claims={**CLAIMS, "fullname": "Alice P. Liddell"},
            )
        )

        assert self.profile.fullname == "Alice P. Liddell"

    def test_linking_mints_a_profile_for_a_user_without_one(self):
        """A site that installed the layer after people had accounts."""
        notify(
            IdentityLinked(
                userid="erin-userid",
                provider="github",
                subject="7",
                claims=CLAIMS,
            )
        )

        assert self.catalog.unrestrictedSearchResults(userid="erin-userid")
