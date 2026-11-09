"""The ``personal_tools`` actions Volto's toolbar builds its user menu from.

Read through ``portal_actions`` as the ``@actions`` service reads them, once
per kind of visitor: each entry carries a condition, and the menu is what the
conditions leave for that visitor.
"""

from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from plone import api
from plone.app.testing import logout

import pytest


CATEGORY = "personal_tools"


@pytest.fixture
def users(portal, acl_users) -> None:
    """Create a member without a Profile, one with, and a manager.

    :param portal: The Plone site.
    :param acl_users: The site's PAS instance.
    """
    for userid in ("bob", "alice", "boss"):
        acl_users.source_users.addUser(userid, userid, "placeholder-password")
    api.user.grant_roles(username="boss", roles=["Manager"])
    api.content.create(
        container=portal["identity-profiles"],
        type=PROFILE_PORTAL_TYPE,
        id="alice",
        userid="alice",
        login="alice@example.com",
    )


def personal_tools(portal, userid: str | None) -> list[dict]:
    """List the personal tools a visitor is offered.

    :param portal: The Plone site.
    :param userid: The user to list them for, or ``None`` for anonymous.
    :returns: The id, URL and icon of each, in menu order.
    """

    def read() -> list[dict]:
        # Read inside, not by the caller: an ActionInfo evaluates its URL
        # lazily, so read after `adopt_user` ends it is the URL of whoever
        # the test runs as.
        tool = api.portal.get_tool("portal_actions")
        return [
            {"id": info["id"], "url": info["url"], "icon": info["icon"]}
            for info in tool.listActionInfos(object=portal, categories=[CATEGORY])
        ]

    if userid is None:
        logout()
        return read()
    with api.env.adopt_user(username=userid):
        return read()


class TestTheMenu:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, users) -> None:
        self.portal = portal

    @pytest.mark.parametrize(
        "userid,expected",
        [
            [None, []],
            ["bob", ["profile", "preferences", "identities"]],
            ["alice", ["identity_profile", "preferences", "identities"]],
            ["boss", ["profile", "preferences", "identities", "plone_setup"]],
        ],
    )
    def test_entries(self, userid: str | None, expected: list):
        actions = personal_tools(self.portal, userid)
        assert [action["id"] for action in actions] == expected

    @pytest.mark.parametrize(
        "action_id,userid,url,icon",
        [
            ["profile", "bob", "/personal-information", "plone-user"],
            ["preferences", "bob", "preferences", "plone-user"],
            ["identities", "bob", "/identities", "plone-login"],
            ["plone_setup", "boss", "/controlpanel", "plone-controlpanel"],
        ],
    )
    def test_entry(self, action_id: str, userid: str, url: str, icon: str):
        actions = {a["id"]: a for a in personal_tools(self.portal, userid)}
        assert actions[action_id]["url"] == url
        assert actions[action_id]["icon"] == icon

    def test_the_profile_entry_leads_to_the_profile(self):
        actions = {a["id"]: a for a in personal_tools(self.portal, "alice")}
        profile = self.portal["identity-profiles"]["alice"]
        assert actions["identity_profile"]["url"] == profile.absolute_url()


class TestTheProfileUrlView:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, users) -> None:
        self.portal = portal

    def _url(self, userid: str | None) -> str:
        """Ask the view as a user.

        :param userid: The user, or ``None`` for anonymous.
        :returns: What the view answers.
        """
        view = api.content.get_view(
            "identity-profile-url", self.portal, self.portal.REQUEST
        )
        if userid is None:
            logout()
            return view()
        with api.env.adopt_user(username=userid):
            return view()

    def test_anonymous_gets_nothing(self):
        assert self._url(None) == ""

    def test_a_user_without_a_profile_gets_nothing(self):
        assert self._url("bob") == ""

    def test_a_user_gets_their_own_profile(self):
        profile = self.portal["identity-profiles"]["alice"]
        assert self._url("alice") == profile.absolute_url()
