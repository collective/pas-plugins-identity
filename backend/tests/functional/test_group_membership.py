"""A user cannot put themselves in a group by editing their own profile.

The integration tests next door assert that the owner of a profile does not
hold ``Edit Profile Group Membership``. That is true whatever ``group_ids`` is
declared with, so it passes with the field still pointing at the ordinary edit
permission -- which is the bug. Only an actual write answers the real
question.

So this drives ``PATCH @users``-style traffic the way Volto does: a real
request, as the user, against the field. If the binding is wrong the write
succeeds and alice is in a group she granted herself.

The second half is the legitimate way in: the requests a group's members page
sends, as somebody allowed to send them.
"""

from pas.plugins.identity.core.catalog import GROUP_PORTAL_TYPE
from pas.plugins.identity.core.container import get_container
from plone import api
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD

import pytest
import requests
import transaction


USERID = "alice"
PASSWORD = "alice-secret-1"

JSON = {"Accept": "application/json", "Content-Type": "application/json"}


@pytest.fixture
def site(functional):
    """A site with a user, a profile, and a group to covet.

    :param functional: The functional layer.
    :returns: ``(portal, url)``.
    """
    portal = functional["portal"]
    with api.env.adopt_roles(["Manager"]):
        container = get_container(create=True)
        api.content.create(
            container=container,
            type=GROUP_PORTAL_TYPE,
            id="site-editors",
            group_id="site-editors",
            title="Site Editors",
        )
        api.user.create(
            username=USERID,
            email="alice@example.com",
            password=PASSWORD,
            properties={"fullname": "Alice Liddell"},
        )
    transaction.commit()
    return portal, portal.absolute_url()


def patch(url: str, auth, payload: dict) -> requests.Response:
    """PATCH a profile.

    :param url: The profile URL.
    :param auth: Credentials.
    :param payload: The JSON body.
    :returns: The response.
    """
    return requests.patch(url, json=payload, headers=JSON, auth=auth, timeout=30)


class TestWritingYourOwnGroups:
    @pytest.fixture(autouse=True)
    def _setup(self, site) -> None:
        self.portal, self.url = site
        self.user = (USERID, PASSWORD)
        self.profile_url = f"{self.url}/identity-profiles/{USERID}"

    def groups(self) -> tuple:
        """Return the group ids currently on alice's profile.

        Read from the object rather than from the response, because the
        question is what was *stored*.

        :returns: The stored value.
        """
        self.portal._p_jar.sync()
        return tuple(self.portal["identity-profiles"][USERID].group_ids or ())

    def test_she_starts_in_no_group(self):
        """The premise. Without it the assertion below is vacuous."""
        assert self.groups() == ()

    def test_she_cannot_add_herself_to_one(self):
        """The bug, in the form Érico found it: her own edit form offered the
        field, and the field granted roles."""
        patch(self.profile_url, self.user, {"group_ids": ["site-editors"]})

        assert self.groups() == ()

    def test_she_cannot_add_herself_through_groups_either(self):
        """The other way in, which asks for a site-wide permission."""
        response = patch(
            f"{self.url}/@groups/site-editors", self.user, {"users": {USERID: True}}
        )

        assert response.status_code == 401
        assert self.groups() == ()

    def test_she_can_still_edit_her_own_name(self):
        """The control. A fix that took self-service with it would pass the
        test above and fail this one."""
        response = patch(self.profile_url, self.user, {"fullname": "Alice L."})

        assert response.status_code in (200, 204)
        self.portal._p_jar.sync()
        assert self.portal["identity-profiles"][USERID].fullname == "Alice L."


class TestChangingMembersThroughGroups:
    """plone.restapi's ``PATCH @groups/<id>`` is how a group's members change.

    The members page sends it and nothing else, so it has to reach the field
    this package stores membership in -- for a person and for a nested group.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, site) -> None:
        self.portal, self.url = site
        self.owner = (SITE_OWNER_NAME, SITE_OWNER_PASSWORD)
        with api.env.adopt_roles(["Manager"]):
            api.content.create(
                container=self.portal["identity-profiles"],
                type=GROUP_PORTAL_TYPE,
                id="developers",
                group_id="developers",
                title="Developers",
            )
        transaction.commit()

    def stored(self, principal: str) -> tuple:
        """Return the group ids stored on a principal's content object.

        :param principal: A userid or a group id.
        :returns: The stored value.
        """
        self.portal._p_jar.sync()
        return tuple(self.portal["identity-profiles"][principal].group_ids or ())

    def change(self, members: dict) -> requests.Response:
        """Change the members of site-editors as the site owner.

        :param members: The ``users`` map: id to add (``True``) or remove.
        :returns: The response.
        """
        return patch(f"{self.url}/@groups/site-editors", self.owner, {"users": members})

    def test_a_person_is_added(self):
        response = self.change({USERID: True})

        assert response.status_code == 204
        assert self.stored(USERID) == ("site-editors",)

    def test_a_group_is_nested(self):
        self.change({"developers": True})

        assert self.stored("developers") == ("site-editors",)

    def test_several_are_added_at_once(self):
        self.change({USERID: True, "developers": True})

        assert (self.stored(USERID), self.stored("developers")) == (
            ("site-editors",),
            ("site-editors",),
        )

    def test_a_person_is_removed(self):
        self.change({USERID: True})

        self.change({USERID: False})

        assert self.stored(USERID) == ()

    def test_a_group_is_not_removed_through_groups(self):
        """plone.restapi removes only what ``getGroupMemberIds`` lists, and
        that is userids: a nested group is not among them, by design. The
        members page therefore un-nests a group the other way, below."""
        self.change({"developers": True})

        self.change({"developers": False})

        assert self.stored("developers") == ("site-editors",)

    def test_a_group_is_removed_through_its_own_field(self):
        """What the members page sends to un-nest a group: the nested group's
        own ``group_ids``, without this one."""
        self.change({"developers": True})

        response = patch(
            f"{self.url}/identity-profiles/developers",
            self.owner,
            {"group_ids": []},
        )

        assert response.status_code == 204
        assert self.stored("developers") == ()
