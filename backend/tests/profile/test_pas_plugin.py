"""The profile PAS plugin's contract (Gate 6b).

Zero-wake is asserted separately, in ``test_zero_wake``. What is asserted here
is that the plugin gives the *right* answers: that a Profile outranks the
property sheet core seeded at first login, that a user enumerated by both this
plugin and ``source_users`` still shows up once, that login names match
regardless of case, and that a deactivated Profile disappears from
enumeration without disappearing from the site.
"""

from pas.plugins.identity.profile.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.profile.pas import ENUMERATION_STATES_RECORD
from pas.plugins.identity.profile.pas import PLUGIN_ID
from plone import api
from Products.PluggableAuthService.interfaces.plugins import IPropertiesPlugin
from Products.PluggableAuthService.interfaces.plugins import IUserEnumerationPlugin

import pytest


@pytest.fixture
def acl_users(portal):
    """The site's PAS instance.

    :param portal: The Plone site.
    :returns: ``acl_users``.
    """
    return api.portal.get_tool("acl_users")


@pytest.fixture
def plugin(acl_users):
    """The profile PAS plugin.

    :param acl_users: The site's PAS instance.
    :returns: The plugin.
    """
    return acl_users[PLUGIN_ID]


@pytest.fixture
def make_user(portal, acl_users):
    """Return a factory for a user shaped the way Gate 1 leaves one.

    Core mints a userid, creates a ``source_users`` account with a placeholder
    password and seeds ``mutable_properties`` from the provider's claims. The
    ``[profile]`` layer then adds a Profile. Reproducing both halves is the
    only way to test which one wins.

    :param portal: The Plone site.
    :param acl_users: The site's PAS instance.
    :returns: Callable taking a userid and field values.
    """

    def factory(userid: str, seeded: dict | None = None, **fields) -> object:
        acl_users.source_users.addUser(userid, userid, "placeholder-password")
        if seeded:
            api.user.get(userid=userid).setMemberProperties(seeded)
        with api.env.adopt_roles(["Manager"]):
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
    def test_plugin_present(self, acl_users):
        """The profile GenericSetup profile installs it."""
        assert PLUGIN_ID in acl_users.objectIds()

    def test_activated_for_properties(self, acl_users):
        """It serves member properties."""
        assert PLUGIN_ID in acl_users.plugins.listPluginIds(IPropertiesPlugin)

    def test_activated_for_enumeration(self, acl_users):
        """And user enumeration."""
        assert PLUGIN_ID in acl_users.plugins.listPluginIds(IUserEnumerationPlugin)

    def test_not_an_authentication_plugin(self, acl_users):
        """This layer must never become a way to log in."""
        from Products.PluggableAuthService.interfaces.plugins import (
            IAuthenticationPlugin,
        )

        assert PLUGIN_ID not in acl_users.plugins.listPluginIds(IAuthenticationPlugin)

    def test_ordered_above_mutable_properties(self, acl_users):
        """Load-bearing: Plone takes the first sheet that has the property.

        Below ``mutable_properties`` the Profile would never be read and the
        layer would look installed while doing nothing.
        """
        order = acl_users.plugins.listPluginIds(IPropertiesPlugin)

        assert order.index(PLUGIN_ID) < order.index("mutable_properties")


class TestPropertiesAreServed:
    def test_fullname_and_email_for_an_authenticated_user(self, make_user):
        """The headline of Gate 6b, read the way Plone reads it."""
        make_user("alice", fullname="Alice Liddell", email="alice@example.com")

        member = api.user.get(userid="alice")

        assert member.getProperty("fullname") == "Alice Liddell"
        assert member.getProperty("email") == "alice@example.com"

    def test_profile_outranks_the_seeded_sheet(self, make_user):
        """A Profile edit is what the site shows, not the login-time claim."""
        make_user(
            "alice",
            seeded={"fullname": "A. Liddell", "email": "old@example.com"},
            fullname="Alice Liddell",
            email="alice@example.com",
        )

        member = api.user.get(userid="alice")

        assert member.getProperty("fullname") == "Alice Liddell"
        assert member.getProperty("email") == "alice@example.com"

    def test_the_other_fields_are_served_too(self, make_user):
        """Not just the two anybody remembers."""
        make_user(
            "alice",
            home_page="https://example.com/alice",
            description="Fond of white rabbits",
            location="Wonderland",
        )

        member = api.user.get(userid="alice")

        assert member.getProperty("home_page") == "https://example.com/alice"
        assert member.getProperty("description") == "Fond of white rabbits"
        assert member.getProperty("location") == "Wonderland"

    def test_user_without_a_profile_falls_through(self, acl_users, plugin):
        """A site can hold users the layer knows nothing about."""
        acl_users.source_users.addUser("bob", "bob", "placeholder-password")
        api.user.get(userid="bob").setMemberProperties({"fullname": "Bob"})

        assert plugin.getPropertiesForUser(acl_users.getUserById("bob")) is None
        assert api.user.get(userid="bob").getProperty("fullname") == "Bob"

    def test_empty_profile_field_is_served_as_empty(self, make_user):
        """The Profile is the source of truth, including when it is blank.

        Falling through to the seeded claim would make a field the user
        deliberately cleared reappear at the next page load.
        """
        make_user("alice", seeded={"fullname": "A. Liddell"})

        assert api.user.get(userid="alice").getProperty("fullname") == ""


