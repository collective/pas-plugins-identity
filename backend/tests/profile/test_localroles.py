"""A user may edit their own Profile and nobody else's (§4.7)."""

from pas.plugins.identity.profile.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.profile.localroles import ProfileSelfRole
from pas.plugins.identity.profile.localroles import SELF_ROLE
from plone import api

import pytest


@pytest.fixture
def make_profile(portal, acl_users):
    """Return a factory for a user with a Profile.

    :param portal: The Plone site.
    :param acl_users: The site's PAS instance.
    :returns: Callable taking a userid.
    """

    def factory(userid: str) -> object:
        acl_users.source_users.addUser(userid, userid, "placeholder-password")
        with api.env.adopt_roles(["Manager"]):
            return api.content.create(
                container=portal["identity-profiles"],
                type=PROFILE_PORTAL_TYPE,
                id=userid,
                userid=userid,
                login=f"{userid}@example.com",
            )

    return factory


@pytest.fixture
def acl_users(portal):
    """The site's PAS instance.

    :param portal: The Plone site.
    :returns: ``acl_users``.
    """
    return api.portal.get_tool("acl_users")


class TestRolesAreComputed:
    def test_owner_gets_editor(self, make_profile):
        """The self-Editor role."""
        profile = make_profile("alice")

        assert ProfileSelfRole(profile).getRoles("alice") == (SELF_ROLE,)

    def test_somebody_else_gets_nothing(self, make_profile):
        """Which is the half that matters."""
        profile = make_profile("alice")

        assert ProfileSelfRole(profile).getRoles("bob") == ()

    def test_all_roles_lists_the_owner(self, make_profile):
        """The Sharing tab shows what is granted."""
        profile = make_profile("alice")

        assert list(ProfileSelfRole(profile).getAllRoles()) == [("alice", (SELF_ROLE,))]

    def test_a_profile_without_a_userid_grants_nothing(self, portal):
        """Half-built content must not become a permission hole."""

        class Bare:
            """A Profile-shaped object with no userid."""

            userid = None

        assert ProfileSelfRole(Bare()).getRoles("alice") == ()
        assert list(ProfileSelfRole(Bare()).getAllRoles()) == []


class TestThroughPAS:
    def test_user_may_edit_their_own_profile(self, make_profile):
        """End to end, through the permission machinery."""
        profile = make_profile("alice")

        with api.env.adopt_user(user=api.user.get(userid="alice")):
            assert api.user.has_permission("Modify portal content", obj=profile)

    def test_user_may_not_edit_somebody_elses(self, make_profile):
        """The point of the whole adapter."""
        make_profile("alice")
        other = make_profile("bob")

        with api.env.adopt_user(user=api.user.get(userid="alice")):
            assert not api.user.has_permission("Modify portal content", obj=other)

    def test_editor_does_not_carry_delete(self, make_profile):
        """Owner would; a user deleting their own Profile breaks their account
        while the login keeps succeeding."""
        profile = make_profile("alice")

        with api.env.adopt_user(user=api.user.get(userid="alice")):
            assert not api.user.has_permission("Delete objects", obj=profile)
