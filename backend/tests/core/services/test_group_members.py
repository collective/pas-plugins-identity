"""``GET @group-members/<id>``.

plone.restapi's ``@groups/<id>`` already carries a member list and already
sees the nesting, because it goes through PlonePAS. This endpoint exists for
what that one cannot do on a group page: name each person, search within the
group, and say what feeds into it.
"""

from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.interfaces import IGroupMemberSerializer
from pas.plugins.identity.core.serializers.groupmember import GroupMemberSerializer
from pas.plugins.identity.core.services.groups.get import GroupMembersGet
from pas.plugins.identity.interfaces import IBrowserLayer
from plone import api
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from Products.CMFCore.interfaces import ISiteRoot
from zope.component import getGlobalSiteManager
from zope.component import getMultiAdapter
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

    def test_a_nested_group_entry_links_to_its_page(self):
        """``@id`` is this listing for that group, an API resource rather than
        a page, so the group page had nowhere to send a reader."""
        developers = self.portal["identity-profiles"]["developers"]

        entry = self.listing("staff")["nested_groups"][0]

        assert entry["group_url"] == developers.absolute_url()

    def test_a_parent_group_entry_links_to_its_page(self):
        """The other list on the same page, built the same way."""
        staff = self.portal["identity-profiles"]["staff"]

        entry = self.listing("developers")["parent_groups"][0]

        assert entry["group_url"] == staff.absolute_url()

    def test_a_group_with_no_page_has_no_url(self):
        """A stored membership of a group this site holds no entry for.
        ``None`` rather than a guessed URL, as ``profile_url`` is for a member
        with no Profile."""
        self.nest("developers", "staff", "ghost")

        entries = {g["id"]: g for g in self.listing("developers")["parent_groups"]}

        assert entries["ghost"]["group_url"] is None

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

    @pytest.mark.parametrize(
        "query,found",
        [
            # Searching *within* a group is the thing @groups cannot do.
            ("liddell", "alice"),
            # People are looked up by full name or by login.
            ("bob@", "bob"),
            # Nobody types the case a name was stored in.
            ("ALICE", "alice"),
        ],
        ids=["a-full-name", "a-login", "the-wrong-case"],
    )
    def test_it_matches(self, query: str, found: str):
        ids = [i["id"] for i in self.listing("staff", query=query)["items"]]

        assert ids == [found]

    def test_an_empty_query_returns_everybody(self):
        """A blank search box is not a filter."""
        assert len(self.listing("staff", query="")["items"]) == 2


class TestTotals(GroupMembersCase):
    """How big a group is, which a group page shows instead of a list."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, acl_users, make_group) -> None:
        self.portal = portal
        self.request = request_
        self.acl_users = acl_users
        setRoles(portal, TEST_USER_ID, ["Manager"])
        login(portal, TEST_USER_NAME)
        make_group("staff", title="Staff")
        make_group("developers", title="Developers")
        make_group("empty", title="Empty")
        self.nest("developers", "staff")
        self.member("alice", "developers", fullname="Alice Liddell")
        self.member("bob", "staff", fullname="Bob Cratchit")
        self.member("carol", "staff", "developers", fullname="Carol Danvers")

    def test_the_total_counts_nested_members(self):
        assert self.listing("staff")["members_total"] == 3

    def test_the_direct_total_leaves_out_nested_members(self):
        """Alice is in staff only through developers; Carol is in both."""
        assert self.listing("staff")["direct_members_total"] == 2

    def test_a_nested_group_counts_its_own_members(self):
        result = self.listing("developers")

        assert (result["members_total"], result["direct_members_total"]) == (2, 2)

    def test_the_totals_ignore_the_search(self):
        """A page searching a group still says how big the group is."""
        result = self.listing("staff", query="alice")

        assert result["items_total"] == 1
        assert (result["members_total"], result["direct_members_total"]) == (3, 2)

    def test_an_empty_group_counts_nobody(self):
        result = self.listing("empty")

        assert (result["members_total"], result["direct_members_total"]) == (0, 0)


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

    def test_a_site_administrator_may_read_any_group(self):
        """They hold the permission ``PATCH @groups`` asks for, not
        ``Manage users``, and must see the members they may change."""
        setRoles(self.portal, TEST_USER_ID, ["Site Administrator"])

        self.listing("secret")

        assert self.status() == 200


class TestTheRow(GroupMembersCase):
    """What one member looks like, and what rendering one costs."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, acl_users, make_group) -> None:
        self.portal = portal
        self.request = request_
        self.acl_users = acl_users
        setRoles(portal, TEST_USER_ID, ["Manager"])
        login(portal, TEST_USER_NAME)
        make_group("staff", title="Staff")
        self.alice = self.member("alice", "staff", fullname="Alice Liddell")
        self.member("bob", "staff", fullname="Bob Cratchit")

    def row(self, userid: str = "alice") -> dict:
        """Return one member's row.

        :param userid: Whose row.
        :returns: The row.
        """
        items = self.listing("staff")["items"]
        return next(item for item in items if item["id"] == userid)

    def test_the_id_is_the_persons_profile(self):
        """It used to be the listing's own URL with the userid appended, which
        is not a resource: the service takes exactly one path segment."""
        assert self.row()["@id"] == self.alice.absolute_url()

    def test_the_old_id_was_not_a_resource(self):
        """Stated as behaviour rather than as history, so the URL the row no
        longer points at is on record as one that never answered."""
        listing = f"{self.portal.absolute_url()}/@group-members/staff"

        self.listing("staff", "alice")

        assert self.status() == 400
        assert self.row()["@id"] != f"{listing}/alice"

    def test_profile_url_is_the_same_url(self):
        """Kept, and deliberately redundant: clients written against the
        broken ``@id`` were told to follow this one instead, and taking it
        away would break them a second time."""
        row = self.row()

        assert row["profile_url"] == row["@id"]


