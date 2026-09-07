"""The group graph, closed over.

Two halves. The first drives
:mod:`pas.plugins.identity.core.utils.nesting` as the pure functions it is -- no
portal, no catalog, just a mapping -- because that is where the cycle and
depth behaviour is decidable. The second proves the plugin actually asks it,
which the first cannot: a correct closure the plugin never calls is a
membership rule nothing enforces.
"""

from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.utils.nesting import build_edges
from pas.plugins.identity.core.utils.nesting import close_over
from pas.plugins.identity.core.utils.nesting import MAX_DEPTH
from pas.plugins.identity.core.utils.nesting import members_of
from plone import api
from zope.lifecycleevent import modified

import pytest


class Brain:
    """A stand-in for a catalog brain, carrying the attributes read."""

    def __init__(
        self,
        group_id: str,
        group_ids: tuple[str, ...] = (),
        path: str = "",
    ) -> None:
        """Record what the brain answers.

        :param group_id: The group's own id.
        :param group_ids: The groups it belongs to.
        :param path: Physical path, from which containment is derived. Empty
            for the brains of a site that nests nothing by containment, which
            is what most of these tests are about.
        """
        self.group_id = group_id
        self.group_ids = group_ids
        self.path = path

    def getPath(self) -> str:
        """Answer the way a real brain does.

        :returns: The physical path.
        """
        return self.path


#: developers -> engineering -> staff, and a group off to one side.
GRAPH = {
    "developers": ("engineering",),
    "engineering": ("staff",),
    "staff": (),
    "contractors": (),
}


class TestBuildingTheGraph:
    def test_reads_the_edges_off_brains(self):
        """One query's worth of metadata is the whole graph."""
        edges = build_edges([
            Brain("developers", ("engineering",)),
            Brain("engineering", ()),
        ])

        assert edges == {"developers": ("engineering",), "engineering": ()}

    def test_a_group_with_no_memberships_is_still_a_node(self):
        """It has to be: a node absent from the graph is one that grants
        nothing, and an outer group usually has no memberships of its own."""
        assert build_edges([Brain("staff")]) == {"staff": ()}


class TestContainmentIsTheSameEdge:
    """A group filed inside a group belongs to it, field or no field."""

    def test_the_containing_group_becomes_a_parent(self):
        """The requirement, at its smallest."""
        edges = build_edges([
            Brain("staff", (), "/plone/groups/staff"),
            Brain("developers", (), "/plone/groups/staff/developers"),
        ])

        assert edges["developers"] == ("staff",)

    def test_the_field_and_the_tree_are_unioned(self):
        """Both ways of writing an edge are true of the group, so both are
        read. Stored first, so a page shows what somebody typed before what
        the tree implies."""
        edges = build_edges([
            Brain("staff", (), "/plone/groups/staff"),
            Brain("contractors", (), "/plone/groups/contractors"),
            Brain("developers", ("contractors",), "/plone/groups/staff/developers"),
        ])

        assert edges["developers"] == ("contractors", "staff")

    def test_an_edge_written_twice_is_one_edge(self):
        """Nesting a group under ``staff`` *and* naming ``staff`` in its field
        is the duplicate this has to not produce."""
        edges = build_edges([
            Brain("staff", (), "/plone/groups/staff"),
            Brain("developers", ("staff",), "/plone/groups/staff/developers"),
        ])

        assert edges["developers"] == ("staff",)

    def test_only_the_immediate_container_is_an_edge(self):
        """A grandchild reaches its grandparent through the closure, exactly
        as it would through two field edges. Recording both here would make
        the graph carry the answer instead of the question."""
        edges = build_edges([
            Brain("staff", (), "/plone/groups/staff"),
            Brain("engineering", (), "/plone/groups/staff/engineering"),
            Brain("developers", (), "/plone/groups/staff/engineering/developers"),
        ])

        assert edges["developers"] == ("engineering",)
        assert close_over(("developers",), edges) == (
            "developers",
            "engineering",
            "staff",
        )

    def test_a_group_in_an_ordinary_folder_gains_nothing(self):
        """Only a *group* container is an edge. A site that files its groups
        in folders has drawn no hierarchy by doing so."""
        edges = build_edges([
            Brain("staff", (), "/plone/groups/staff"),
            Brain("developers", (), "/plone/some-folder/developers"),
        ])

        assert edges["developers"] == ()

    def test_a_deactivated_container_conducts_nothing(self):
        """The brains are filtered to the active states before they arrive,
        so an inactive outer group is simply not in the graph -- and an edge
        pointing at a group the graph does not know is dropped by the walk."""
        edges = build_edges([
            Brain("developers", (), "/plone/groups/staff/developers"),
        ])

        assert edges["developers"] == ()
        assert close_over(("developers",), edges) == ("developers",)

    def test_a_brain_with_no_path_is_the_flat_case(self):
        """Which is every graph in the rest of this module."""
        assert build_edges([Brain("staff"), Brain("developers")]) == {
            "staff": (),
            "developers": (),
        }


