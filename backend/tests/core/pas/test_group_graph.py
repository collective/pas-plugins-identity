"""Two ways the group graph is read, and that they agree (issue #115).

``getGroupsForPrincipal`` walks upwards from a principal's own groups, one
index query per level, and reads no group it does not reach. Everything that
needs the whole graph -- listings, the group control panel, ``@groups`` --
reads it once per request and keeps it on the request.

The first half proves the walk gives the answer the whole graph gives, on the
shapes where a level-by-level walk could differ: a cycle, a group reached two
ways, a chain longer than the bound. The second proves the kept graph is not
kept past the point where it stops being true.
"""

from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.pas import profile as profile_module
from pas.plugins.identity.core.pas.profile import GROUP_STATES_RECORD
from pas.plugins.identity.core.pas.profile import IdentityProfilePlugin
from pas.plugins.identity.core.utils.nesting import close_over
from pas.plugins.identity.core.utils.nesting import MAX_DEPTH
from plone import api
from Products.PlonePAS.plugins.group import PloneGroup
from zope.lifecycleevent import modified

import pytest
import transaction


class TestTheWalk:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, profile_plugin, make_group) -> None:
        self.acl_users = acl_users
        self.plugin = profile_plugin
        self.make_group = make_group
        self.folder = portal["identity-profiles"]

    def _member(self, userid: str, *group_ids: str) -> None:
        """Create a Profile-only user in the given groups.

        :param userid: The userid.
        :param group_ids: Direct memberships.
        """
        api.content.create(
            container=self.folder,
            type=PROFILE_PORTAL_TYPE,
            id=userid,
            userid=userid,
            login=f"{userid}@example.org",
            group_ids=tuple(group_ids),
        )

    def _nest(self, group, *outer: str) -> None:
        """Name the groups one group is in.

        :param group: The inner group.
        :param outer: Its parents.
        """
        group.group_ids = tuple(outer)
        modified(group)

    def _groups_of(self, principal_id: str) -> tuple[str, ...]:
        """Return the plugin's answer for a user or a group.

        :param principal_id: A userid or a group id.
        :returns: Group ids.
        """
        principal = self.acl_users.getUserById(principal_id) or PloneGroup(principal_id)
        return self.plugin.getGroupsForPrincipal(principal)

    def _from_the_whole_graph(self, principal_id: str) -> tuple[str, ...]:
        """Return what the closure over the whole graph answers.

        :param principal_id: A userid or a group id.
        :returns: Group ids.
        """
        edges = self.plugin.group_edges()
        brain = self.plugin._brain_for_userid(principal_id)
        if brain is not None:
            return close_over(tuple(brain.group_ids or ()), edges)
        return tuple(
            group_id
            for group_id in close_over(edges.get(principal_id, ()), edges)
            if group_id != principal_id
        )

    def test_it_agrees_with_the_whole_graph(self):
        """Field edges, tree edges, a deactivated group and a group reached
        two ways, all on one site -- and every principal asked."""
        staff = self.make_group("staff")
        engineering = self.make_group("engineering", container=staff)
        developers = self.make_group("developers", container=engineering)
        contractors = self.make_group("contractors")
        retired = self.make_group("retired")
        self._nest(developers, "contractors", "retired")
        self._nest(contractors, "staff")
        self._nest(retired, "board")
        self.make_group("board")
        api.content.transition(obj=retired, transition="deactivate")
        self._member("alice", "developers")
        self._member("bob", "contractors", "ghosts")
        self._member("carol", "retired")

        principals = (
            "alice",
            "bob",
            "carol",
            "staff",
            "engineering",
            "developers",
            "contractors",
            "retired",
            "board",
        )
        for principal_id in principals:
            assert self._groups_of(principal_id) == self._from_the_whole_graph(
                principal_id
            ), principal_id
        assert self._groups_of("alice") == (
            "contractors",
            "developers",
            "engineering",
            "staff",
        )

    def test_a_group_and_its_container_both_claimed(self):
        """The container is reached twice, once by name and once by the
        tree, and counted once."""
        staff = self.make_group("staff")
        self.make_group("developers", container=staff)
        self._member("alice", "developers", "staff")

        assert self._groups_of("alice") == ("developers", "staff")

    def test_a_cycle_terminates(self):
        self._nest(self.make_group("a"), "b")
        self._nest(self.make_group("b"), "a")
        self._member("alice", "a")

        assert self._groups_of("alice") == ("a", "b")

    def test_a_group_in_a_cycle_is_not_its_own_member(self):
        self._nest(self.make_group("a"), "b")
        self._nest(self.make_group("b"), "a")

        assert self._groups_of("a") == ("b",)

    def test_the_walk_is_bounded(self):
        """At the same depth as the closure over the whole graph."""
        depth = MAX_DEPTH + 5
        for index in range(depth):
            group = self.make_group(f"g{index}")
            self._nest(group, f"g{index + 1}")
        self._member("alice", "g0")

        assert len(self._groups_of("alice")) == MAX_DEPTH
        assert self._groups_of("alice") == self._from_the_whole_graph("alice")

    def test_an_unknown_group_principal_has_none(self):
        assert self._groups_of("no-such-group") == ()

    def test_no_active_state_grants_nothing(self, monkeypatch):
        """No states is a site without the layer's records, and an empty
        state list in a catalog query would match every state."""
        self._nest(self.make_group("developers"), "staff")
        self.make_group("staff")
        self._member("alice", "developers")
        monkeypatch.setattr(IdentityProfilePlugin, "_group_states", lambda self: ())

        assert self._groups_of("alice") == ()
        assert self._groups_of("developers") == ()