class TestEnumeration:
    def test_enumerate_by_exact_userid(self, plugin, make_user):
        """The identity join, straight off the index."""
        make_user("alice")

        results = plugin.enumerateUsers(id="alice", exact_match=True)

        assert [record["id"] for record in results] == ["alice"]

    def test_records_carry_the_plugin_id(self, plugin, make_user):
        """PAS needs to know who answered."""
        make_user("alice")

        assert plugin.enumerateUsers(id="alice")[0]["pluginid"] == PLUGIN_ID

    def test_substring_is_the_default(self, plugin, make_user):
        """Matching ``source_users``, which is what callers expect."""
        make_user("alice", fullname="Alice Liddell")

        assert plugin.enumerateUsers(fullname="iddel")

    def test_exact_match_is_not_substring(self, plugin, make_user):
        """And exact means exact."""
        make_user("alice", fullname="Alice Liddell")

        assert not plugin.enumerateUsers(fullname="iddel", exact_match=True)

    def test_criteria_are_ored(self, plugin, make_user):
        """A record matching on email must not be dropped for missing on name."""
        make_user("alice", fullname="Alice Liddell", email="rabbit@example.com")

        results = plugin.enumerateUsers(fullname="nobody", email="rabbit")

        assert [record["id"] for record in results] == ["alice"]

    def test_sequences_are_accepted(self, plugin, make_user):
        """PAS allows every search argument to be a sequence."""
        make_user("alice")
        make_user("bob")

        results = plugin.enumerateUsers(id=["alice", "bob"], exact_match=True)

        assert sorted(record["id"] for record in results) == ["alice", "bob"]

    def test_max_results_is_honoured(self, plugin, make_user):
        """A listing asking for two must not be handed ten."""
        for index in range(5):
            make_user(f"user{index}")

        assert len(plugin.enumerateUsers(max_results=2)) == 2

    def test_no_criteria_enumerates_everybody(self, plugin, make_user):
        """A bare call is "list them all", not "match nothing"."""
        make_user("alice")
        make_user("bob")

        assert len(plugin.enumerateUsers()) == 2

    def test_no_match_is_empty(self, plugin, make_user):
        """And a miss is a miss."""
        make_user("alice")

        assert plugin.enumerateUsers(id="nobody", exact_match=True) == ()

    def test_empty_field_never_matches(self, plugin, make_user):
        """An unfilled field is not a wildcard.

        Without this, searching for the empty string -- which is what an
        over-eager search box sends -- would match every Profile that had not
        filled that field in, on a criterion the caller never meant.
        """
        make_user("alice", fullname="")

        assert plugin.enumerateUsers(fullname="anything") == ()

    def test_properties_for_a_user_without_an_id(self, plugin, acl_users):
        """PAS can hand over a user whose id is empty; do not query on it."""

        class Anonymous:
            """A user with no id."""

            def getId(self):
                """Return no id.

                :returns: ``None``.
                """
                return None

        assert plugin.getPropertiesForUser(Anonymous()) is None


