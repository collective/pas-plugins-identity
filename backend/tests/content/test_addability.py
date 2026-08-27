"""Where a user or a group may be created, and where they may not.

Both types are addable in exactly one place: the container the registry names
for them. That is enforced by the add permission and by nothing else --
``rolemap.xml`` grants it to no role at all, and
:func:`~pas.plugins.identity.content.container.grant_add_permission` grants it
on the container.

The lock is worth testing from both sides, because each side fails silently in
its own way. Granted too widely, a ``UserProfile`` becomes a thing anybody with
authoring rights can scatter through the site, and PAS enumerates whatever it
finds. Granted too narrowly, the layer looks installed and refuses every user
the moment somebody signs in -- including the machine paths, which run as
Manager and would be just as refused.
"""

from . import PROFILE_ID
from AccessControl import getSecurityManager
from AccessControl.Permission import Permission
from pas.plugins.identity.content.catalog import GROUP_PORTAL_TYPE
from pas.plugins.identity.content.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.content.container import ADD_PERMISSIONS
from pas.plugins.identity.content.container import ADD_ROLES
from pas.plugins.identity.content.container import get_container
from pas.plugins.identity.content.container import GROUP
from pas.plugins.identity.content.container import GROUP_ID_RECORD
from pas.plugins.identity.content.container import PROFILE
from plone import api
from zExceptions import Unauthorized

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


def may_add(obj, kind: str) -> bool:
    """Return whether the current user may add this kind of principal here.

    The observable answer, which is what the FTI asks and therefore the only
    one worth asserting. ``rolesOfPermission`` is *not* it: for a permission
    no rolemap has touched it reports the roles Zope registered the permission
    with, which is ``Manager`` for every ZCML permission and says nothing
    about this object. These tests run as a Manager, so "may a Manager add one
    here" is exactly the question.

    :param obj: The prospective container.
    :param kind: :data:`PROFILE` or :data:`GROUP`.
    :returns: Whether the add permission is held here.
    """
    return bool(getSecurityManager().checkPermission(ADD_PERMISSIONS[kind], obj))


def local_grant(obj, kind: str) -> tuple | list | None:
    """Return the roles set for a kind's add permission *on this object*.

    ``None`` when the object has no setting of its own and acquires whatever
    is above it. A tuple means acquisition is off, a list means it is on --
    that is how ``AccessControl`` stores the distinction, and both halves
    matter here: granted-but-acquiring would make the answer depend on where
    the folder is filed.

    :param obj: The object to look at.
    :param kind: :data:`PROFILE` or :data:`GROUP`.
    :returns: The stored roles, or ``None`` when nothing is stored.
    """
    return Permission(ADD_PERMISSIONS[kind], (), obj).getRoles(default=None)


@pytest.fixture
def container(portal):
    """Return the configured container, which the harness has already made.

    :param portal: The Plone site.
    :returns: The folder both kinds are filed in on this site.
    """
    return get_container()


class TestTheSiteWideAnswerIsNobody:
    """``rolemap.xml`` grants both permissions to no role.

    Stated rather than left out. A permission a rolemap does not mention is
    not a permission nobody has: the object acquires one, and the answer then
    depends on where it happens to be filed.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    @pytest.mark.parametrize("kind", [PROFILE, GROUP])
    def test_not_even_a_manager_may_add_one_at_the_root(self, kind: str):
        assert may_add(self.portal, kind) is False

    @pytest.mark.parametrize("kind", [PROFILE, GROUP])
    def test_the_root_grants_it_to_nobody_and_acquires_nothing(self, kind: str):
        assert local_grant(self.portal, kind) == ()


class TestAnOrdinaryFolder:
    """A folder nobody configured takes neither type."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.folder = api.content.create(
            container=portal, type="Folder", id="somewhere", title="Somewhere"
        )

    def test_a_user_profile_is_refused(self):
        with pytest.raises(Unauthorized):
            api.content.create(
                container=self.folder,
                type=PROFILE_PORTAL_TYPE,
                id="alice",
                userid="alice",
                login="alice@example.com",
            )

    def test_a_user_group_is_refused(self):
        with pytest.raises(Unauthorized):
            api.content.create(
                container=self.folder,
                type=GROUP_PORTAL_TYPE,
                id="editors",
                group_id="editors",
                title="Editors",
            )

    def test_neither_type_is_offered(self):
        """The add menu is the same answer, reached the other way.

        A type that raises on creation but still appears in the menu is a
        worse experience than one that is simply absent, and the two come
        from the same check.
        """
        offered = {fti.getId() for fti in self.folder.allowedContentTypes()}

        assert PROFILE_PORTAL_TYPE not in offered
        assert GROUP_PORTAL_TYPE not in offered


