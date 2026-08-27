"""The profile PAS plugin's contract.

Zero-wake is asserted separately, in ``test_zero_wake``. What is asserted here
is that the plugin gives the *right* answers: that a Profile outranks the
property sheet core seeded at first login, that a user enumerated by both this
plugin and ``source_users`` still shows up once, that login names match
regardless of case, and that a deactivated Profile disappears from
enumeration without disappearing from the site.
"""

from . import PROFILE_ID
from pas.plugins.identity.content.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.content.pas import ENUMERATION_STATES_RECORD
from pas.plugins.identity.content.pas import PLUGIN_ID
from plone import api
from Products.PluggableAuthService.interfaces.plugins import IPropertiesPlugin
from Products.PluggableAuthService.interfaces.plugins import IUserEnumerationPlugin

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


@pytest.fixture
def make_user(portal, acl_users):
    """Return a factory for a user shaped the way a login leaves one.

    Core mints a userid, creates a ``source_users`` account with a placeholder
    password and seeds ``mutable_properties`` from the provider's claims. The
    ``[content]`` layer then adds a Profile. Reproducing both halves is the
    only way to test which one wins.

    :param portal: The Plone site.
    :param acl_users: The site's PAS instance.
    :returns: Callable taking a userid and field values.
    """

    def factory(userid: str, seeded: dict | None = None, **fields) -> object:
        acl_users.source_users.addUser(userid, userid, "placeholder-password")
        if seeded:
            api.user.get(userid=userid).setMemberProperties(seeded)
        return api.content.create(
            container=portal["identity-profiles"],
            type=PROFILE_PORTAL_TYPE,
            id=userid,
            userid=userid,
            login=fields.pop("login", f"{userid}@example.com"),
            **fields,
        )

    return factory


class TestInstallation:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, plugin) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.plugin = plugin

    def test_plugin_present(self):
        """The profile GenericSetup profile installs it."""
        assert PLUGIN_ID in self.acl_users.objectIds()

    def test_activated_for_properties(self):
        """It serves member properties."""
        assert PLUGIN_ID in self.acl_users.plugins.listPluginIds(IPropertiesPlugin)

    def test_activated_for_enumeration(self):
        """And user enumeration."""
        assert PLUGIN_ID in self.acl_users.plugins.listPluginIds(IUserEnumerationPlugin)

    def test_not_an_authentication_plugin(self):
        """This layer must never become a way to log in."""
        from Products.PluggableAuthService.interfaces.plugins import (
            IAuthenticationPlugin,
        )

        assert PLUGIN_ID not in self.acl_users.plugins.listPluginIds(
            IAuthenticationPlugin
        )

    def test_ordered_above_mutable_properties(self):
        """Load-bearing: Plone takes the first sheet that has the property.

        Below ``mutable_properties`` the Profile would never be read and the
        layer would look installed while doing nothing.
        """
        order = self.acl_users.plugins.listPluginIds(IPropertiesPlugin)

        assert order.index(PLUGIN_ID) < order.index("mutable_properties")


class TestPropertiesAreServed:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, plugin, make_user) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.plugin = plugin
        self.make_user = make_user

    def test_fullname_and_email_for_an_authenticated_user(self):
        """The headline, read the way Plone reads it."""
        self.make_user("alice", fullname="Alice Liddell", email="alice@example.com")

        member = api.user.get(userid="alice")

        assert member.getProperty("fullname") == "Alice Liddell"
        assert member.getProperty("email") == "alice@example.com"

    def test_profile_outranks_the_seeded_sheet(self):
        """A Profile edit is what the site shows, not the login-time claim."""
        self.make_user(
            "alice",
            seeded={"fullname": "A. Liddell", "email": "old@example.com"},
            fullname="Alice Liddell",
            email="alice@example.com",
        )

        member = api.user.get(userid="alice")

        assert member.getProperty("fullname") == "Alice Liddell"
        assert member.getProperty("email") == "alice@example.com"

    def test_the_other_fields_are_served_too(self):
        """Not just the two anybody remembers."""
        self.make_user(
            "alice",
            home_page="https://example.com/alice",
            description="Fond of white rabbits",
            location="Wonderland",
        )

        member = api.user.get(userid="alice")

        assert member.getProperty("home_page") == "https://example.com/alice"
        assert member.getProperty("description") == "Fond of white rabbits"
        assert member.getProperty("location") == "Wonderland"

    def test_user_without_a_profile_falls_through(self):
        """A site can hold users the layer knows nothing about."""
        self.acl_users.source_users.addUser("bob", "bob", "placeholder-password")
        api.user.get(userid="bob").setMemberProperties({"fullname": "Bob"})

        assert (
            self.plugin.getPropertiesForUser(self.acl_users.getUserById("bob")) is None
        )
        assert api.user.get(userid="bob").getProperty("fullname") == "Bob"

    def test_empty_profile_field_is_served_as_empty(self):
        """The Profile is the source of truth, including when it is blank.

        Falling through to the seeded claim would make a field the user
        deliberately cleared reappear at the next page load.
        """
        self.make_user("alice", seeded={"fullname": "A. Liddell"})

        assert api.user.get(userid="alice").getProperty("fullname") == ""


