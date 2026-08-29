"""A user may not put themselves in a group.

``group_ids`` is not an ordinary profile field. It is what decides which
groups a user belongs to, and therefore which roles they hold, so writing it
on your own profile is granting yourself those roles. It was declared with the
same write permission as ``fullname`` -- which the owner of a profile holds on
their own profile, by design, because that is what self-service means. Filling
in your name and promoting yourself were the same action.

Found by Érico editing his own profile in the demo, which is the only place
anybody looks at the form.

The fix is a permission of its own, granted to administrators and to nobody
else in any workflow state. These tests are about that permission being
*effective*, so they ask the security machinery rather than reading the
schema: a `write_permission` nothing enforces would satisfy a test that only
checked the declaration.
"""

from AccessControl import getSecurityManager
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from plone import api

import pytest


#: The permission that now guards the field.
EDIT_GROUPS = "pas.plugins.identity: Edit Profile Group Membership"

#: The one that guards every other field, which the owner does hold.
EDIT = "pas.plugins.identity: Edit Profile"


@pytest.fixture
def alice(portal, acl_users):
    """A user with a profile of their own.

    :param portal: The Plone site.
    :param acl_users: The site's PAS instance.
    :returns: Alice's profile.
    """
    acl_users.source_users.addUser("alice", "alice", "placeholder-password")
    api.user.grant_roles(username="alice", roles=["Member"])
    return api.content.create(
        container=portal["identity-profiles"],
        type=PROFILE_PORTAL_TYPE,
        id="alice",
        userid="alice",
        login="alice@example.com",
        fullname="Alice Liddell",
        email="alice@example.com",
    )


def may(userid: str, permission: str, obj) -> bool:
    """Report whether a user holds a permission on an object.

    :param userid: The user to check as.
    :param permission: Permission title.
    :param obj: The object to check on.
    :returns: Whether the permission is held.
    """
    with api.env.adopt_user(username=userid):
        return bool(getSecurityManager().checkPermission(permission, obj))


class TestTheOwnerOfAProfile:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, alice) -> None:
        self.portal = portal
        self.profile = alice

    def test_may_not_edit_their_own_group_membership(self):
        """The bug. Before this, a member could join any group on the site by
        editing their own profile."""
        assert may("alice", EDIT_GROUPS, self.profile) is False

    def test_may_still_edit_the_rest_of_their_profile(self):
        """The control, and the half being kept. If this goes red the fix has
        taken self-service with it."""
        assert may("alice", EDIT, self.profile) is True

    @pytest.mark.parametrize("transition", ["reopen", "deactivate"])
    def test_not_in_any_other_state_either(self, transition: str):
        """The workflow states the permission in all three states, so there
        is no state in which it falls back to being acquired."""
        api.content.transition(obj=self.profile, transition=transition)

        assert may("alice", EDIT_GROUPS, self.profile) is False


class TestAnAdministrator:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, alice, acl_users) -> None:
        self.portal = portal
        self.profile = alice
        acl_users.source_users.addUser("boss", "boss", "placeholder-password")
        api.user.grant_roles(username="boss", roles=["Site Administrator"])

    def test_may_edit_group_membership(self):
        """Somebody has to be able to, or membership becomes unmanageable
        through the form the control panel links to."""
        assert may("boss", EDIT_GROUPS, self.profile) is True


class TestTheFieldIsGuardedByIt:
    """The declaration and the permission have to be the same one.

    Asserted here rather than assumed, because the failure is silent: a field
    pointing at a permission nobody manages is a field whose answer depends on
    where the profile happens to be filed.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_group_ids_names_the_new_permission(self):
        from pas.plugins.identity.core.profile import IUserProfileSchema
        from plone.autoform.interfaces import WRITE_PERMISSIONS_KEY

        permissions = IUserProfileSchema.queryTaggedValue(WRITE_PERMISSIONS_KEY)

        assert permissions["group_ids"] == ("pas.plugins.identity.content.editgroups")

    def test_the_other_fields_still_name_the_ordinary_one(self):
        from pas.plugins.identity.core.profile import IUserProfileSchema
        from plone.autoform.interfaces import WRITE_PERMISSIONS_KEY

        permissions = IUserProfileSchema.queryTaggedValue(WRITE_PERMISSIONS_KEY)

        assert permissions["fullname"] == "pas.plugins.identity.content.edit"
