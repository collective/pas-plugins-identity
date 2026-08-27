"""A user cannot put themselves in a group by editing their own profile.

The integration tests next door assert that the owner of a profile does not
hold ``Edit Profile Group Membership``. That is true whatever ``group_ids`` is
declared with, so it passes with the field still pointing at the ordinary edit
permission -- which is the bug. Only an actual write answers the real
question.

So this drives ``PATCH @users``-style traffic the way Volto does: a real
request, as the user, against the field. If the binding is wrong the write
succeeds and alice is in a group she granted herself.
"""

from pas.plugins.identity import PACKAGE_NAME
from pas.plugins.identity.content.catalog import GROUP_PORTAL_TYPE
from pas.plugins.identity.content.container import get_container
from plone import api
from plone.app.testing import applyProfile

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
    applyProfile(portal, f"{PACKAGE_NAME}.content:default")
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

    def test_she_can_still_edit_her_own_name(self):
        """The control. A fix that took self-service with it would pass the
        test above and fail this one."""
        response = patch(self.profile_url, self.user, {"fullname": "Alice L."})

        assert response.status_code in (200, 204)
        self.portal._p_jar.sync()
        assert self.portal["identity-profiles"][USERID].fullname == "Alice L."
