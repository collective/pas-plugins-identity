"""The authorization server adds Applications to the personal tools.

Before Site Setup, which stays last, and only on a site with this profile:
the page lists the clients a user has authorized, which no other site has.
"""

from . import PROFILE_ID
from plone import api

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


def personal_tools(portal, userid: str) -> list[dict]:
    """List the personal tools a user is offered.

    :param portal: The Plone site.
    :param userid: The user to list them for.
    :returns: The id and URL of each, in menu order, read while acting as
        that user because an ActionInfo evaluates its URL lazily.
    """
    tool = api.portal.get_tool("portal_actions")
    with api.env.adopt_user(username=userid):
        return [
            {"id": info["id"], "url": info["url"]}
            for info in tool.listActionInfos(
                object=portal, categories=["personal_tools"]
            )
        ]


class TestApplications:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users) -> None:
        self.portal = portal
        for userid in ("bob", "boss"):
            acl_users.source_users.addUser(userid, userid, "placeholder-password")
        api.user.grant_roles(username="boss", roles=["Manager"])

    def test_a_member_is_offered_it(self):
        actions = personal_tools(self.portal, "bob")
        assert {"id": "applications", "url": "/applications"} in actions

    def test_it_comes_before_site_setup(self):
        ids = [action["id"] for action in personal_tools(self.portal, "boss")]
        assert ids[-2:] == ["applications", "plone_setup"]
