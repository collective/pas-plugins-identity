"""C6: properties and enumeration wake no Profile objects.

This is the claim the ``[profile]`` design was chosen for, and the reason this
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

from pas.plugins.identity.profile.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.profile.content.profile import Profile
from pas.plugins.identity.profile.pas import PLUGIN_ID
from plone import api
from Products.CMFCore.indexing import processQueue

import pytest
import transaction
import ZODB.Connection


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
    :returns: The Profile objects, as ghosts.
    """
    container = portal["identity-profiles"]
    created = []
    with api.env.adopt_roles(["Manager"]):
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
    """Filter a load record down to Profile activations.

    :param recorded: Class names recorded by the ``loads`` fixture.
    :returns: Only the Profile entries.
    """
    return [name for name in recorded if name == Profile.__name__]


class TestTheFixtureItself:
    def test_profiles_start_as_ghosts(self, profiles):
        """Without this, a load count of zero would prove nothing."""
        assert [profile._p_changed for profile in profiles] == [None] * 10

    def test_the_counter_sees_a_real_load(self, profiles, loads):
        """The counter is wired up: touching a Profile registers."""
        profiles[0].fullname  # noqa: B018 - the point is the side effect

        assert profile_loads(loads) == [Profile.__name__]


class TestEnumerationWakesNothing:
    def test_enumerate_everybody(self, plugin, profiles, loads):
        """A bare enumeration returns all ten and loads none of them."""
        results = plugin.enumerateUsers()

        assert len(results) == 10
        assert profile_loads(loads) == []

    def test_enumerate_by_login(self, plugin, profiles, loads):
        """The hot path: resolving one login."""
        results = plugin.enumerateUsers(login="user3@example.com", exact_match=True)

        assert [record["id"] for record in results] == ["user3"]
        assert profile_loads(loads) == []

    def test_substring_search(self, plugin, profiles, loads):
        """A Sharing-style search over full names."""
        results = plugin.enumerateUsers(fullname="Number 7")

        assert [record["id"] for record in results] == ["user7"]
        assert profile_loads(loads) == []

    def test_profiles_are_still_ghosts_afterwards(self, plugin, profiles):
        """The other half of the claim: nothing was woken and put back."""
        plugin.enumerateUsers(fullname="User")

        assert [profile._p_changed for profile in profiles] == [None] * 10


class TestPropertiesWakeNothing:
    def test_property_sheet_is_built_from_the_brain(
        self, plugin, profiles, acl_users, loads
    ):
        """Reading a full name is the most frequent read in a Plone site."""
        user = acl_users.getUserById("user4")
        sheet = plugin.getPropertiesForUser(user)

        assert sheet.getProperty("fullname") == "User Number 4"
        assert sheet.getProperty("email") == "user4@example.com"
        assert sheet.getProperty("location") == "Room 4"
        assert profile_loads(loads) == []

    def test_whole_sheet_read_wakes_nothing(self, plugin, profiles, acl_users, loads):
        """Every served field, not just the two anybody remembers."""
        user = acl_users.getUserById("user4")
        sheet = plugin.getPropertiesForUser(user)

        for name in sheet.propertyIds():
            sheet.getProperty(name)

        assert profile_loads(loads) == []

    def test_every_user_in_one_pass(self, plugin, profiles, acl_users, loads):
        """Rendering a listing reads properties for everybody at once."""
        for index in range(10):
            user = acl_users.getUserById(f"user{index}")
            plugin.getPropertiesForUser(user)

        assert profile_loads(loads) == []
