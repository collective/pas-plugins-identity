"""Who may read and write a Profile's fields, in each workflow state.

The schema in :mod:`pas.plugins.identity.core.profile` declares a
``read_permission`` and a ``write_permission`` on every field. Declaring one is
not granting it: until this package said who holds them, they were permissions
no rolemap and no workflow mentioned, which does not mean "nobody" -- it means
whatever the Profile happened to acquire from wherever it was filed.

The roles that matter here:

``Owner``
    The local role a user holds on their *own* Profile, computed by
    :mod:`pas.plugins.identity.core.localroles`. Not a site role: alice is
    Owner of alice's Profile and nothing on bob's, which is what makes these
    tests about self-service rather than about privilege.

``Member``
    Everybody signed in. Reaches a ``complete`` Profile's ordinary fields, so
    that a Sharing-tab search can show a name -- and never reaches the email
    address, which is what ``View Personal Identifiable Information`` is for.
"""

from AccessControl import getSecurityManager
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from plone import api

import pytest


#: The field permissions declared on the Profile schema.
EDIT = "pas.plugins.identity: Edit Profile"
VIEW = "pas.plugins.identity: View Profile"
VIEW_PII = "pas.plugins.identity: View Personal Identifiable Information"


@pytest.fixture
def profiles(portal, acl_users):
    """Create two users with a Profile each.

    :param portal: The Plone site.
    :param acl_users: The site's PAS instance.
    :returns: Mapping of userid to Profile.
    """
    created = {}
    for userid in ("alice", "bob"):
        acl_users.source_users.addUser(userid, userid, "placeholder-password")
        api.user.grant_roles(username=userid, roles=["Member"])
        created[userid] = api.content.create(
            container=portal["identity-profiles"],
            type=PROFILE_PORTAL_TYPE,
            id=userid,
            userid=userid,
            login=f"{userid}@example.com",
        )
    return created


def _may(userid: str, permission: str, obj) -> bool:
    """Report whether a user holds a permission on an object.

    :param userid: The user to check as.
    :param permission: Permission title.
    :param obj: The object to check on.
    :returns: Whether the permission is held.
    """
    with api.env.adopt_user(username=userid):
        return bool(getSecurityManager().checkPermission(permission, obj))


#: What stock Plone hands ``Owner`` site-wide with acquisition on, and what
#: ``user_profile_workflow`` therefore has to manage. Owning your own Profile
#: means being able to edit it, and these are the things it must not also
#: come to mean.
OWNER_WOULD_ACQUIRE = (
    "Delete objects",
    "Add portal content",
    "Add portal folders",
    "Manage properties",
    "Modify constrain types",
    "Modify view template",
    "Undo changes",
    "View management screens",
)


class TestOwningYourProfileIsNotOwningPlone:
    """The cost of using ``Owner`` for the self-role, and the fence around it.

    ``Editor`` holds nothing site-wide, so granting it locally granted exactly
    what the workflow said. ``Owner`` holds sixteen permissions with
    acquisition on, and every one the workflow does not manage would land on
    the user whose Profile it is.

    The one that matters most is ``Delete objects``: a user deleting their own
    Profile keeps a login that succeeds and an account whose properties and
    enumeration have stopped working. The rest are smaller and the same shape.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, profiles) -> None:
        self.profiles = profiles

    @pytest.mark.parametrize("permission", OWNER_WOULD_ACQUIRE)
    def test_the_owner_does_not_hold_it(self, permission: str):
        assert not _may("alice", permission, self.profiles["alice"])

    def test_but_they_may_still_edit_it(self):
        """The half being kept. If this goes red the fence is too high."""
        assert _may("alice", EDIT, self.profiles["alice"])


class TestIncomplete:
    """The state a Profile is minted in. The user has to be able to fill it
    in, which is the whole point of the state existing."""

    @pytest.fixture(autouse=True)
    def _setup(self, profiles) -> None:
        self.profiles = profiles

    def test_a_user_may_edit_their_own_profile(self):
        assert _may("alice", EDIT, self.profiles["alice"])

    def test_a_user_may_not_edit_somebody_elses(self):
        assert not _may("bob", EDIT, self.profiles["alice"])

    def test_a_user_may_read_their_own_profile(self):
        assert _may("alice", VIEW, self.profiles["alice"])

    def test_a_user_may_read_their_own_email(self):
        assert _may("alice", VIEW_PII, self.profiles["alice"])

    def test_an_incomplete_profile_is_not_public_to_members(self):
        """It is sparse by definition, and the user has not decided to show
        it to anybody yet."""
        assert not _may("bob", VIEW, self.profiles["alice"])


class TestComplete:
    """Filled in, and therefore worth other members finding."""

    @pytest.fixture(autouse=True)
    def _setup(self, profiles) -> None:
        self.profiles = profiles
        api.content.transition(obj=profiles["alice"], transition="complete")

    def test_members_may_read_it(self):
        """What makes a Sharing-tab search useful."""
        assert _may("bob", VIEW, self.profiles["alice"])

    def test_members_may_not_read_the_email_address(self):
        """The reason the PII permission is separate from the other one. A
        site that wants members to see addresses grants it; nothing here
        decides that on their behalf."""
        assert not _may("bob", VIEW_PII, self.profiles["alice"])

    def test_members_may_not_edit_it(self):
        assert not _may("bob", EDIT, self.profiles["alice"])

    def test_the_user_still_may(self):
        """Completing a Profile is not handing it in."""
        assert _may("alice", EDIT, self.profiles["alice"])


class TestDeactivated:
    """The account should no longer appear anywhere."""

    @pytest.fixture(autouse=True)
    def _setup(self, profiles) -> None:
        self.profiles = profiles
        api.content.transition(obj=profiles["alice"], transition="deactivate")

    def test_the_user_loses_their_own_profile(self):
        """Deactivation is done *to* an account, so leaving its owner able to
        edit their way out of it would make the state advisory."""
        assert not _may("alice", EDIT, self.profiles["alice"])

    def test_members_lose_it_too(self):
        assert not _may("bob", VIEW, self.profiles["alice"])

    def test_an_administrator_keeps_it(self):
        """The data is kept, and somebody has to be able to look at it."""
        assert _may("admin", VIEW, self.profiles["alice"])
