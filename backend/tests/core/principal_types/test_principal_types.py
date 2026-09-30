"""Which types a site keeps its users and groups in, and what those types are.

Every path that creates, finds or walks principals asks
:mod:`~pas.plugins.identity.core.principal_types` rather than naming
``UserProfile`` or ``UserGroup`` itself. These tests pin the two halves of
that: the readers, which answer the site's record and fall back to this
package's own type; and :func:`type_provides`, which has to recognise a
marker whichever of Dexterity's routes brought it -- because a site bringing
its own type is most likely to use a behavior, the one route ``UserProfile``
does not.
"""

from ..pas.stubs import add_type
from ..pas.stubs import IStubDocumentSchema
from pas.plugins.identity.core.interfaces import IUserContent
from pas.plugins.identity.core.interfaces import IUserProfile
from pas.plugins.identity.core.principal_types import catalogued_types
from pas.plugins.identity.core.principal_types import GROUP_CONTENT_TYPE_RECORD
from pas.plugins.identity.core.principal_types import group_portal_type
from pas.plugins.identity.core.principal_types import type_provides
from pas.plugins.identity.core.principal_types import USER_CONTENT_TYPE_RECORD
from pas.plugins.identity.core.principal_types import user_portal_type
from plone import api
from plone.behavior.interfaces import IBehavior
from plone.behavior.registration import BehaviorRegistration
from plone.dexterity.schema import SCHEMA_CACHE
from plone.registry.interfaces import IRegistry
from zope.component import getGlobalSiteManager
from zope.component import getUtility
from zope.interface import Interface

import pytest


class IStubUserBehavior(IUserContent):
    """A behavior schema that makes a type a user."""


class IStubPlainBehavior(Interface):
    """A behavior schema that says nothing about users."""


class IStubUserMarker(IUserContent):
    """A behavior marker that makes a type a user."""


#: Portal type the behavior tests enable their behavior on.
BEHAVED = "StubBehaved"


@pytest.fixture
def behavior():
    """Return a callable registering a behavior, and remove them all after.

    Registered globally, the way ZCML would, and unregistered so no other test
    sees a behavior it did not ask for. The schema cache is cleared on the way
    out as well: it memoizes behavior registrations per portal type.

    :returns: Callable taking a behavior name, its schema and its marker.
    """
    registry = getGlobalSiteManager()
    names: list[str] = []

    def register(name: str, interface, marker=None) -> None:
        registration = BehaviorRegistration(
            title=name,
            description="",
            interface=interface,
            marker=marker,
            factory=None,
            name=name,
        )
        registry.registerUtility(registration, IBehavior, name=name)
        names.append(name)

    yield register
    for name in names:
        registry.unregisterUtility(provided=IBehavior, name=name)
    SCHEMA_CACHE.clear()


@pytest.fixture
def behaved(portal):
    """Return a callable adding a plain type with some behaviors enabled.

    :param portal: The Plone site.
    :returns: Callable taking behavior names, answering the portal type.
    """

    def factory(*names: str) -> str:
        add_type(
            portal, BEHAVED, f"{IStubDocumentSchema.__module__}.IStubDocumentSchema"
        )
        portal.portal_types[BEHAVED].behaviors = names
        SCHEMA_CACHE.invalidate(BEHAVED)
        return BEHAVED

    return factory


class TestTheReaders:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_install_names_the_profile(self):
        assert user_portal_type() == "UserProfile"

    def test_install_names_the_group(self):
        assert group_portal_type() == "UserGroup"

    def test_a_site_type_is_answered(self):
        api.portal.set_registry_record(USER_CONTENT_TYPE_RECORD, "Person")
        api.portal.set_registry_record(GROUP_CONTENT_TYPE_RECORD, "Team")

        assert (user_portal_type(), group_portal_type()) == ("Person", "Team")

    def test_whitespace_is_not_part_of_the_name(self):
        api.portal.set_registry_record(USER_CONTENT_TYPE_RECORD, "  Person ")

        assert user_portal_type() == "Person"

    @pytest.mark.parametrize("blank", ["", "   ", None])
    def test_a_blank_record_reads_as_our_own_type(self, blank):
        """``None`` is what an empty ``<value>`` in a policy profile's
        ``registry.xml`` imports as -- the way a site says "no group type".
        Written through the registry, as the import does: ``plone.api``
        refuses ``None`` as a value."""
        getUtility(IRegistry)[GROUP_CONTENT_TYPE_RECORD] = blank

        assert group_portal_type() == "UserGroup"

    def test_a_missing_record_reads_as_our_own_type(self):
        """A site mid-install, or one this add-on was removed from."""
        del getUtility(IRegistry).records[USER_CONTENT_TYPE_RECORD]

        assert user_portal_type() == "UserProfile"

    def test_the_catalogued_types_follow_the_records(self):
        api.portal.set_registry_record(USER_CONTENT_TYPE_RECORD, "Person")

        assert catalogued_types() == ("Person", "UserGroup")


class TestTypeProvides:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, behavior, behaved) -> None:
        self.portal = portal
        self.behavior = behavior
        self.behaved = behaved

    def test_through_the_type_schema(self):
        """``UserProfile``'s own route: its schema extends the marker."""
        assert type_provides("UserProfile", IUserContent)

    def test_through_the_content_class(self):
        """``IUserProfile`` reaches ``UserProfile`` through
        ``<class><implements>``, not through its schema."""
        schema = self.portal.portal_types.UserProfile.lookupSchema()
        assert not schema.isOrExtends(IUserProfile)

        assert type_provides("UserProfile", IUserProfile)

    def test_through_a_behavior_schema(self):
        self.behavior("stub.user_schema", IStubUserBehavior)

        assert type_provides(self.behaved("stub.user_schema"), IUserContent)

    def test_through_a_behavior_marker(self):
        """The route the issue was about: a schema that says nothing, and a
        marker that makes the type a user."""
        self.behavior("stub.user_marker", IStubPlainBehavior, IStubUserMarker)

        assert type_provides(self.behaved("stub.user_marker"), IUserContent)

    def test_an_unrelated_behavior_is_not_enough(self):
        self.behavior("stub.plain", IStubPlainBehavior)

        assert not type_provides(self.behaved("stub.plain"), IUserContent)

    def test_a_type_that_does_not_exist(self):
        assert not type_provides("NoSuchType", IUserContent)

    def test_a_type_that_is_not_dexterity(self):
        assert not type_provides("Plone Site", IUserContent)

    def test_a_class_that_will_not_load(self):
        """A broken FTI must not break adding a user, a group or a login."""
        portal_type = self.behaved()
        self.portal.portal_types[portal_type].klass = "no.such.module.Klass"

        assert not type_provides(portal_type, IUserContent)
