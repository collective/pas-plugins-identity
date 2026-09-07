"""The personal fields are a behavior, and they stay on the default tab.

The counterpart to ``test_email_behavior``: the same move, and deliberately
*not* the same fieldset. ``home_page``, ``location`` and ``image`` belong
beside the login and the full name, because a person opening their own profile
expects the ordinary form in one place. Only the addresses earn a tab, and only
because they carry a different read permission.

A behavior with no fieldset directive is easy to give one by accident, and the
result is a form that looks reorganized to everybody who had learnt it. Hence
``TestItHasNoFieldsetOfItsOwn``.
"""

from pas.plugins.identity.core.behaviors.details import IProfileDetails
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from plone import api
from plone.autoform.interfaces import IFormFieldProvider
from plone.autoform.interfaces import READ_PERMISSIONS_KEY
from plone.autoform.interfaces import WRITE_PERMISSIONS_KEY
from plone.behavior.interfaces import IBehavior
from plone.supermodel.interfaces import FIELDSETS_KEY
from zope.component import getUtility

import pytest


#: What the behavior is registered as.
NAME = "pas.plugins.identity.profile_details"

#: The fields that moved.
FIELDS = ("home_page", "location", "image")


class TestTheBehaviorIsRegistered:
    def test_it_is_a_behavior(self):
        assert getUtility(IBehavior, name=NAME).interface is IProfileDetails

    def test_it_is_a_form_field_provider(self):
        """Without this the fields store and index correctly and appear on no
        form."""
        assert IFormFieldProvider.providedBy(IProfileDetails)

    def test_the_profile_enables_it(self, portal):
        fti = api.portal.get_tool("portal_types")[PROFILE_PORTAL_TYPE]

        assert NAME in fti.behaviors


class TestTheFieldsMoved:
    @pytest.mark.parametrize("name", FIELDS)
    def test_it_is_no_longer_on_the_type(self, name: str):
        from pas.plugins.identity.core.contents.profile import IUserProfileSchema

        assert name not in IUserProfileSchema.names()

    @pytest.mark.parametrize("name", FIELDS)
    def test_it_is_on_the_behavior(self, name: str):
        assert name in IProfileDetails.names()


class TestItHasNoFieldsetOfItsOwn:
    def test_the_fields_stay_on_the_default_tab(self):
        """A fieldset here would move three fields off the form everybody
        already knows, which is a change nobody asked for and nothing would
        report."""
        assert not (IProfileDetails.queryTaggedValue(FIELDSETS_KEY) or [])


class TestThePermissionsCameWithThem:
    @pytest.mark.parametrize("name", FIELDS)
    def test_writing_still_needs_the_edit_permission(self, name: str):
        permissions = IProfileDetails.queryTaggedValue(WRITE_PERMISSIONS_KEY)

        assert permissions[name] == "pas.plugins.identity.content.edit"

    @pytest.mark.parametrize("name", FIELDS)
    def test_reading_still_needs_the_view_permission(self, name: str):
        """The ordinary one, not ``viewpii``: a home page is not an address."""
        permissions = IProfileDetails.queryTaggedValue(READ_PERMISSIONS_KEY)

        assert permissions[name] == "pas.plugins.identity.content.view"


class TestTheStorageDidNotMove:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.profile = api.content.create(
            container=portal["identity-profiles"],
            type=PROFILE_PORTAL_TYPE,
            id="dana",
            userid="dana",
            login="dana",
            emails=("dana@example.com",),
            home_page="https://example.com/dana",
            location="Berlin",
        )

    def test_the_values_are_on_the_object(self):
        assert self.profile.home_page == "https://example.com/dana"
        assert self.profile.location == "Berlin"

    def test_they_are_still_catalog_metadata(self):
        """``home_page`` and ``location`` are member properties served from a
        brain, which is the whole reason this package has a catalog."""
        from pas.plugins.identity.core.catalog import get_catalog

        brain = get_catalog()(userid="dana")[0]

        assert brain.home_page == "https://example.com/dana"
        assert brain.location == "Berlin"
