"""``group_ids`` is a behavior now, and both principal types carry it.

The move is what lets a group be nested the same way a user is a member, and
what lets a site's own user type get membership without redeclaring the field,
its vocabulary and its two permissions.
"""

from pas.plugins.identity.core.behaviors.membership import FIELDSET
from pas.plugins.identity.core.behaviors.membership import IGroupMembership
from pas.plugins.identity.core.catalog import GROUP_PORTAL_TYPE
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.contents.profile import IUserProfileSchema
from plone import api
from plone.behavior.interfaces import IBehavior
from zope.component import queryUtility

import pytest


#: The name the behavior is registered under.
BEHAVIOR = "pas.plugins.identity.group_membership"


class TestRegistration:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.types = api.portal.get_tool("portal_types")

    def test_the_behavior_is_registered(self):
        """Without this the FTIs below name something that does not exist."""
        assert queryUtility(IBehavior, name=BEHAVIOR) is not None

    @pytest.mark.parametrize("portal_type", [PROFILE_PORTAL_TYPE, GROUP_PORTAL_TYPE])
    def test_both_types_enable_it(self, portal_type):
        """One field, two types: a user's memberships and a group's nesting
        are the same fact stored on the same side."""
        assert BEHAVIOR in self.types[portal_type].behaviors

    def test_the_profile_schema_no_longer_declares_it(self):
        """Declaring it in both places would be two fields to keep in step,
        and the type's own schema wins the default lookup."""
        assert "group_ids" not in IUserProfileSchema.names()

    def test_the_field_is_in_its_own_fieldset(self):
        """So membership is a tab of its own on the edit form -- it is the
        one field carrying a different write permission."""
        from plone.supermodel.interfaces import FIELDSETS_KEY

        fieldsets = IGroupMembership.queryTaggedValue(FIELDSETS_KEY)

        assert [f.__name__ for f in fieldsets] == [FIELDSET]


class TestStorage:
    """A schema-only behavior stores on the object, which is what keeps the
    catalog and every existing reader working unchanged."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, make_group) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.make_group = make_group
        self.container = portal["identity-profiles"]

    def test_a_profile_defaults_to_no_groups(self):
        """Read straight off the object, and never an AttributeError: the
        marker interface deliberately does not declare ``group_ids`` as an
        Attribute, because that shadows the behavior's field and breaks the
        default lookup."""
        self.acl_users.source_users.addUser("alice", "alice", "placeholder")
        profile = api.content.create(
            container=self.container,
            type=PROFILE_PORTAL_TYPE,
            id="alice",
            login="alice@example.com",
        )

        assert profile.group_ids == ()

    def test_a_group_defaults_to_no_nesting(self):
        """The same guarantee on the other type."""
        assert self.make_group("staff").group_ids == ()

    def test_a_profile_still_stores_it_on_the_object(self):
        """Not in an annotation and not on an adapter: the catalog indexes
        this field, and a brain reads attributes."""
        self.acl_users.source_users.addUser("alice", "alice", "placeholder")
        profile = api.content.create(
            container=self.container,
            type=PROFILE_PORTAL_TYPE,
            id="alice",
            login="alice@example.com",
            group_ids=("staff",),
        )

        assert profile.__dict__["group_ids"] == ("staff",)

    def test_a_group_stores_it_too(self):
        """Which is what makes nesting a stored edge rather than a new kind
        of relation."""
        group = self.make_group("developers", group_ids=("staff",))

        assert group.__dict__["group_ids"] == ("staff",)