class TestEnumeration:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, plugin, make_user) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.plugin = plugin
        self.make_user = make_user

    def test_enumerate_by_exact_userid(self):
        """The identity join, straight off the index."""
        self.make_user("alice")

        results = self.plugin.enumerateUsers(id="alice", exact_match=True)

        assert [record["id"] for record in results] == ["alice"]

    def test_records_carry_the_plugin_id(self):
        """PAS needs to know who answered."""
        self.make_user("alice")

        assert self.plugin.enumerateUsers(id="alice")[0]["pluginid"] == PLUGIN_ID

    def test_substring_is_the_default(self):
        """Matching ``source_users``, which is what callers expect."""
        self.make_user("alice", fullname="Alice Liddell")

        assert self.plugin.enumerateUsers(fullname="iddel")

    def test_exact_match_is_not_substring(self):
        """And exact means exact."""
        self.make_user("alice", fullname="Alice Liddell")

        assert not self.plugin.enumerateUsers(fullname="iddel", exact_match=True)

    def test_criteria_are_ored(self):
        """A record matching on email must not be dropped for missing on name."""
        self.make_user("alice", fullname="Alice Liddell", email="rabbit@example.com")

        results = self.plugin.enumerateUsers(fullname="nobody", email="rabbit")

        assert [record["id"] for record in results] == ["alice"]

    def test_sequences_are_accepted(self):
        """PAS allows every search argument to be a sequence."""
        self.make_user("alice")
        self.make_user("bob")

        results = self.plugin.enumerateUsers(id=["alice", "bob"], exact_match=True)

        assert sorted(record["id"] for record in results) == ["alice", "bob"]

    def test_max_results_is_honoured(self):
        """A listing asking for two must not be handed ten."""
        for index in range(5):
            self.make_user(f"user{index}")

        assert len(self.plugin.enumerateUsers(max_results=2)) == 2

    def test_no_criteria_enumerates_everybody(self):
        """A bare call is "list them all", not "match nothing"."""
        self.make_user("alice")
        self.make_user("bob")

        assert len(self.plugin.enumerateUsers()) == 2

    def test_no_match_is_empty(self):
        """And a miss is a miss."""
        self.make_user("alice")

        assert self.plugin.enumerateUsers(id="nobody", exact_match=True) == ()

    def test_empty_field_never_matches(self):
        """An unfilled field is not a wildcard.

        Without this, searching for the empty string -- which is what an
        over-eager search box sends -- would match every Profile that had not
        filled that field in, on a criterion the caller never meant.
        """
        self.make_user("alice", fullname="")

        assert self.plugin.enumerateUsers(fullname="anything") == ()

    def test_properties_for_a_user_without_an_id(self):
        """PAS can hand over a user whose id is empty; do not query on it."""

        class Anonymous:
            """A user with no id."""

            def getId(self):
                """Return no id.

                :returns: ``None``.
                """
                return None

        assert self.plugin.getPropertiesForUser(Anonymous()) is None