class TestLoginCaseInsensitivity:
    def test_login_matches_regardless_of_case(self, plugin, make_user):
        """Login names are case-insensitive in Plone; FieldIndex is not.

        The index stores the folded form and the plugin folds the query, so
        neither side can drift without this failing.
        """
        make_user("alice", login="Alice@Example.COM")

        assert plugin.enumerateUsers(login="alice@example.com", exact_match=True)
        assert plugin.enumerateUsers(login="ALICE@EXAMPLE.COM", exact_match=True)
        assert plugin.enumerateUsers(login="Alice@Example.COM", exact_match=True)

    def test_substring_login_search_folds_too(self, plugin, make_user):
        """The non-exact path folds on the same rule."""
        make_user("alice", login="Alice@Example.COM")

        assert plugin.enumerateUsers(login="EXAMPLE")


class TestEnumerationStates:
    def test_incomplete_is_enumerated(self, plugin, make_user):
        """A sparse profile is still a working account."""
        make_user("alice")

        assert plugin.enumerateUsers(id="alice", exact_match=True)

    def test_complete_is_enumerated(self, plugin, make_user):
        """So is a filled-in one."""
        profile = make_user("alice")
        with api.env.adopt_roles(["Manager"]):
            api.content.transition(obj=profile, transition="complete")

        assert plugin.enumerateUsers(id="alice", exact_match=True)

    def test_deactivated_is_not_enumerated(self, plugin, make_user):
        """The point of the state."""
        profile = make_user("alice")
        with api.env.adopt_roles(["Manager"]):
            api.content.transition(obj=profile, transition="deactivate")

        assert plugin.enumerateUsers(id="alice", exact_match=True) == ()

    def test_deactivated_profile_still_exists(self, portal, plugin, make_user):
        """Deactivation hides an account; it does not delete one."""
        profile = make_user("alice")
        with api.env.adopt_roles(["Manager"]):
            api.content.transition(obj=profile, transition="deactivate")

        assert "alice" in portal["identity-profiles"].objectIds()

    def test_the_state_list_is_configuration(self, plugin, make_user):
        """A site that only wants completed profiles listed says so."""
        make_user("alice")
        api.portal.set_registry_record(ENUMERATION_STATES_RECORD, ("complete",))

        assert plugin.enumerateUsers(id="alice", exact_match=True) == ()


class TestNoDuplicatesWithSourceUsers:
    def test_both_plugins_answer(self, acl_users, plugin, make_user):
        """The premise: core leaves ``source_users`` enumerating."""
        make_user("alice", fullname="Alice Liddell")

        assert plugin.enumerateUsers(id="alice", exact_match=True)
        assert acl_users.source_users.enumerateUsers(id="alice", exact_match=True)

    def test_pas_itself_returns_two_rows(self, acl_users, make_user):
        """PAS concatenates enumerators and does not deduplicate.

        Pinned deliberately: this is the behaviour the userid agreement below
        exists to survive, and if a future PAS started deduplicating we would
        want to know rather than to keep compensating for it.
        """
        make_user("alice", fullname="Alice Liddell")

        assert len(acl_users.searchUsers(id="alice", exact_match=True)) == 2

    def test_the_rows_agree_on_the_userid(self, acl_users, make_user):
        """Which is what lets every consumer merge them back into one (I1)."""
        make_user("alice", fullname="Alice Liddell")

        rows = acl_users.searchUsers(id="alice", exact_match=True)

        assert {row["userid"] for row in rows} == {"alice"}

    def test_sharing_style_search_returns_one_row(self, acl_users, make_user):
        """The gate's own wording, through the merge the Sharing tab uses."""
        from plone.app.workflow.browser.sharing import merge_search_results

        make_user("alice", fullname="Alice Liddell")

        merged = merge_search_results(acl_users.searchUsers(name="alice"), "userid")

        assert [row["userid"] for row in merged] == ["alice"]

    def test_several_users_each_appear_once(self, acl_users, make_user):
        """Not an artefact of there being only one of them.

        Counted rather than compared against a fixed list: the test layer has
        a user of its own, and asserting the exact set would be asserting
        something about ``plone.app.testing`` instead of about this plugin.
        """
        from plone.app.workflow.browser.sharing import merge_search_results

        ours = {f"user{index}" for index in range(5)}
        for userid in sorted(ours):
            make_user(userid, fullname=f"Number {userid[-1]}")

        raw = [
            row["userid"]
            for row in acl_users.searchUsers(name="user")
            if row["userid"] in ours
        ]
        merged = [
            row["userid"]
            for row in merge_search_results(
                acl_users.searchUsers(name="user"), "userid"
            )
            if row["userid"] in ours
        ]

        assert len(raw) == 10
        assert sorted(merged) == sorted(ours)
