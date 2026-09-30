"""A site that keeps its users as a content type of its own.

The records have always said a site may substitute its own user type, and
until #127 only the user adder listened. Everything else named ``UserProfile``
outright: a login created a ``UserProfile`` beside the site's own object, the
Profile plugin searched the catalog for ``UserProfile`` and nothing else, and
the rebuild, the export and the consistency check all walked a type the site
did not use.

The type here is built the way the how-to builds it, and the way this
package's own ``UserProfile`` is *not*: a plain schema, with
``pas.plugins.identity.principal_user`` making it a user (``IUserContent``)
and a Profile the layer can catalogue (``IUserProfile``). The other shipped
behaviors supply the fields the catalog reads. It mirrors
``docs/docs/how-to-guides/extend/use-your-own-user-type.md``, in Python rather
than XML. The group side, with ``principal_group``, closes the module.

A type that is a user but not a Profile is the other case, covered in
``tests/core/pas/test_external_user_record.py``: the layer leaves it to
whoever created it rather than making a second record of the same person.
"""

from pas.plugins.identity.core import doctor
from pas.plugins.identity.core.catalog import CATALOG_ID
from pas.plugins.identity.core.catalog import group_brains
from pas.plugins.identity.core.catalog import profile_brains
from pas.plugins.identity.core.completeness import required_fields
from pas.plugins.identity.core.principal_types import GROUP_CONTENT_TYPE_RECORD
from pas.plugins.identity.core.principal_types import USER_CONTENT_TYPE_RECORD
from pas.plugins.identity.core.profiles import ensure_profile
from pas.plugins.identity.core.services.groups import member_brains
from pas.plugins.identity.core.services.myprofile import field_titles
from pas.plugins.identity.exportimport.exporter import export_site
from plone import api
from plone.dexterity.fti import DexterityFTI
from plone.dexterity.schema import SCHEMA_CACHE
from plone.supermodel import model
from zope import schema
from zope.lifecycleevent import modified

import pytest


#: The site's own user type.
PERSON = "Person"

#: The site's own group type.
TEAM = "Team"

#: The behaviors the how-to enables on the user type: the one that makes it a
#: user, and the three ``UserProfile`` gets the catalog's fields from.
USER_BEHAVIORS = (
    "pas.plugins.identity.principal_user",
    "pas.plugins.identity.profile_details",
    "pas.plugins.identity.email_addresses",
    "pas.plugins.identity.group_membership",
)

#: The same for a group type, which keeps its nesting in ``group_ids``.
GROUP_BEHAVIORS = (
    "pas.plugins.identity.principal_group",
    "pas.plugins.identity.group_membership",
)


class IPersonSchema(model.Schema):
    """The site's own schema, with a field ``UserProfile`` does not have."""

    nickname = schema.TextLine(title="Nickname", required=True)


class ITeamSchema(model.Schema):
    """The site's own group schema, which says nothing about groups."""


def add_principal_type(
    portal, name: str, schema_: type, behaviors: tuple, workflow_of: str
) -> None:
    """Register a site's own principal type, the way the how-to does.

    The FTI with its behaviors, the workflow of the type it replaces, and room
    for it in the principals container.

    :param portal: The Plone site.
    :param name: Portal type id.
    :param schema_: The type's own schema.
    :param behaviors: Behavior names to enable.
    :param workflow_of: The shipped type whose workflow chain to bind.
    """
    fti = DexterityFTI(name)
    fti.klass = "plone.dexterity.content.Container"
    fti.schema = f"{schema_.__module__}.{schema_.__name__}"
    fti.behaviors = behaviors
    fti.global_allow = False
    portal.portal_types._setObject(name, fti)

    workflow = api.portal.get_tool("portal_workflow")
    workflow.setChainForPortalTypes([name], workflow.getChainForPortalType(workflow_of))
    container_fti = portal.portal_types.PrincipalsContainer
    container_fti.allowed_content_types = (*container_fti.allowed_content_types, name)


@pytest.fixture
def person_type(portal):
    """Register the ``Person`` type and make the site keep its users in it.

    :param portal: The Plone site.
    :returns: The Plone site.
    """
    add_principal_type(portal, PERSON, IPersonSchema, USER_BEHAVIORS, "UserProfile")
    api.portal.set_registry_record(USER_CONTENT_TYPE_RECORD, PERSON)
    yield portal
    SCHEMA_CACHE.clear()


@pytest.fixture
def team_type(portal):
    """Register the ``Team`` type and make the site keep its groups in it.

    :param portal: The Plone site.
    :returns: The Plone site.
    """
    add_principal_type(portal, TEAM, ITeamSchema, GROUP_BEHAVIORS, "UserGroup")
    api.portal.set_registry_record(GROUP_CONTENT_TYPE_RECORD, TEAM)
    yield portal
    SCHEMA_CACHE.clear()