class TestTheRowIsAnAdapter(GroupMembersCase):
    """A deployment can add a field to a membership row.

    Which is the whole point of the indirection: before this, one more field
    on a row meant replacing the service.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, acl_users, make_group) -> None:
        self.portal = portal
        self.request = request_
        self.acl_users = acl_users
        setRoles(portal, TEST_USER_ID, ["Manager"])
        login(portal, TEST_USER_NAME)
        make_group("staff", title="Staff")
        self.member("alice", "staff", fullname="Alice Liddell")

    def test_the_package_registers_one(self):
        """Without a registration the service raises rather than answering,
        so this is the premise the rest of the endpoint rests on."""
        serializer = getMultiAdapter(
            (self.portal, self.request), IGroupMemberSerializer
        )

        assert isinstance(serializer, GroupMemberSerializer)

    def test_a_subclass_can_add_a_field(self):
        """The documented way to extend a row: subclass, call up, add keys,
        register for your own layer."""

        class WithBadge(GroupMemberSerializer):
            def __call__(self, brain):
                row = super().__call__(brain)
                row["badge"] = "gold"
                return row

        registry = getGlobalSiteManager()
        registry.registerAdapter(
            WithBadge, (ISiteRoot, IBrowserLayer), IGroupMemberSerializer
        )
        try:
            row = self.listing("staff")["items"][0]
        finally:
            registry.unregisterAdapter(
                WithBadge, (ISiteRoot, IBrowserLayer), IGroupMemberSerializer
            )
            registry.registerAdapter(
                GroupMemberSerializer,
                (ISiteRoot, IBrowserLayer),
                IGroupMemberSerializer,
            )

        assert row["badge"] == "gold"
        # The base row is still there: an override extends rather than
        # replaces, which is what makes `@id` safe to change downstream.
        assert row["id"] == "alice"
        assert row["@id"].endswith("/identity-profiles/alice")

    def test_the_override_is_gone_again(self):
        """The fixture above restores the package's own registration. Without
        this, a later test would pass or fail depending on ordering."""
        row = self.listing("staff")["items"][0]

        assert "badge" not in row


class TestDirect(GroupMembersCase):
    """``direct=1``: the members somebody managing the group can remove."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, acl_users, make_group) -> None:
        self.portal = portal
        self.request = request_
        self.acl_users = acl_users
        setRoles(portal, TEST_USER_ID, ["Manager"])
        login(portal, TEST_USER_NAME)
        self.staff = make_group("staff", title="Staff")
        make_group("developers", title="Developers")
        make_group("contractors", title="Contractors")
        self.nest("developers", "staff")
        self.nest("contractors", "staff")
        self.member("alice", "developers", fullname="Alice Liddell")
        self.member("bob", "staff", fullname="Bob Cratchit")

    def ids(self, **form) -> list[str]:
        """Return the ids of a direct listing of staff, in order.

        :param form: More query-string parameters.
        :returns: Row ids.
        """
        return [i["id"] for i in self.listing("staff", direct="1", **form)["items"]]

    def test_lists_nested_groups_then_people(self):
        """Groups first, by title; then the people in the group itself."""
        assert self.ids() == ["contractors", "developers", "bob"]

    def test_leaves_out_people_who_arrive_through_a_nested_group(self):
        """Alice is removed from developers, not from staff."""
        assert "alice" not in self.ids()

    def test_without_the_flag_people_only(self):
        """The group page lists people; nested groups have their own list."""
        ids = [i["id"] for i in self.listing("staff")["items"]]

        assert ids == ["alice", "bob"]

    @pytest.mark.parametrize("flag", ["0", "", "no"])
    def test_anything_else_is_not_the_flag(self, flag: str):
        ids = [i["id"] for i in self.listing("staff", direct=flag)["items"]]

        assert ids == ["alice", "bob"]

    def test_every_row_says_what_it_is(self):
        rows = self.listing("staff", direct="1")["items"]

        assert [r["type"] for r in rows] == ["group", "group", "user"]

    def test_a_group_row_names_and_links_the_group(self):
        row = self.listing("staff", direct="1")["items"][1]

        assert row["id"] == "developers"
        assert row["fullname"] == "Developers"
        assert row["login"] is None
        assert row["profile_url"].endswith("/identity-profiles/developers")

    def test_the_search_narrows_groups_and_people(self):
        assert self.ids(query="dev") == ["developers"]
        assert self.ids(query="cratchit") == ["bob"]

    def test_a_group_filed_inside_is_not_a_removable_member(self, make_group):
        """Containment nests it too, but only moving it undoes that."""
        make_group("interns", title="Interns", container=self.staff)

        assert "interns" not in self.ids()

    def test_it_is_batched(self):
        for index in range(12):
            self.member(f"member-{index:02d}", "staff")

        result = self.listing("staff", direct="1", b_size="10")

        assert result["items_total"] == 15
        assert len(result["items"]) == 10
        assert "batching" in result

    def test_the_totals_do_not_change(self):
        """The summary is the group's, whatever the listing shows."""
        result = self.listing("staff", direct="1")

        assert (result["members_total"], result["direct_members_total"]) == (2, 1)


