"""Properties and enumeration wake no Profile objects.

This is the claim the ``[content]`` design was chosen for, and the reason this
package does not build on Products.membrane. It is asserted two ways, because
each alone is weaker than it looks:

* a **load counter** patched over ``ZODB.Connection.setstate``, which is the
  single funnel every ghost activation goes through. It counts what was woken,
  not what is awake at the end.
* a **ghost check**, which confirms the objects were ghosts to begin with --
  without it a counter of zero proves nothing, since an object already in
  memory is never loaded again.

Both are needed. A test that only counted would pass trivially on a warm
cache; a test that only checked ghost state would miss a load followed by a
deactivation.
"""

from . import PROFILE_ID
from pas.plugins.identity.content.catalog import GROUP_PORTAL_TYPE
from pas.plugins.identity.content.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.content.group import Group
from pas.plugins.identity.content.profile import Profile
from plone import api
from Products.CMFCore.indexing import processQueue

import pytest
import transaction
import ZODB.Connection


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


@pytest.fixture
def profiles(portal):
    """Ten Profiles, committed and then ghosted.

    Two things have to happen before these can be ghosts, and both are easy
    to leave out:

    * a savepoint, so the objects are written and become evictable at all --
      an object created in this transaction stays in the connection cache
      whatever we ask of it;
    * a ``processQueue()``, to drain CMFCore's *pending* indexing operations.
      They are flushed lazily, and the flush happens inside the next catalog
      search -- which would wake exactly one Profile per call and make it look
      as though enumeration had woken it. In a real site the queue was drained
      when the request that created the Profile committed; leaving it pending
      here would be measuring the fixture, not the plugin.

    :param portal: The Plone site.
    :returns: The Profile and Group objects, as ghosts.
    """
    container = portal["identity-profiles"]
    created = []
    for group_id in ("editors", "reviewers"):
        created.append(
            api.content.create(
                container=container,
                type=GROUP_PORTAL_TYPE,
                id=group_id,
                group_id=group_id,
                title=group_id.title(),
            )
        )
    for index in range(10):
        created.append(
            api.content.create(
                container=container,
                type=PROFILE_PORTAL_TYPE,
                id=f"user{index}",
                userid=f"user{index}",
                login=f"user{index}@example.com",
                fullname=f"User Number {index}",
                email=f"user{index}@example.com",
                location=f"Room {index}",
                group_ids=("editors",) if index % 2 else (),
            )
        )
    transaction.savepoint(optimistic=True)
    processQueue()
    for profile in created:
        profile._p_deactivate()
    return created


@pytest.fixture
def loads(monkeypatch):
    """Count ZODB object activations, by class name.

    ``Connection.setstate`` is where every ghost is filled in from storage, so
    patching it catches an activation however it was triggered -- attribute
    access, acquisition, or a catalog that decided to be helpful.

    :param monkeypatch: pytest's patcher.
    :returns: A list that accumulates class names as objects are loaded.
    """
    recorded: list[str] = []
    original = ZODB.Connection.Connection.setstate

    def counting_setstate(self, obj):
        """Record the load and delegate.

        :param self: The ZODB connection.
        :param obj: The object being activated.
        """
        recorded.append(type(obj).__name__)
        return original(self, obj)

    monkeypatch.setattr(ZODB.Connection.Connection, "setstate", counting_setstate)
    return recorded


def profile_loads(recorded: list[str]) -> list[str]:
    """Filter a load record down to Profile and Group activations.

    :param recorded: Class names recorded by the ``loads`` fixture.
    :returns: Only the entries for content this layer catalogues.
    """
    return [name for name in recorded if name in (Profile.__name__, Group.__name__)]


class TestTheFixtureItself:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, plugin, profiles, loads) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.plugin = plugin
        self.profiles = profiles
        self.loads = loads

    def test_profiles_start_as_ghosts(self):
        """Without this, a load count of zero would prove nothing."""
        assert [profile._p_changed for profile in self.profiles] == [None] * 12

    def test_the_counter_sees_a_real_load(self):
        """The counter is wired up: touching a Profile registers."""
        profile = next(one for one in self.profiles if isinstance(one, Profile))

        profile.fullname  # noqa: B018 - the point is the side effect

        assert Profile.__name__ in profile_loads(self.loads)