class TestClosure:
    def test_a_direct_membership(self):
        """The unnested case still works."""
        assert close_over(("staff",), GRAPH) == ("staff",)

    def test_membership_is_inherited_upwards(self):
        """A member of the inner group is a member of the outer one, which is
        the whole feature."""
        assert close_over(("developers",), GRAPH) == (
            "developers",
            "engineering",
            "staff",
        )

    def test_an_unknown_group_is_dropped(self):
        """It is deleted or deactivated, and both mean it grants nothing."""
        assert close_over(("developers", "gone"), GRAPH) == (
            "developers",
            "engineering",
            "staff",
        )

    def test_a_cycle_terminates(self):
        """Two edit forms that each looked reasonable can produce one, so it
        is an ordinary input rather than an error."""
        cyclic = {"a": ("b",), "b": ("a",)}

        assert close_over(("a",), cyclic) == ("a", "b")

    def test_a_self_reference_terminates(self):
        """The shortest cycle."""
        assert close_over(("a",), {"a": ("a",)}) == ("a",)

    def test_the_walk_is_bounded(self):
        """A graph built by an import rather than by a person degrades into a
        missing grant, not a request that never returns."""
        depth = MAX_DEPTH + 10
        chain = {f"g{i}": (f"g{i + 1}",) for i in range(depth)}
        chain[f"g{depth}"] = ()

        result = close_over(("g0",), chain)

        assert len(result) == MAX_DEPTH
        assert "g0" in result

    def test_nothing_claimed_is_nothing_granted(self):
        """The common case on a site that does not nest anything."""
        assert close_over((), GRAPH) == ()


class TestTheOtherDirection:
    def test_includes_the_group_itself(self):
        """So a caller can hand the whole answer to one catalog query rather
        than running one per level."""
        assert "staff" in members_of("staff", GRAPH)

    def test_gathers_the_groups_that_feed_in(self):
        """Everybody in developers is in staff, at two removes."""
        assert members_of("staff", GRAPH) == (
            "developers",
            "engineering",
            "staff",
        )

    def test_a_leaf_feeds_only_itself(self):
        """Nothing is nested under developers."""
        assert members_of("developers", GRAPH) == ("developers",)

    def test_an_unknown_group_feeds_nothing(self):
        """Rather than answering with the id it was handed, which would make
        a deleted group look like an empty one."""
        assert members_of("gone", GRAPH) == ()

    def test_a_cycle_terminates(self):
        """Same graph, walked the other way."""
        assert members_of("a", {"a": ("b",), "b": ("a",)}) == ("a", "b")