class TestCanManage(GroupMembersCase):
    """Whether plone.restapi's ``PATCH @groups/<id>`` would take a change."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, acl_users, make_group) -> None:
        self.portal = portal
        self.request = request_
        self.acl_users = acl_users
        login(portal, TEST_USER_NAME)
        make_group("staff", title="Staff")
        make_group("admins", title="Admins")
        api.group.grant_roles(groupname="admins", roles=["Manager"])
        self.member("alice", "staff", fullname="Alice Liddell")

    def can_manage(self, group_id: str, *roles: str) -> bool:
        """Read ``can_manage`` with the test user holding some roles.

        :param group_id: The group to read.
        :param roles: The test user's roles.
        :returns: The flag.
        """
        setRoles(self.portal, TEST_USER_ID, list(roles))
        return self.listing(group_id)["can_manage"]

    def test_a_manager_may(self):
        assert self.can_manage("staff", "Manager") is True

    def test_a_site_administrator_may(self):
        assert self.can_manage("staff", "Site Administrator") is True

    def test_a_manager_may_change_a_manager_group(self):
        assert self.can_manage("admins", "Manager") is True

    def test_a_site_administrator_may_not_change_a_manager_group(self):
        """Adding somebody to it would be granting them Manager, which
        plone.restapi refuses a Site Administrator."""
        assert self.can_manage("admins", "Site Administrator") is False

    def test_a_member_reading_their_own_group_may_not(self):
        """Being able to read a group is not being able to change it."""
        setRoles(self.portal, TEST_USER_ID, ["Member"])
        login(self.portal, "alice")

        assert self.listing("staff")["can_manage"] is False
