"""First login and D2 claims sync (Gate 6c).

The subscriber is driven entirely by the §4.3 event contract, so these tests
fire the events rather than driving a login. That is not a shortcut: it is the
contract the layer is built against, and a test that logged in would be
testing core's flow a second time.

The D2 table in the subscriber's docstring has a row per situation; there is a
test per row.
"""

from pas.plugins.identity.core.events import ExternalIdentityAuthenticated
from pas.plugins.identity.core.events import IdentityLinked
from pas.plugins.identity.core.events import UserClaimsRefreshed
from pas.plugins.identity.profile import subscribers
from pas.plugins.identity.profile.catalog import PROFILE_PORTAL_TYPE
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
    def test_first_login_creates_a_profile(self, portal, catalog):
        """The headline of Gate 6c."""
        login()

        assert catalog.unrestrictedSearchResults(userid="alice-userid")

    def test_it_lands_in_the_configured_container(self, portal, profile):
        """Where new Profiles go is the container setting, not a constant."""
        assert profile.__parent__.getId() == "identity-profiles"

    def test_it_starts_incomplete(self, portal, profile):
        """Which is what the frontend routes on."""
        assert api.content.get_state(profile) == "incomplete"

    def test_the_id_is_the_userid(self, portal, profile):
        """Opaque and permanent (I1), so the Profile is never renamed."""
        assert profile.getId() == "alice-userid"

    def test_the_userid_is_recorded(self, portal, profile):
        """The join back to the identity store."""
        assert profile.userid == "alice-userid"

    def test_the_login_comes_from_the_username_claim(self, portal, profile):
        """A provider that sends a username has named the account."""
        assert profile.login == "alice"

    def test_login_falls_back_to_the_email(self, portal):
        """Plenty of providers send no username."""
        login(userid="bob-userid", username="")

        assert subscribers.get_profile("bob-userid").login == "alice@example.com"

    def test_login_falls_back_to_the_userid(self, portal):
        """The field is required; a Profile that cannot be created is a login
        that fails."""
        login(userid="carol-userid", username="", email="")

        assert subscribers.get_profile("carol-userid").login == "carol-userid"

    def test_second_login_does_not_create_a_second(self, portal, catalog):
        """Idempotent, which is what makes it safe on every login."""
        login()
        login()

        assert len(catalog.unrestrictedSearchResults(userid="alice-userid")) == 1

    def test_claims_are_seeded(self, portal, profile):
        """The Profile is usable straight away, not blank."""
        assert profile.fullname == "Alice Liddell"
        assert profile.email == "alice@example.com"

    def test_the_brain_is_up_to_date(self, portal, catalog):
        """A Profile the catalog does not know about is invisible to PAS."""
        login()

        brain = catalog.unrestrictedSearchResults(userid="alice-userid")[0]

        assert brain.fullname == "Alice Liddell"


class TestD2ClaimsRefresh:
    """One test per row of the table in the subscriber's docstring."""

    def test_fresh_field_is_written(self, portal, profile):
        """Row 1: nothing written yet."""
        assert profile.fullname == "Alice Liddell"

    def test_provider_change_is_applied(self, portal, profile):
        """Row 2: the provider still owns the field, so a rename lands."""
        login(fullname="Alice P. Liddell")

        assert profile.fullname == "Alice P. Liddell"

    def test_user_edit_is_never_clobbered(self, portal, profile):
        """Row 3: the whole point of D2."""
        profile.fullname = "Alice from Accounts"
        modified(profile)

        login(fullname="Alice P. Liddell")

        assert profile.fullname == "Alice from Accounts"

    def test_a_cleared_field_stays_cleared(self, portal, profile):
        """Row 4: clearing is an edit.

        A value that reappears at the next login is indistinguishable from a
        bug, and this is the row a flag-based design usually gets wrong.
        """
        profile.fullname = ""
        modified(profile)

        login(fullname="Alice P. Liddell")

        assert profile.fullname == ""

    def test_hand_typed_value_is_never_clobbered(self, portal, catalog):
        """Row 5: an administrator who typed it in owns it."""
        with api.env.adopt_roles(["Manager"]):
            api.content.create(
                container=portal["identity-profiles"],
                type=PROFILE_PORTAL_TYPE,
                id="alice-userid",
                userid="alice-userid",
                login="alice",
                fullname="Alice, on the third floor",
            )

        login()

        profile = subscribers.get_profile("alice-userid")
        assert profile.fullname == "Alice, on the third floor"

    def test_an_absent_claim_does_not_clear_the_field(self, portal, profile):
        """A provider that stops sending a name has not said there is none."""
        login(fullname="")

        assert profile.fullname == "Alice Liddell"

    def test_ownership_is_per_field(self, portal, profile):
        """Editing the name must not freeze the email as well."""
        profile.fullname = "Alice from Accounts"
        modified(profile)

        login(fullname="Ignored", email="alice@example.org")

        assert profile.fullname == "Alice from Accounts"
        assert profile.email == "alice@example.org"

    def test_login_is_never_synced(self, portal, profile):
        """A provider renaming somebody must not move their account.

        ``login`` is half of the case-folded index the enumeration plugin
        queries; letting a claim rewrite it would move a working account.
        """
        login(username="alice-renamed")

        assert profile.login == "alice"

    def test_unchanged_claims_report_no_change(self, portal, profile):
        """Nothing to reindex means nothing gets reindexed."""
        assert subscribers.sync_claims(profile, CLAIMS) == []


class TestOtherEvents:
    def test_linking_fills_a_field_the_provider_still_owns(self, portal):
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

    def test_linking_still_respects_a_user_edit(self, portal, profile):
        """A second provider is not a way around D2."""
        profile.fullname = "Alice from Accounts"
        modified(profile)

        notify(
            IdentityLinked(
                userid="alice-userid",
                provider="github",
                subject="99",
                claims={**CLAIMS, "fullname": "Alice P. Liddell"},
            )
        )

        assert profile.fullname == "Alice from Accounts"

    def test_claims_refresh_applies(self, portal, profile):
        """A refresh fired outside the login path lands the same way."""
        notify(
            UserClaimsRefreshed(
                userid="alice-userid",
                provider="dex",
                claims={**CLAIMS, "fullname": "Alice P. Liddell"},
            )
        )

        assert profile.fullname == "Alice P. Liddell"

    def test_linking_mints_a_profile_for_a_user_without_one(self, portal, catalog):
        """A site that installed the layer after people had accounts."""
        notify(
            IdentityLinked(
                userid="erin-userid",
                provider="github",
                subject="7",
                claims=CLAIMS,
            )
        )

        assert catalog.unrestrictedSearchResults(userid="erin-userid")
