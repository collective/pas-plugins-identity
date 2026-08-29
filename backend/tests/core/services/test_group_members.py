"""``GET @group-members/<id>``.

plone.restapi's ``@groups/<id>`` already carries a member list and already
sees the nesting, because it goes through PlonePAS. This endpoint exists for
what that one cannot do on a group page: name each person, search within the
group, and say what feeds into it.
"""

from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.services.groups.get import GroupMembersGet
from plone import api
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from zope.lifecycleevent import modified

import pytest


class GroupMembersCase:
    """Drive the service directly, the way the other service tests do."""

    def listing(self, *segments, **form) -> dict:
        """GET the members of a group.

        :param segments: Path segments after the endpoint name.
        :param form: Query-string parameters.
        :returns: The service's reply.
        """
        self.request.form.update(form)
        service = GroupMembersGet(self.portal, self.request)
        service.segments = list(segments)
        return service.reply()

    def status(self) -> int:
        """Return the status the last reply set.

        :returns: The HTTP status.
        """
        return self.request.response.getStatus()

    def member(self, userid: str, *group_ids: str, fullname: str = "") -> object:
        """Create a user with a Profile in the given groups.

        :param userid: The userid.
        :param group_ids: Direct memberships.
        :param fullname: The name they are shown under.
        :returns: The Profile.
        """
        self.acl_users.source_users.addUser(userid, userid, "placeholder-password")
        return api.content.create(
            container=self.portal["identity-profiles"],
            type=PROFILE_PORTAL_TYPE,
            id=userid,
            userid=userid,
            login=f"{userid}@example.com",
            fullname=fullname or userid.title(),
            group_ids=tuple(group_ids),
        )

    def nest(self, inner: str, *outer: str) -> None:
        """Put one group inside others.

        :param inner: The nested group.
        :param outer: The groups it becomes a member of.
        """
        group = self.portal["identity-profiles"][inner]
        group.group_ids = tuple(outer)
        modified(group)


class TestListing(GroupMembersCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, acl_users, make_group) -> None:
        self.portal = portal
        self.request = request_
        self.acl_users = acl_users
        setRoles(portal, TEST_USER_ID, ["Manager"])
        login(portal, TEST_USER_NAME)
        make_group("staff", title="Staff")
        make_group("developers", title="Developers")
        self.nest("developers", "staff")
        self.member("alice", "developers", fullname="Alice Liddell")
        self.member("bob", "staff", fullname="Bob Cratchit")

    def test_lists_the_direct_members(self):
        """The ordinary case."""
        ids = [item["id"] for item in self.listing("staff")["items"]]

        assert "bob" in ids

    def test_lists_the_members_of_a_nested_group(self):
        """The requirement: everybody in developers is in staff."""
        ids = [item["id"] for item in self.listing("staff")["items"]]

        assert "alice" in ids

    def test_a_row_names_the_person(self):
        """The reason this exists rather than @groups/<id>, whose members are
        bare userids."""
        row = next(i for i in self.listing("staff")["items"] if i["id"] == "alice")

        assert row["fullname"] == "Alice Liddell"
        assert row["login"] == "alice@example.com"
        assert row["profile_url"].endswith("/identity-profiles/alice")

    def test_a_row_says_which_group_it_came_through(self):
        """So a page can account for somebody being on it."""
        row = next(i for i in self.listing("staff")["items"] if i["id"] == "alice")

        assert row["through"] == ["developers"]

    def test_no_address_is_published(self):
        """A membership listing is not a directory of contact details."""
        row = self.listing("staff")["items"][0]

        assert "email" not in row

    def test_rows_are_sorted_by_name(self):
        """A listing that reorders itself between requests is unusable."""
        ids = [item["id"] for item in self.listing("staff")["items"]]

        assert ids == ["alice", "bob"]

    def test_reports_what_is_nested_under_it(self):
        """The group page draws this without a request per level."""
        assert [g["id"] for g in self.listing("staff")["nested_groups"]] == [
            "developers"
        ]

    def test_reports_what_it_is_nested_inside(self):
        """The other direction, for the same page."""
        assert [g["id"] for g in self.listing("developers")["parent_groups"]] == [
            "staff"
        ]

    def test_a_nested_group_entry_carries_its_title(self):
        """A list of ids is not something to show a person."""
        entry = self.listing("staff")["nested_groups"][0]

        assert entry["title"] == "Developers"

    def test_a_group_the_graph_does_not_know_feeds_nobody(self):
        """An empty listing rather than a query with no criteria, which in
        ZCatalog returns nothing anyway and reads as "the group is empty"."""
        from pas.plugins.identity.core.services.groups import member_brains

        plugin = api.portal.get_tool("acl_users")["identity_profile"]

        assert member_brains("no-such-group", plugin) == []

    def test_a_missing_group_id_is_a_400(self):
        """The endpoint is about one group."""
        self.listing()

        assert self.status() == 400

    def test_a_long_listing_carries_its_batching(self):
        """plone.restapi's own batch links, so a caller pages the way it
        pages everything else."""
        for index in range(30):
            self.member(f"member-{index:02d}", "staff")

        result = self.listing("staff")

        assert result["items_total"] == 32
        assert "batching" in result

    def test_the_url_is_traversed_rather_than_supplied(self):
        """The service is published, so the id arrives one segment at a
        time."""
        from pas.plugins.identity.core.services.groups.get import GroupMembersGet

        service = GroupMembersGet(self.portal, self.request)
        service.publishTraverse(self.request, "staff")

        assert service.segments == ["staff"]

    def test_an_unknown_group_is_a_404(self):
        """And so is a group that is not content, deliberately: which groups
        a site has is not worth probing for."""
        self.listing("no-such-group")

        assert self.status() == 404