def types_in_container(portal) -> set[str]:
    """Return the portal types in the Profile container.

    :param portal: The Plone site.
    :returns: The types found.
    """
    return {obj.portal_type for obj in portal["identity-profiles"].objectValues()}


class TestALoginCreatesThePerson:
    @pytest.fixture(autouse=True)
    def _setup(self, person_type) -> None:
        self.portal = person_type

    def test_the_profile_is_the_sites_type(self):
        profile = ensure_profile("alice", "alice@example.com", {})

        assert profile.portal_type == PERSON

    def test_no_user_profile_is_created_beside_it(self):
        """The bug as reported: every login made a ``UserProfile`` next to
        the site's own object."""
        ensure_profile("alice", "alice@example.com", {})

        assert types_in_container(self.portal) == {PERSON}

    def test_a_second_login_finds_it(self):
        first = ensure_profile("alice", "alice@example.com", {})
        second = ensure_profile("alice", "alice@example.com", {})

        assert first.UID() == second.UID()


class TestTheLayerServesIt:
    """Every read path finds the site's type, and only because it asks.

    The object is created directly rather than through ``ensure_profile``, so
    these assertions cannot pass on a ``UserProfile`` a hardcoded login path
    made instead.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, person_type, catalog, profile_plugin, make_group) -> None:
        self.portal = person_type
        self.catalog = catalog
        self.plugin = profile_plugin
        self.group = make_group("editors")
        self.person = api.content.create(
            container=person_type["identity-profiles"],
            type=PERSON,
            id="alice",
            userid="alice",
            login="alice@example.com",
        )
        self.person.group_ids = ["editors"]
        # The event, not ``reindexObject``: the layer's own subscriber is
        # what files a change in its catalog, and it has to reach this type.
        modified(self.person)

    def test_it_is_catalogued(self):
        assert [brain.userid for brain in profile_brains(self.catalog)] == ["alice"]

    def test_the_plugin_finds_it_by_id(self):
        assert self.plugin._exact_brains(ids=["alice"], logins=[])

    def test_the_plugin_lists_its_group_membership(self):
        assert "alice" in self.plugin.getGroupMembers("editors")

    def test_group_members_lists_it(self):
        assert [b.userid for b in member_brains("editors", self.plugin)] == ["alice"]

    def test_a_rebuild_indexes_it_again(self):
        self.catalog.clearFindAndRebuild()

        assert [brain.userid for brain in profile_brains(self.catalog)] == ["alice"]

    def test_the_export_carries_it(self):
        assert [user["userid"] for user in export_site()["users"]] == ["alice"]

    def test_the_doctor_finds_nothing_wrong(self):
        assert doctor.check() == []

    def test_the_doctor_looks_at_it(self):
        """ "Nothing wrong" is also what a doctor that never looked would
        say, so a drift it can only see by reading this type."""
        self.person.group_ids = ["editors", "reviewers"]

        assert {finding["path"] for finding in doctor.check()} == {
            "/".join(self.person.getPhysicalPath())
        }


class TestItsSchemaIsTheOneRead:
    """Required fields and their titles come from the site's type."""

    @pytest.fixture(autouse=True)
    def _setup(self, person_type) -> None:
        self.portal = person_type
        self.person = ensure_profile("alice", "alice@example.com", {})

    def test_its_required_field_is_required(self):
        assert "nickname" in required_fields(self.person)

    def test_its_field_has_its_title(self):
        assert field_titles(("nickname",)) == {"nickname": "Nickname"}


class TestAddingAUser:
    @pytest.fixture(autouse=True)
    def _setup(self, person_type) -> None:
        self.portal = person_type

    def test_api_user_create_mints_the_person(self):
        """The adder accepts the type because a behavior makes it a user --
        a route the type check used to refuse."""
        api.user.create(email="bob@example.com", username="bob")

        assert self.portal["identity-profiles"]["bob"].portal_type == PERSON

    def test_the_user_can_be_looked_up(self):
        api.user.create(email="bob@example.com", username="bob")

        assert api.user.get(userid="bob") is not None


class TestAddingAGroup:
    """The group side: ``principal_group`` on a type of the site's own."""

    @pytest.fixture(autouse=True)
    def _setup(self, team_type, catalog) -> None:
        self.portal = team_type
        self.catalog = catalog
        api.group.create(groupname="editors", title="Editors")

    def test_api_group_create_mints_the_team(self):
        assert self.portal["identity-profiles"]["editors"].portal_type == TEAM

    def test_it_is_catalogued(self):
        assert [brain.group_id for brain in group_brains(self.catalog)] == ["editors"]

    def test_the_group_can_be_looked_up(self):
        assert api.group.get(groupname="editors") is not None


def test_the_catalog_tool_is_the_one_asked(portal):
    """Guards the fixture rather than the code: the tests above assert on
    this catalog, and would pass vacuously against another."""
    assert api.portal.get_tool(CATALOG_ID).__class__.__name__ == (
        "IdentityProfileCatalog"
    )