class TestTheKeptGraph:
    """Read once per request, and read again as soon as it is out of date."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, profile_plugin, make_group, monkeypatch) -> None:
        self.portal = portal
        self.plugin = profile_plugin
        self.make_group = make_group
        self.reads = 0
        original = profile_module.group_brains

        def counting(catalog):
            self.reads += 1
            return original(catalog)

        # On the module rather than the catalog: the catalog is persistent,
        # and a savepoint taken while it carried a function would pickle it.
        monkeypatch.setattr(profile_module, "group_brains", counting)

    def test_later_readers_read_nothing(self):
        self.make_group("staff")
        assert self.plugin.getGroupIds() == ["staff"]
        self.reads = 0

        self.plugin.enumerateGroups()
        self.plugin.getGroupById("staff")
        self.plugin.getGroupParentIds("staff")
        self.plugin.getNestedGroupIds("staff")

        assert self.reads == 0

    def test_a_group_added_since_is_seen(self):
        self.make_group("staff")
        assert self.plugin.getGroupIds() == ["staff"]

        self.make_group("developers")

        assert self.plugin.getGroupIds() == ["developers", "staff"]

    def test_a_group_deactivated_since_is_gone(self):
        staff = self.make_group("staff")
        assert self.plugin.getGroupIds() == ["staff"]

        api.content.transition(obj=staff, transition="deactivate")

        assert self.plugin.getGroupIds() == []

    def test_a_changed_state_record_is_seen(self):
        self.make_group("staff")
        assert self.plugin.getGroupIds() == ["staff"]

        api.portal.set_registry_record(GROUP_STATES_RECORD, ("nothing",))

        assert self.plugin.getGroupIds() == []

    def test_without_a_request_nothing_is_kept(self, monkeypatch):
        """A script run outside a request still gets a right answer."""
        self.make_group("staff")
        monkeypatch.setattr(profile_module, "getRequest", lambda: None)
        self.reads = 0

        assert self.plugin.getGroupIds() == ["staff"]
        assert self.plugin.getGroupIds() == ["staff"]
        assert self.reads == 2


class TestAcrossAnAbort:
    """An abort rolls the catalog's change counter back, so the next write
    brings it to a value the kept graph was already read at.

    On the functional layer, whose fixtures can be committed: an abort on the
    integration layer also takes the site state every test here starts from.
    """

    @pytest.fixture
    def portal(self, functional):
        """Return the functional portal, for the autouse fixtures to set up.

        :param functional: The functional layer.
        :returns: The portal.
        """
        return functional["portal"]

    def test_an_aborted_write_is_not_seen(self, catalog, profile_plugin, make_group):
        """Brought back to the kept value by bumping the counter, as any write
        in the next transaction would. A group created there would not do: its
        own subscribers read the graph on the way, which re-keys the copy and
        hides the collision."""
        make_group("staff")
        transaction.commit()
        make_group("developers")
        assert profile_plugin.getGroupIds() == ["developers", "staff"]
        kept_at = catalog.getCounter()

        transaction.abort()
        while catalog.getCounter() < kept_at:
            catalog._increment_counter()

        assert catalog.getCounter() == kept_at
        assert profile_plugin.getGroupIds() == ["staff"]
