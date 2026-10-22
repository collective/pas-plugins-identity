"""A Profile's REST payload, as read by viewers who hold different permissions.

``login`` and ``group_ids`` are account data: the login is what signs the
account in, and the groups decide the roles it holds. ``View Profile`` guards
the public fields, so a site that shows a Profile to Anonymous would otherwise
show the login as well. plone.restapi checks each field's read permission
while it serializes, and these tests read the payload the way ``@content``
does.
"""

from AccessControl import getSecurityManager
from plone import api
from plone.app.testing import logout
from plone.restapi.interfaces import ISerializeToJson
from zope.component import getMultiAdapter

import pytest


VIEW = "pas.plugins.identity: View Profile"
VIEW_ACCOUNT = "pas.plugins.identity: View Account Details"


def _serialize(profile, request) -> dict:
    """Return the JSON a Profile is served as.

    :param profile: The Profile to serialize.
    :param request: The request the serializer is bound to.
    :returns: The payload.
    """
    return getMultiAdapter((profile, request), ISerializeToJson)()


class TestAnonymousWithViewProfileOnly:
    """A site that opens the public fields of a Profile to Anonymous and
    nothing else."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_profile, request_) -> None:
        self.request = request_
        self.profile = make_profile(
            "alice",
            fullname="Alice Liddell",
            description="Curious about the other side.",
        )
        self.profile.manage_permission(
            VIEW,
            roles=["Anonymous", "Manager", "Site Administrator", "Owner"],
            acquire=0,
        )
        self.profile.manage_permission(
            VIEW_ACCOUNT,
            roles=["Manager", "Site Administrator", "Owner"],
            acquire=0,
        )
        logout()

    def test_premise_anonymous_holds_view_profile_only(self):
        """If Anonymous did not hold the public permission the tests below
        would pass without the split."""
        assert getSecurityManager().checkPermission(VIEW, self.profile)
        assert not getSecurityManager().checkPermission(VIEW_ACCOUNT, self.profile)

    def test_the_public_fields_are_served(self):
        """What the split is for: the name and the biography stay public."""
        data = _serialize(self.profile, self.request)

        assert data["fullname"] == "Alice Liddell"
        assert data["description"] == "Curious about the other side."

    def test_the_login_is_not_served(self):
        """The field that signs the account in."""
        data = _serialize(self.profile, self.request)

        assert "login" not in data

    def test_the_groups_are_not_served(self):
        """The field that decides which roles the account holds."""
        data = _serialize(self.profile, self.request)

        assert "group_ids" not in data


class TestOwnerAndManagerStillSeeAccountDetails:
    """The split takes nothing from the people who manage the account."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, make_profile, request_) -> None:
        self.request = request_
        acl_users.source_users.addUser("alice", "alice", "placeholder-password")
        api.user.grant_roles(username="alice", roles=["Member"])
        api.user.create(
            email="root@example.com",
            username="root",
            password="root-placeholder-password",
            roles=("Manager",),
        )
        self.profile = make_profile("alice", fullname="Alice Liddell")

    def test_the_owner_sees_the_login(self):
        """Their own sign-in name, from their own Profile."""
        with api.env.adopt_user(username="alice"):
            data = _serialize(self.profile, self.request)

        assert data["login"] == "alice@example.com"

    def test_the_owner_sees_the_groups(self):
        with api.env.adopt_user(username="alice"):
            data = _serialize(self.profile, self.request)

        assert "group_ids" in data

    def test_a_manager_sees_the_login(self):
        with api.env.adopt_user(username="root"):
            data = _serialize(self.profile, self.request)

        assert data["login"] == "alice@example.com"

    def test_a_manager_sees_the_groups(self):
        with api.env.adopt_user(username="root"):
            data = _serialize(self.profile, self.request)

        assert "group_ids" in data
