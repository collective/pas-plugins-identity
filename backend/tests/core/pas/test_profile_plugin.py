"""The profile PAS plugin's contract.

Zero-wake is asserted separately, in ``test_zero_wake``. What is asserted here
is that the plugin gives the *right* answers: that a Profile outranks the
property sheet core seeded at first login, that a user enumerated by both this
plugin and ``source_users`` still shows up once, that login names match
regardless of case, and that a deactivated Profile disappears from
enumeration without disappearing from the site.
"""

from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.pas.profile import ENUMERATION_STATES_RECORD
from pas.plugins.identity.core.pas.profile import PLUGIN_ID
from plone import api
from Products.PluggableAuthService.interfaces.plugins import IPropertiesPlugin
from Products.PluggableAuthService.interfaces.plugins import IUserEnumerationPlugin

import pytest


@pytest.fixture
def make_user(portal, acl_users):
    """Return a factory for a user shaped the way a login leaves one.

    Core mints a userid, creates a ``source_users`` account with a placeholder
    password and seeds ``mutable_properties`` from the provider's claims. The
    profile plugin then adds a Profile. Reproducing both halves is the
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
    def _setup(self, portal, acl_users, profile_plugin) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.plugin = profile_plugin

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
    def _setup(self, portal, acl_users, profile_plugin, make_user) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.plugin = profile_plugin
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

    def test_empty_profile_field_falls_through(self):
        """A blank Profile field is not an answer of its own.

        **This reverses a decision.** It used to assert the opposite -- the
        Profile as the source of truth including when blank -- on the grounds
        that falling through would make a field the user deliberately cleared
        reappear at the next page load. That cost turned out to be much
        smaller than the one it was paying for.

        PAS stops at the first sheet that *has* a property, not the first with
        a value for it, and this plugin declares all five on every Profile
        because that is what routes a write here rather than into
        ``portal_memberdata``. So "blank means blank" did not stay inside this
        layer: it erased what ``portal_memberdata`` held from the user
        listing, the author page and the ``id_token``, for every user whose
        Profile was minted before it carried the field -- which is every user
        who existed when the layer was installed, and every federated user
        whose provider withheld a claim.

        The reappearing-value case is real and is the accepted trade
        (Érico, 2026-08-28). It needs a user to clear a field through the
        dexterity edit form, which writes the object rather than the sheet and
        so leaves ``portal_memberdata`` holding the old value.
        """
        self.make_user("alice", seeded={"fullname": "A. Liddell"})

        assert api.user.get(userid="alice").getProperty("fullname") == "A. Liddell"


class TestEnumeration:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, profile_plugin, make_user) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.plugin = profile_plugin
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
    def _setup(self, portal, acl_users, profile_plugin, make_user) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.plugin = profile_plugin
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
    def _setup(self, portal, acl_users, profile_plugin, make_user) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.plugin = profile_plugin
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
    def _setup(self, portal, acl_users, profile_plugin, make_user) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.plugin = profile_plugin
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


class TestDeletingAUser:
    """The object *is* the account, so deleting the user has to reach it.

    This did not exist, and the failure was silent in the way that matters:
    PlonePAS hands a deletion to whichever plugins implement
    ``IUserManagement``, this package implemented none, and ``source_users``
    removed whatever it held -- nothing at all, for anybody who signed in
    through a provider. The Profile stayed, kept answering enumeration and
    kept serving the property sheet, and the site had reported success.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, profile_plugin, make_user) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.plugin = profile_plugin
        self.make_user = make_user

    def test_the_profile_is_deleted(self):
        self.make_user("alice", fullname="Alice Liddell")

        api.user.delete(username="alice")

        assert "alice" not in self.portal["identity-profiles"]

    def test_the_user_is_gone(self):
        """Which is the question the caller actually asked."""
        self.make_user("alice", fullname="Alice Liddell")

        api.user.delete(username="alice")

        assert api.user.get(userid="alice") is None

    def test_enumeration_stops_answering(self):
        """A Profile left behind goes on being a user in every search."""
        self.make_user("alice", fullname="Alice Liddell")

        api.user.delete(username="alice")

        assert self.plugin.enumerateUsers(id="alice", exact_match=True) == ()

    def test_a_userid_it_does_not_hold_is_declined(self):
        """``KeyError`` is how PAS is told to try the next plugin, and it is
        what ``ZODBUserManager`` raises for the same reason. PAS swallows it;
        returning false instead would claim a deletion that did not happen."""
        with pytest.raises(KeyError):
            self.plugin.doDeleteUser("nobody-at-all")

    def test_the_identity_records_are_left_alone(self):
        """An identity outliving an account is by design: it is what lets the
        same person sign back in under the same userid. Removing one is a
        separate decision, and a login through an orphaned identity says so."""
        from pas.plugins.identity.core.pas import PLUGIN_ID as CORE_PLUGIN_ID

        self.make_user("alice", fullname="Alice Liddell")
        core = self.acl_users[CORE_PLUGIN_ID]
        core.store.add("dex", "subject-1", "alice", {})

        api.user.delete(username="alice")

        assert core.store.userid_for("dex", "subject-1") == "alice"


class TestTheUiIsToldItMayDelete:
    """``canDelete`` on the member walks the ``IUserManagement`` plugins and
    asks each one that provides ``IDeleteCapability``. Without an answer here
    the users listing offered no delete button for a Profile-backed user."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, profile_plugin, make_user) -> None:
        self.portal = portal
        self.plugin = profile_plugin
        self.make_user = make_user

    def test_a_user_with_a_profile_may_be_deleted(self):
        self.make_user("alice", fullname="Alice Liddell")

        assert self.plugin.allowDeletePrincipal("alice") is True

    def test_a_userid_with_no_profile_may_not(self):
        """Not a refusal of the deletion, a refusal to claim it: the userid
        belongs to some other plugin, and that plugin answers for it."""
        assert self.plugin.allowDeletePrincipal("nobody-at-all") is False


class TestItIsNotACredentialStore:
    """Which plugin holds a password is a separate question with a separate
    answer, and answering it twice would give a site two ways to write the
    same credential."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, profile_plugin) -> None:
        self.portal = portal
        self.plugin = profile_plugin

    def test_changing_a_password_is_refused(self):
        """``RuntimeError`` is what PlonePAS's ``userSetPassword`` expects
        from a plugin that cannot set one, and it moves on to the next."""
        with pytest.raises(RuntimeError, match="does not store passwords"):
            self.plugin.doChangeUser("alice", "hunter2!")
