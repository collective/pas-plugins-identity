"""Listing every user, rather than searching for some (#131).

PAS answers "who are all the users?" -- ``acl_users.getUserIds()``,
``getUsers()``, ``portal_membership.listMembers()``, ``api.user.get_users()``
-- by asking each ``IUserIntrospection`` plugin and concatenating what they
say. A user who signed in through a provider has a Profile and nothing in
``source_users``, so until the profile plugin answered too, those calls left
them out while every search found them.

Concatenated, not merged: PlonePAS never removes a duplicate. A user added
through ``api.user.create`` has a Profile *and* a ``source_users`` credential,
so the profile plugin lists only the users no other introspector already
does.
"""

from pas.plugins.identity.core.pas.profile import PLUGIN_ID
from plone import api
from Products.PlonePAS.interfaces.plugins import IUserIntrospection

import pytest


class TestAUserOnlyTheProfileHolds:
    """The case the issue reports: a federated user, with no credential."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, make_profile) -> None:
        self.portal = portal
        self.acl_users = acl_users
        make_profile("sso-user", login="sso@example.com")

    def test_the_plugin_is_an_introspector(self):
        assert PLUGIN_ID in self.acl_users.plugins.listPluginIds(IUserIntrospection)

    def test_get_user_ids_lists_it(self):
        assert "sso-user" in self.acl_users.getUserIds()

    def test_get_user_names_lists_its_login(self):
        assert "sso@example.com" in self.acl_users.getUserNames()

    def test_get_users_lists_it(self):
        assert "sso-user" in [user.getId() for user in self.acl_users.getUsers()]

    def test_api_user_get_users_lists_it(self):
        assert "sso-user" in [user.getId() for user in api.user.get_users()]

    def test_list_members_lists_it(self):
        membership = api.portal.get_tool("portal_membership")

        assert "sso-user" in [member.getId() for member in membership.listMembers()]


class TestAUserBothStoresHold:
    """``api.user.create`` writes a Profile and a ``source_users`` row."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users) -> None:
        self.acl_users = acl_users
        api.user.create(email="bob@example.com", username="bob")

    def test_both_stores_hold_it(self):
        """Guards the premise: without the row this class tests nothing."""
        assert "bob" in self.acl_users.source_users.getUserIds()
        assert self.acl_users[PLUGIN_ID]._brain_for_userid("bob") is not None

    def test_get_user_ids_lists_it_once(self):
        assert self.acl_users.getUserIds().count("bob") == 1

    def test_get_user_names_lists_it_once(self):
        assert self.acl_users.getUserNames().count("bob") == 1

    def test_api_user_get_users_lists_it_once(self):
        ids = [user.getId() for user in api.user.get_users()]

        assert ids.count("bob") == 1


class TestAUserThatIsNotEnumerated:
    """The same review states as enumeration: a deactivated user is not
    listed, as it is not found."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, make_profile) -> None:
        self.acl_users = acl_users
        profile = make_profile("gone", login="gone@example.com")
        with api.env.adopt_roles(["Manager"]):
            api.content.transition(obj=profile, transition="deactivate")

    def test_get_user_ids_leaves_it_out(self):
        assert "gone" not in self.acl_users.getUserIds()

    def test_get_user_names_leaves_it_out(self):
        assert "gone@example.com" not in self.acl_users.getUserNames()
