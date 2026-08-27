"""A user may edit their own Profile and nobody else's."""

from . import PROFILE_ID
from pas.plugins.identity.content.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.content.localroles import ProfileSelfRole
from pas.plugins.identity.content.localroles import SELF_ROLE
from plone import api

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


@pytest.fixture
def make_profile(portal, acl_users):
    """Return a factory for a user with a Profile.

    :param portal: The Plone site.
    :param acl_users: The site's PAS instance.
    :returns: Callable taking a userid.
    """

    def factory(userid: str) -> object:
        acl_users.source_users.addUser(userid, userid, "placeholder-password")
        return api.content.create(
            container=portal["identity-profiles"],
            type=PROFILE_PORTAL_TYPE,
            id=userid,
            userid=userid,
            login=f"{userid}@example.com",
        )

    return factory


class TestRolesAreComputed:
    @pytest.fixture(autouse=True)
    def _setup(self, make_profile) -> None:
        self.profile = make_profile("alice")

    def test_owner_gets_editor(self):
        """The self-Editor role."""
        assert ProfileSelfRole(self.profile).getRoles("alice") == (SELF_ROLE,)

    def test_somebody_else_gets_nothing(self):
        """Which is the half that matters."""
        assert ProfileSelfRole(self.profile).getRoles("bob") == ()

    def test_all_roles_lists_the_owner(self):
        """The Sharing tab shows what is granted."""
        assert list(ProfileSelfRole(self.profile).getAllRoles()) == [
            ("alice", (SELF_ROLE,))
        ]

    def test_a_profile_without_a_userid_grants_nothing(self):
        """Half-built content must not become a permission hole."""

        class Bare:
            """A Profile-shaped object with no userid."""

            userid = None

        assert ProfileSelfRole(Bare()).getRoles("alice") == ()
        assert list(ProfileSelfRole(Bare()).getAllRoles()) == []


class TestThroughPAS:
    @pytest.fixture(autouse=True)
    def _setup(self, make_profile) -> None:
        self.make_profile = make_profile
        self.profile = make_profile("alice")
        self.alice = api.user.get(userid="alice")

    def test_user_may_edit_their_own_profile(self):
        """End to end, through the permission machinery."""
        with api.env.adopt_user(user=self.alice):
            assert api.user.has_permission("Modify portal content", obj=self.profile)

    def test_user_may_not_edit_somebody_elses(self):
        """The point of the whole adapter."""
        other = self.make_profile("bob")

        with api.env.adopt_user(user=self.alice):
            assert not api.user.has_permission("Modify portal content", obj=other)

    def test_editor_does_not_carry_delete(self):
        """Owner would; a user deleting their own Profile breaks their account
        while the login keeps succeeding."""
        with api.env.adopt_user(user=self.alice):
            assert not api.user.has_permission("Delete objects", obj=self.profile)