class TestTheConfiguredContainer:
    """The one place both types go, on a site that has not separated them."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, container) -> None:
        self.portal = portal
        self.container = container

    @pytest.mark.parametrize("kind", [PROFILE, GROUP])
    def test_the_permission_is_granted_there(self, kind: str):
        assert may_add(self.container, kind) is True

    @pytest.mark.parametrize("kind", [PROFILE, GROUP])
    def test_it_is_granted_locally_and_not_acquired(self, kind: str):
        """A tuple rather than a list: acquisition is off, so moving the
        folder does not change the answer."""
        assert local_grant(self.container, kind) == tuple(ADD_ROLES)

    def test_a_user_profile_may_be_created(self):
        profile = api.content.create(
            container=self.container,
            type=PROFILE_PORTAL_TYPE,
            id="alice",
            userid="alice",
            login="alice@example.com",
        )

        assert profile.portal_type == PROFILE_PORTAL_TYPE

    def test_a_user_group_may_be_created(self):
        """Both permissions land on a shared container, not only the one whose
        kind happened to create it."""
        group = api.content.create(
            container=self.container,
            type=GROUP_PORTAL_TYPE,
            id="editors",
            group_id="editors",
            title="Editors",
        )

        assert group.portal_type == GROUP_PORTAL_TYPE

    def test_both_types_are_offered(self):
        offered = {fti.getId() for fti in self.container.allowedContentTypes()}

        assert PROFILE_PORTAL_TYPE in offered
        assert GROUP_PORTAL_TYPE in offered


class TestSeparateContainers:
    """A site that files groups apart from users locks them apart too.

    This is why there are two permissions rather than one. With a single
    permission, opening the group container to groups would open it to users
    as well, and the two halves of the lock could not be moved independently.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, container) -> None:
        self.portal = portal
        self.profiles = container
        api.portal.set_registry_record(GROUP_ID_RECORD, "identity-groups")
        self.groups = get_container(create=True, kind=GROUP)

    def test_they_are_different_folders(self):
        assert self.groups.getId() == "identity-groups"
        assert self.groups is not self.profiles

    def test_the_group_container_takes_groups(self):
        assert may_add(self.groups, GROUP) is True

    def test_the_group_container_refuses_users(self):
        assert may_add(self.groups, PROFILE) is False

    def test_the_profile_container_still_takes_users(self):
        assert may_add(self.profiles, PROFILE) is True

    def test_the_profile_container_still_takes_groups(self):
        """It was granted both while the two shared a folder. Pointing the
        group records somewhere else does not revoke that: the folder may
        still hold groups, and revoking would strand them."""
        assert may_add(self.profiles, GROUP) is True


class TestAContainerThisPackageDidNotCreate:
    """The case the install handler and the settings subscriber both miss.

    A policy profile, an operator, or a content import can put the folder
    there afterwards, at the path the records already name. Nothing else
    would ever grant it the permission, and the symptom is a container that
    looks right and refuses every user filed into it.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        api.portal.set_registry_record(GROUP_ID_RECORD, "elsewhere-groups")
        self.made_by_hand = api.content.create(
            container=portal,
            type="Folder",
            id="elsewhere-groups",
            title="Groups, filed by hand",
        )

    def test_it_is_granted_the_permission(self):
        assert may_add(self.made_by_hand, GROUP) is True

    def test_a_group_may_be_created_in_it(self):
        group = api.content.create(
            container=self.made_by_hand,
            type=GROUP_PORTAL_TYPE,
            id="editors",
            group_id="editors",
            title="Editors",
        )

        assert group.portal_type == GROUP_PORTAL_TYPE

    def test_a_folder_somewhere_else_is_untouched(self):
        """The subscriber fires for every folder added anywhere; only the one
        at the configured path is opened."""
        other = api.content.create(
            container=self.portal, type="Folder", id="unrelated", title="Unrelated"
        )

        assert may_add(other, GROUP) is False
