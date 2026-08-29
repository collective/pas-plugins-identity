"""The group graph, closed over.

Two halves. The first drives
:mod:`pas.plugins.identity.core.nesting` as the pure functions it is -- no
portal, no catalog, just a mapping -- because that is where the cycle and
depth behaviour is decidable. The second proves the plugin actually asks it,
which the first cannot: a correct closure the plugin never calls is a
membership rule nothing enforces.
"""

from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.nesting import build_edges
from pas.plugins.identity.core.nesting import close_over
from pas.plugins.identity.core.nesting import MAX_DEPTH
from pas.plugins.identity.core.nesting import members_of
from plone import api
from zope.lifecycleevent import modified

import pytest


class Brain:
    """A stand-in for a catalog brain, carrying the two attributes read."""

    def __init__(self, group_id: str, group_ids: tuple[str, ...] = ()) -> None:
        """Record what the brain answers.

        :param group_id: The group's own id.
        :param group_ids: The groups it belongs to.
        """
        self.group_id = group_id
        self.group_ids = group_ids


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

    def test_parent_ids_are_what_was_typed(self):
        """The edit form shows the stored edges, not their closure."""
        for group_id in ("staff", "engineering", "developers"):
            self.make_group(group_id)
        self._nest("engineering", "staff")
        self._nest("developers", "engineering")

        assert self.plugin.getGroupParentIds("developers") == ("engineering",)