class TestEnumerationWakesNothing:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, plugin, profiles, loads) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.plugin = plugin
        self.profiles = profiles
        self.loads = loads

    def test_enumerate_everybody(self):
        """A bare enumeration returns the ten users and self.loads none of them.

        Ten, not twelve: the two Groups share this catalog and must not leak
        into a user listing.
        """
        results = self.plugin.enumerateUsers()

        assert len(results) == 10
        assert profile_loads(self.loads) == []

    def test_enumerate_by_login(self):
        """The hot path: resolving one login."""
        results = self.plugin.enumerateUsers(
            login="user3@example.com", exact_match=True
        )

        assert [record["id"] for record in results] == ["user3"]
        assert profile_loads(self.loads) == []

    def test_substring_search(self):
        """A Sharing-style search over full names."""
        results = self.plugin.enumerateUsers(fullname="Number 7")

        assert [record["id"] for record in results] == ["user7"]
        assert profile_loads(self.loads) == []

    def test_profiles_are_still_ghosts_afterwards(self):
        """The other half of the claim: nothing was woken and put back."""
        self.plugin.enumerateUsers(fullname="User")

        assert [profile._p_changed for profile in self.profiles] == [None] * 12


class TestPropertiesWakeNothing:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, plugin, profiles, loads) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.plugin = plugin
        self.profiles = profiles
        self.loads = loads

    def test_property_sheet_is_built_from_the_brain(self):
        """Reading a full name is the most frequent read in a Plone site."""
        user = self.acl_users.getUserById("user4")
        sheet = self.plugin.getPropertiesForUser(user)

        assert sheet.getProperty("fullname") == "User Number 4"
        assert sheet.getProperty("email") == "user4@example.com"
        assert sheet.getProperty("location") == "Room 4"
        assert profile_loads(self.loads) == []

    def test_whole_sheet_read_wakes_nothing(self):
        """Every served field, not just the two anybody remembers."""
        user = self.acl_users.getUserById("user4")
        sheet = self.plugin.getPropertiesForUser(user)

        for name in sheet.propertyIds():
            sheet.getProperty(name)

        assert profile_loads(self.loads) == []

    def test_every_user_in_one_pass(self):
        """Rendering a listing reads properties for everybody at once."""
        for index in range(10):
            user = self.acl_users.getUserById(f"user{index}")
            self.plugin.getPropertiesForUser(user)

        assert profile_loads(self.loads) == []


class TestGroupsWakeNothing:
    """Groups ride on the same guarantee, on a hotter path.

    ``getGroupsForPrincipal`` runs on every permission check that touches a
    local role, so if anything here woke an object it would do so constantly.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, plugin, profiles, loads) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.plugin = plugin
        self.profiles = profiles
        self.loads = loads

    def test_groups_for_principal(self):
        """The hottest question in the layer."""
        principal = self.acl_users.getUserById("user1")

        assert self.plugin.getGroupsForPrincipal(principal) == ("editors",)
        assert profile_loads(self.loads) == []

    def test_group_enumeration(self):
        """Rendering the group listing."""
        assert len(self.plugin.enumerateGroups()) == 2
        assert profile_loads(self.loads) == []

    def test_group_members(self):
        """The rare direction, still off the index."""
        assert self.plugin.getGroupMembers("editors") == (
            "user1",
            "user3",
            "user5",
            "user7",
            "user9",
        )
        assert profile_loads(self.loads) == []

    def test_group_ids(self):
        """Introspection too."""
        assert self.plugin.getGroupIds() == ["editors", "reviewers"]
        assert profile_loads(self.loads) == []

    def test_everything_is_still_a_ghost(self):
        """The other half of the claim, over the whole group surface."""
        self.plugin.getGroupsForPrincipal(self.acl_users.getUserById("user1"))
        self.plugin.enumerateGroups()
        self.plugin.getGroupMembers("editors")

        assert [profile._p_changed for profile in self.profiles] == [None] * 12
