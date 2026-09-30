"""The behaviors that make a site's own type a user or a group.

``pas.plugins.identity.principal_user`` and ``principal_group`` exist so a
site does not have to write the marker itself -- and so it does not write it
the obvious way, which breaks its objects. The obvious way is one interface
extending both markers, registered as the behavior's ``provides``.
``IUserContent`` declares ``login`` as an ``Attribute``, and Dexterity, looking
for a missing attribute's default, walks each behavior's ``provides`` in turn:
it finds the ``Attribute`` first, reads ``.default`` off it, and dies there
instead of reaching the real ``login`` field a later behavior supplies.
``TestTheObviousSpellingBreaks`` pins that failure, so the reason for the
factory stays demonstrable rather than asserted.
"""

from ..pas.stubs import add_type
from ..pas.stubs import IStubDocumentSchema
from pas.plugins.identity.core.behaviors.principal import IPrincipalGroup
from pas.plugins.identity.core.behaviors.principal import IPrincipalGroupBehavior
from pas.plugins.identity.core.behaviors.principal import IPrincipalUser
from pas.plugins.identity.core.behaviors.principal import IPrincipalUserBehavior
from pas.plugins.identity.core.interfaces import IGroupContent
from pas.plugins.identity.core.interfaces import IUserContent
from pas.plugins.identity.core.interfaces import IUserGroup
from pas.plugins.identity.core.interfaces import IUserProfile
from pas.plugins.identity.core.principal_types import type_provides
from plone import api
from plone.behavior.interfaces import IBehavior
from plone.behavior.registration import BehaviorRegistration
from plone.dexterity.schema import SCHEMA_CACHE
from plone.supermodel import model
from zope import schema
from zope.component import getGlobalSiteManager
from zope.component import getUtility

import pytest


USER_BEHAVIOR = "pas.plugins.identity.principal_user"
GROUP_BEHAVIOR = "pas.plugins.identity.principal_group"

#: A behavior supplying a real ``login`` field, with a default to read.
LOGIN_FIELD = "stub.login_field"

#: The obvious spelling, registered for the one test that shows it breaking.
NAIVE = "stub.naive_user"

#: A plain type, with nothing but the behaviors under test.
BEHAVED = "StubPrincipal"


class ILoginField(model.Schema):
    """A behavior that supplies ``login``, as a site's own might."""

    login = schema.TextLine(title="Login", default="not-yet-set")


@pytest.fixture
def stub_behaviors():
    """Register the two stub behaviors, and remove them after.

    :returns: Nothing; the registrations are the point.
    """
    registry = getGlobalSiteManager()
    registrations = {
        LOGIN_FIELD: (ILoginField, None),
        NAIVE: (IPrincipalUser, IPrincipalUser),
    }
    for name, (interface, marker) in registrations.items():
        registry.registerUtility(
            BehaviorRegistration(
                title=name,
                description="",
                interface=interface,
                marker=marker,
                factory=None,
                name=name,
            ),
            IBehavior,
            name=name,
        )
    yield
    for name in registrations:
        registry.unregisterUtility(provided=IBehavior, name=name)


@pytest.fixture
def behaved(portal, stub_behaviors):
    """Return a callable adding a plain type with some behaviors enabled.

    :param portal: The Plone site.
    :param stub_behaviors: Registers the stub behaviors.
    :returns: Callable taking behavior names, answering the portal type.
    """

    def factory(*names: str) -> str:
        add_type(
            portal, BEHAVED, f"{IStubDocumentSchema.__module__}.IStubDocumentSchema"
        )
        portal.portal_types[BEHAVED].behaviors = names
        SCHEMA_CACHE.invalidate(BEHAVED)
        return BEHAVED

    yield factory
    SCHEMA_CACHE.clear()


def create(portal, portal_type: str):
    """Create an object as an add form would: no userid and no login.

    :param portal: The Plone site.
    :param portal_type: The type to create.
    :returns: The object.
    """
    return api.content.create(container=portal, type=portal_type, id="someone")


class TestRegistration:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    @pytest.mark.parametrize(
        "name,marker",
        [(USER_BEHAVIOR, IPrincipalUser), (GROUP_BEHAVIOR, IPrincipalGroup)],
    )
    def test_the_behavior_applies_its_marker(self, name, marker):
        assert getUtility(IBehavior, name=name).marker is marker

    @pytest.mark.parametrize("name", [USER_BEHAVIOR, GROUP_BEHAVIOR])
    def test_what_it_provides_declares_nothing(self, name):
        """Nothing here for Dexterity to take a default from."""
        assert list(getUtility(IBehavior, name=name).interface) == []


class TestAUserType:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, behaved) -> None:
        self.portal = portal
        self.portal_type = behaved(USER_BEHAVIOR)

    @pytest.mark.parametrize("marker", [IUserContent, IUserProfile])
    def test_the_type_is_known_to_provide(self, marker):
        """Asked of the FTI, as the adder and a login ask it."""
        assert type_provides(self.portal_type, marker)

    @pytest.mark.parametrize("marker", [IUserContent, IUserProfile])
    def test_its_objects_provide(self, marker):
        assert marker.providedBy(create(self.portal, self.portal_type))

    def test_it_is_not_a_group(self):
        assert not type_provides(self.portal_type, IGroupContent)

    def test_the_behavior_adapts(self):
        """The factory exists for ``plone.behavior``, which wants one beside
        a separate marker, and adapting through it has to work."""
        obj = create(self.portal, self.portal_type)

        assert IPrincipalUserBehavior(obj).context is obj


class TestAGroupType:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, behaved) -> None:
        self.portal = portal
        self.portal_type = behaved(GROUP_BEHAVIOR)

    @pytest.mark.parametrize("marker", [IGroupContent, IUserGroup])
    def test_the_type_is_known_to_provide(self, marker):
        assert type_provides(self.portal_type, marker)

    @pytest.mark.parametrize("marker", [IGroupContent, IUserGroup])
    def test_its_objects_provide(self, marker):
        assert marker.providedBy(create(self.portal, self.portal_type))

    def test_it_is_not_a_user(self):
        assert not type_provides(self.portal_type, IUserContent)

    def test_the_behavior_adapts(self):
        obj = create(self.portal, self.portal_type)

        assert IPrincipalGroupBehavior(obj).context is obj


class TestALaterBehaviorsField:
    """The contract the factory exists for."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, behaved) -> None:
        self.portal = portal
        self.behaved = behaved

    def test_its_default_is_answered(self):
        obj = create(self.portal, self.behaved(USER_BEHAVIOR, LOGIN_FIELD))

        assert obj.login == "not-yet-set"


class TestTheObviousSpellingBreaks:
    """The same type, marked the obvious way."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, behaved) -> None:
        self.portal = portal
        self.behaved = behaved

    def test_the_later_field_is_never_reached(self):
        obj = create(self.portal, self.behaved(NAIVE, LOGIN_FIELD))

        with pytest.raises(AttributeError):
            _ = obj.login
