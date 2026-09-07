"""The addresses are a behavior, on their own tab.

Moving a field to a behavior is silent in both directions. The schema still
says what it always said, so a test that reads the schema passes whether or
not anything reaches it; and a type that does not enable the behavior simply
has no such field, with nothing reporting the difference. So these assert the
declaration, the registration and the fieldset separately.

The tab is not decoration. ``emails`` and ``email`` are the two fields read
under ``View Personal Identifiable Information`` rather than the ordinary view
permission, and a form where that difference is visible is a form somebody can
reason about.
"""

from pas.plugins.identity.core.behaviors.email import FIELDSET
from pas.plugins.identity.core.behaviors.email import IEmailAddresses
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
NAME = "pas.plugins.identity.email_addresses"


class TestTheBehaviorIsRegistered:
    def test_it_is_a_behavior(self):
        """A ``provides`` naming a schema nothing registered is a behavior an
        FTI cannot enable, and the FTI records the name either way."""
        assert getUtility(IBehavior, name=NAME).interface is IEmailAddresses

    def test_it_is_a_form_field_provider(self):
        """Without this the fields store, index and serialize correctly and
        appear on no form at all. That is how ``group_ids`` was missing for
        months."""
        assert IFormFieldProvider.providedBy(IEmailAddresses)

    def test_the_profile_enables_it(self, portal):
        fti = api.portal.get_tool("portal_types")[PROFILE_PORTAL_TYPE]

        assert NAME in fti.behaviors


class TestTheFieldsMoved:
    def test_they_are_no_longer_on_the_type(self):
        from pas.plugins.identity.core.contents.profile import IUserProfileSchema

        assert "emails" not in IUserProfileSchema.names()
        assert "email" not in IUserProfileSchema.names()

    def test_they_are_on_the_behavior(self):
        assert {"emails", "email"} <= set(IEmailAddresses.names())


class TestTheFieldset:
    def test_it_is_named_email(self):
        fieldsets = IEmailAddresses.queryTaggedValue(FIELDSETS_KEY) or []

        assert [f.__name__ for f in fieldsets] == [FIELDSET] == ["email"]

    def test_it_holds_both_fields(self):
        fieldsets = IEmailAddresses.queryTaggedValue(FIELDSETS_KEY) or []

        assert list(fieldsets[0].fields) == ["emails", "email"]


class TestThePermissionsCameWithThem:
    """A field that loses its read permission on the way to a behavior is a
    field whose address is suddenly readable by every member."""

    def test_reading_them_still_needs_the_pii_permission(self):
        permissions = IEmailAddresses.queryTaggedValue(READ_PERMISSIONS_KEY)

        assert permissions["emails"] == "pas.plugins.identity.content.viewpii"
        assert permissions["email"] == "pas.plugins.identity.content.viewpii"

    def test_writing_the_list_needs_the_ordinary_edit_permission(self):
        """Its owner may edit it; that is what self-service means here."""
        permissions = IEmailAddresses.queryTaggedValue(WRITE_PERMISSIONS_KEY)

        assert permissions["emails"] == "pas.plugins.identity.content.edit"


class TestTheStorageDidNotMove:
    """A schema-only behavior stores on the content object, so the class
    properties that normalize a write and derive the single value are still
    what runs."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.profile = api.content.create(
            container=portal["identity-profiles"],
            type=PROFILE_PORTAL_TYPE,
            id="dana",
            userid="dana",
            login="dana",
            emails=("Dana@Example.COM", "dana@example.com"),
        )

    def test_the_setter_still_normalizes_and_deduplicates(self):
        assert self.profile.emails == ("dana@example.com",)

    def test_the_derived_value_still_derives(self):
        assert self.profile.email == "dana@example.com"

    def test_writing_the_derived_value_still_moves_it_to_the_front(self):
        self.profile.emails = ("a@example.com", "b@example.com")

        self.profile.email = "b@example.com"

        assert self.profile.emails == ("b@example.com", "a@example.com")