class TestThroughThePlugin:
    """The half the unit tests cannot see: that PAS gets the closed answer.

    Driven through ``api.group.get_groups`` rather than through the plugin
    method, because a correct plugin Plone never reaches passes every test
    written against the plugin.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, make_group, profile_plugin) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.make_group = make_group
        self.plugin = profile_plugin

    def _member(self, userid: str, *group_ids: str) -> object:
        """Create a user with a Profile in the given groups.

        :param userid: The userid.
        :param group_ids: Direct memberships.
        :returns: The Profile.
        """
        self.acl_users.source_users.addUser(userid, userid, "placeholder-password")
        return api.content.create(
            container=self.portal["identity-profiles"],
            type=PROFILE_PORTAL_TYPE,
            id=userid,
            userid=userid,
            login=f"{userid}@example.com",
            group_ids=tuple(group_ids),
        )

    def _groups_of(self, userid: str) -> set[str]:
        """Return the ids of the groups a user is in, as Plone answers it.

        Through ``api.group.get_groups`` rather than the plugin, because a
        correct plugin Plone never reaches passes every test written against
        the plugin.

        :param userid: The userid.
        :returns: Group ids.
        """
        return {group.getId() for group in api.group.get_groups(username=userid)}

    def _nest(self, inner: str, *outer: str) -> None:
        """Put one group inside others.

        :param inner: The nested group.
        :param outer: The groups it becomes a member of.
        """
        group = self.portal["identity-profiles"][inner]
        group.group_ids = tuple(outer)
        # ``modified`` rather than ``reindexObject``: the Profile catalog is
        # kept in step by the subscriber on IObjectModifiedEvent, and a write
        # nobody reindexed there is a write nothing in this layer can see.
        modified(group)

    def test_a_member_of_an_inner_group_is_in_the_outer_one(self):
        """The requirement, stated as a permission question."""
        self.make_group("staff")
        self.make_group("developers")
        self._nest("developers", "staff")
        self._member("alice", "developers")

        assert self._groups_of("alice") >= {
            "developers",
            "staff",
        }

    def test_nesting_is_transitive(self):
        """Two levels, because one level can be got right by accident."""
        for group_id in ("staff", "engineering", "developers"):
            self.make_group(group_id)
        self._nest("engineering", "staff")
        self._nest("developers", "engineering")
        self._member("alice", "developers")

        assert self._groups_of("alice") >= {
            "developers",
            "engineering",
            "staff",
        }

    def test_deactivating_the_middle_group_cuts_the_chain(self):
        """A deactivated group must not conduct, or deactivating one is not a
        control over what it grants."""
        for group_id in ("staff", "engineering", "developers"):
            self.make_group(group_id)
        self._nest("engineering", "staff")
        self._nest("developers", "engineering")
        self._member("alice", "developers")
        api.content.transition(
            obj=self.portal["identity-profiles"]["engineering"], transition="deactivate"
        )

        groups = self._groups_of("alice")

        assert "developers" in groups
        assert "engineering" not in groups
        assert "staff" not in groups

    def test_the_outer_group_lists_the_inner_members(self):
        """The other direction, through the introspection API the group
        control panel reads."""
        self.make_group("staff")
        self.make_group("developers")
        self._nest("developers", "staff")
        self._member("alice", "developers")
        self._member("bob", "staff")

        assert set(self.plugin.getGroupMembers("staff")) == {"alice", "bob"}

    def test_a_members_listing_returns_users_not_groups(self):
        """PAS expects userids here, and a group id among them would be
        resolved as a user by everything that reads the answer."""
        self.make_group("staff")
        self.make_group("developers")
        self._nest("developers", "staff")
        self._member("alice", "developers")

        assert "developers" not in self.plugin.getGroupMembers("staff")

    def test_nested_group_ids_excludes_the_group_itself(self):
        """A caller asking what is inside a group does not want it back."""
        self.make_group("staff")
        self.make_group("developers")
        self._nest("developers", "staff")

        assert self.plugin.getNestedGroupIds("staff") == ("developers",)

    def test_an_unknown_group_has_no_members(self):
        """An empty answer rather than a query with no criteria, which in
        ZCatalog returns nothing anyway and reads as an empty group."""
        assert self.plugin.getGroupMembers("no-such-group") == ()

    def test_an_unknown_group_has_no_parents(self):
        """Asked by the group page about a group that has just been deleted."""
        assert self.plugin.getGroupParentIds("no-such-group") == ()

    def test_parent_ids_are_what_was_typed(self):
        """The edit form shows the stored edges, not their closure."""
        for group_id in ("staff", "engineering", "developers"):
            self.make_group(group_id)
        self._nest("engineering", "staff")
        self._nest("developers", "engineering")

        assert self.plugin.getGroupParentIds("developers") == ("engineering",)


class TestNestingByContainment:
    """A ``UserGroup`` filed inside a ``UserGroup``, driven as Plone sees it.

    The same requirements as :class:`TestThroughThePlugin`, written against
    the tree rather than the field. Both have to hold: containment is not a
    replacement for ``group_ids``, it is a second way of writing one edge, and
    a site can use either or both.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, make_group, profile_plugin) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.make_group = make_group
        self.plugin = profile_plugin
        self.groups = portal["identity-profiles"]

    def _member(self, userid: str, *group_ids: str) -> object:
        """Create a user with a Profile in the given groups.

        :param userid: The userid.
        :param group_ids: Direct memberships.
        :returns: The Profile.
        """
        self.acl_users.source_users.addUser(userid, userid, "placeholder-password")
        return api.content.create(
            container=self.groups,
            type=PROFILE_PORTAL_TYPE,
            id=userid,
            userid=userid,
            login=f"{userid}@example.com",
            group_ids=tuple(group_ids),
        )

    def _groups_of(self, userid: str) -> set[str]:
        """Return the ids of the groups a user is in, as Plone answers it.

        ``AuthenticatedUsers`` is dropped: it is Plone's virtual group, in
        every answer for every logged-in principal, and carrying it would make
        each assertion here restate a fact about Plone rather than one about
        nesting.

        :param userid: The userid.
        :returns: Group ids.
        """
        return {group.getId() for group in api.group.get_groups(username=userid)} - {
            "AuthenticatedUsers"
        }

    def test_a_group_may_be_added_inside_a_group(self):
        """The FTI allows it, and the add permission is acquired from the
        container the outer group lives in."""
        staff = self.make_group("staff")

        inner = self.make_group("developers", container=staff)

        assert inner.getId() == "developers"
        assert "developers" in staff.objectIds()

    def test_a_member_of_a_contained_group_is_in_the_container(self):
        """The requirement, stated as a permission question."""
        staff = self.make_group("staff")
        self.make_group("developers", container=staff)
        self._member("alice", "developers")

        assert self._groups_of("alice") == {"developers", "staff"}

    def test_containment_nests_to_any_depth(self):
        """Two levels of tree, closed over the same way two fields would be."""
        staff = self.make_group("staff")
        engineering = self.make_group("engineering", container=staff)
        self.make_group("developers", container=engineering)
        self._member("alice", "developers")

        assert self._groups_of("alice") == {"developers", "engineering", "staff"}

    def test_the_container_lists_the_contained_members(self):
        """The other direction, which is what a group page reads."""
        staff = self.make_group("staff")
        self.make_group("developers", container=staff)
        self._member("alice", "developers")
        self._member("bob", "staff")

        assert set(self.plugin.getGroupMembers("staff")) == {"alice", "bob"}

    def test_nested_group_ids_reports_the_tree(self):
        """``getNestedGroupIds`` cannot tell how the edge was written."""
        staff = self.make_group("staff")
        engineering = self.make_group("engineering", container=staff)
        self.make_group("developers", container=engineering)

        assert self.plugin.getNestedGroupIds("staff") == (
            "developers",
            "engineering",
        )

    def test_parent_ids_report_the_containing_group(self):
        """What a group page shows beside a group it is looking at."""
        staff = self.make_group("staff")
        self.make_group("developers", container=staff)

        assert self.plugin.getGroupParentIds("developers") == ("staff",)

    def test_the_field_and_the_tree_are_unioned(self):
        """A group can be filed under one group and name another."""
        staff = self.make_group("staff")
        self.make_group("contractors")
        inner = self.make_group("developers", container=staff)
        inner.group_ids = ("contractors",)
        modified(inner)
        self._member("alice", "developers")

        assert self._groups_of("alice") == {"developers", "staff", "contractors"}

    def test_an_edge_written_both_ways_is_not_duplicated(self):
        """Filing a group under ``staff`` and also naming ``staff`` is the
        obvious thing for an operator to do, and it must not produce two of
        anything."""
        staff = self.make_group("staff")
        inner = self.make_group("developers", container=staff)
        inner.group_ids = ("staff",)
        modified(inner)

        assert self.plugin.getGroupParentIds("developers") == ("staff",)
        assert self.plugin.getNestedGroupIds("staff") == ("developers",)

    def test_a_contained_group_is_a_group_of_this_site(self):
        """It is enumerable, grantable and listed. A hierarchy whose inner
        teams could not be granted a role would be a display feature."""
        staff = self.make_group("staff")
        self.make_group("developers", container=staff)

        assert set(self.plugin.getGroupIds()) == {"staff", "developers"}
        assert {record["id"] for record in self.plugin.enumerateGroups()} == {
            "staff",
            "developers",
        }

    def test_every_group_is_listed_once(self):
        """The listing is per group, not per way of reaching one."""
        staff = self.make_group("staff")
        inner = self.make_group("developers", container=staff)
        inner.group_ids = ("staff",)
        modified(inner)

        ids = [record["id"] for record in self.plugin.enumerateGroups()]

        assert sorted(ids) == ["developers", "staff"]

    def test_deactivating_the_container_cuts_the_grant(self):
        """A deactivated group does not conduct, however the edge was
        written."""
        staff = self.make_group("staff")
        self.make_group("developers", container=staff)
        self._member("alice", "developers")
        api.content.transition(obj=staff, transition="deactivate")

        groups = self._groups_of("alice")

        assert "developers" in groups
        assert "staff" not in groups

    def test_moving_a_group_moves_its_membership(self):
        """No edit, no reindex by hand: the tree is the edge, so re-filing a
        group is the whole operation."""
        staff = self.make_group("staff")
        self.make_group("contractors")
        self.make_group("developers", container=staff)
        self._member("alice", "developers")
        assert self._groups_of("alice") == {"developers", "staff"}

        api.content.move(source=staff["developers"], target=self.groups["contractors"])

        assert self._groups_of("alice") == {"developers", "contractors"}

    def test_a_contained_group_is_resolvable_by_id(self):
        """Reading one, which the catalog already answered."""
        staff = self.make_group("staff")
        self.make_group("developers", container=staff)

        assert api.group.get("developers") is not None
        assert self.plugin.getGroupById("developers") is not None

    def test_a_user_can_be_added_to_a_contained_group(self):
        """The write side resolves the group as an *object*, which used to be
        a lookup in the one configured folder. A nested group was invisible to
        it, so this declined and said nothing."""
        staff = self.make_group("staff")
        self.make_group("developers", container=staff)
        self._member("alice")

        api.group.add_user(groupname="developers", username="alice")

        assert self._groups_of("alice") == {"developers", "staff"}

    def test_a_user_can_be_removed_from_a_contained_group(self):
        """The counterpart, and the one whose silent failure would leave
        access in place after somebody had revoked it."""
        staff = self.make_group("staff")
        self.make_group("developers", container=staff)
        self._member("alice", "developers")

        api.group.remove_user(groupname="developers", username="alice")

        assert self._groups_of("alice") == set()

    def test_a_contained_group_can_be_deleted(self):
        """Removal reaches the object, so it too was blind to a nested
        group -- and a group that cannot be deleted keeps granting."""
        staff = self.make_group("staff")
        self.make_group("developers", container=staff)

        api.group.delete(groupname="developers")

        assert "developers" not in staff.objectIds()
        assert self.plugin.getGroupById("developers") is None