class TestSearching(GroupMembersCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, acl_users, make_group) -> None:
        self.portal = portal
        self.request = request_
        self.acl_users = acl_users
        setRoles(portal, TEST_USER_ID, ["Manager"])
        login(portal, TEST_USER_NAME)
        make_group("staff", title="Staff")
        self.member("alice", "staff", fullname="Alice Liddell")
        self.member("bob", "staff", fullname="Bob Cratchit")

    def test_matches_a_full_name(self):
        """Searching *within* a group is the thing @groups cannot do."""
        ids = [i["id"] for i in self.listing("staff", query="liddell")["items"]]

        assert ids == ["alice"]

    def test_matches_a_login(self):
        """People are looked up by either."""
        ids = [i["id"] for i in self.listing("staff", query="bob@")["items"]]

        assert ids == ["bob"]

    def test_is_case_insensitive(self):
        """Nobody types the case a name was stored in."""
        ids = [i["id"] for i in self.listing("staff", query="ALICE")["items"]]

        assert ids == ["alice"]

    def test_an_empty_query_returns_everybody(self):
        """A blank search box is not a filter."""
        assert len(self.listing("staff", query="")["items"]) == 2


class TestAccess(GroupMembersCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, acl_users, make_group) -> None:
        self.portal = portal
        self.request = request_
        self.acl_users = acl_users
        setRoles(portal, TEST_USER_ID, ["Manager"])
        login(portal, TEST_USER_NAME)
        make_group("staff", title="Staff")
        make_group("secret", title="Secret")
        self.member("alice", "staff", fullname="Alice Liddell")

    def test_anonymous_is_refused(self):
        """A membership list is personal data about other people."""
        logout()

        self.listing("staff")

        assert self.status() == 401

    def test_a_manager_may_read_any_group(self):
        """The administrator case."""
        self.listing("staff")

        assert self.status() == 200

    def test_an_ordinary_member_may_not_read_a_group_they_are_not_in(self):
        """The other legitimate caller is somebody looking at their own team,
        and this is not their team."""
        setRoles(self.portal, TEST_USER_ID, ["Member"])

        self.listing("secret")

        assert self.status() == 403

    def test_a_member_may_read_their_own_group(self):
        """Which is the case the permission check exists to allow."""
        setRoles(self.portal, TEST_USER_ID, ["Member"])
        login(self.portal, "alice")

        self.listing("staff")

        assert self.status() == 200