class TestLoginCaseInsensitivity:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, plugin, make_user) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.plugin = plugin
        self.make_user = make_user

    def test_login_matches_regardless_of_case(self):
        """Login names are case-insensitive in Plone; FieldIndex is not.

        The index stores the folded form and the self.plugin folds the query, so
        neither side can drift without this failing.
        """
        self.make_user("alice", login="Alice@Example.COM")

        assert self.plugin.enumerateUsers(login="alice@example.com", exact_match=True)
        assert self.plugin.enumerateUsers(login="ALICE@EXAMPLE.COM", exact_match=True)
        assert self.plugin.enumerateUsers(login="Alice@Example.COM", exact_match=True)

    def test_substring_login_search_folds_too(self):
        """The non-exact path folds on the same rule."""
        self.make_user("alice", login="Alice@Example.COM")

        assert self.plugin.enumerateUsers(login="EXAMPLE")


class TestEnumerationStates:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, plugin, make_user) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.plugin = plugin
        self.make_user = make_user

    def test_incomplete_is_enumerated(self):
        """A sparse profile is still a working account."""
        self.make_user("alice")

        assert self.plugin.enumerateUsers(id="alice", exact_match=True)

    def test_complete_is_enumerated(self):
        """So is a filled-in one."""
        profile = self.make_user("alice")
        api.content.transition(obj=profile, transition="complete")

        assert self.plugin.enumerateUsers(id="alice", exact_match=True)

    def test_deactivated_is_not_enumerated(self):
        """The point of the state."""
        profile = self.make_user("alice")
        api.content.transition(obj=profile, transition="deactivate")

        assert self.plugin.enumerateUsers(id="alice", exact_match=True) == ()

    def test_deactivated_profile_still_exists(self):
        """Deactivation hides an account; it does not delete one."""
        profile = self.make_user("alice")
        api.content.transition(obj=profile, transition="deactivate")

        assert "alice" in self.portal["identity-profiles"].objectIds()

    def test_the_state_list_is_configuration(self):
        """A site that only wants completed profiles listed says so."""
        self.make_user("alice")
        api.portal.set_registry_record(ENUMERATION_STATES_RECORD, ("complete",))

        assert self.plugin.enumerateUsers(id="alice", exact_match=True) == ()


class TestNoDuplicatesWithSourceUsers:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, plugin, make_user) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.plugin = plugin
        self.make_user = make_user

    def test_both_plugins_answer(self):
        """The premise: core leaves ``source_users`` enumerating."""
        self.make_user("alice", fullname="Alice Liddell")

        assert self.plugin.enumerateUsers(id="alice", exact_match=True)
        assert self.acl_users.source_users.enumerateUsers(id="alice", exact_match=True)

    def test_pas_itself_returns_two_rows(self):
        """PAS concatenates enumerators and does not deduplicate.

        Pinned deliberately: this is the behaviour the userid agreement below
        exists to survive, and if a future PAS started deduplicating we would
        want to know rather than to keep compensating for it.
        """
        self.make_user("alice", fullname="Alice Liddell")

        assert len(self.acl_users.searchUsers(id="alice", exact_match=True)) == 2

    def test_the_rows_agree_on_the_userid(self):
        """Which is what lets every consumer merge them back into one."""
        self.make_user("alice", fullname="Alice Liddell")

        rows = self.acl_users.searchUsers(id="alice", exact_match=True)

        assert {row["userid"] for row in rows} == {"alice"}

    def test_sharing_style_search_returns_one_row(self):
        """The gate's own wording, through the merge the Sharing tab uses."""
        from plone.app.workflow.browser.sharing import merge_search_results

        self.make_user("alice", fullname="Alice Liddell")

        merged = merge_search_results(
            self.acl_users.searchUsers(name="alice"), "userid"
        )

        assert [row["userid"] for row in merged] == ["alice"]

    def test_several_users_each_appear_once(self):
        """Not an artefact of there being only one of them.

        Counted rather than compared against a fixed list: the test layer has
        a user of its own, and asserting the exact set would be asserting
        something about ``plone.app.testing`` instead of about this self.plugin.
        """
        from plone.app.workflow.browser.sharing import merge_search_results

        ours = {f"user{index}" for index in range(5)}
        for userid in sorted(ours):
            self.make_user(userid, fullname=f"Number {userid[-1]}")

        raw = [
            row["userid"]
            for row in self.acl_users.searchUsers(name="user")
            if row["userid"] in ours
        ]
        merged = [
            row["userid"]
            for row in merge_search_results(
                self.acl_users.searchUsers(name="user"), "userid"
            )
            if row["userid"] in ours
        ]

        assert len(raw) == 10
        assert sorted(merged) == sorted(ours)
