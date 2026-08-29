"""``@types`` for the user type: what the edit form is built from.

One correction lives here, and it exists to stop a loop: a form that does not
ask for what the flow insists on, so the user saves, stays `incomplete`, and
is sent straight back. `plone.restapi` cannot know about the site's required
fields, because it reads `required` off the type and nothing else.

There used to be a second correction, decorating the `emails` field with the
addresses a provider had offered but nobody had picked between. Nothing offers
them any more: every address a provider reports goes onto the Profile, so the
field this decorated is never empty when there is anything to put in it.
"""

from pas.plugins.identity.core.completeness import REQUIRED_FIELDS_RECORD
from pas.plugins.identity.core.services.types import ProfileTypesGet
from plone import api

import pytest


USER_TYPE = "UserProfile"


@pytest.fixture
def schema_for(portal):
    """Return the type schema the edit form would be built from.

    :param portal: The Plone site.
    :returns: Callable taking a portal type and returning the schema.
    """

    def reply(portal_type: str = USER_TYPE):
        service = ProfileTypesGet(portal, portal.REQUEST)
        service.params = [portal_type]
        return service.reply_for_type()

    return reply


class TestTheSitesRequiredFields:
    """The correction that was already here, and had no test."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, schema_for) -> None:
        self.portal = portal
        self.schema_for = schema_for

    def test_a_registry_required_field_is_reported_required(self):
        """`plone.restapi` reads `required` off the type and nothing else, so
        without this the form does not ask for what holds the profile."""
        api.portal.set_registry_record(REQUIRED_FIELDS_RECORD, ("location",))

        assert "location" in self.schema_for()["required"]

    def test_a_field_the_type_requires_stays_required(self):
        """Adding never removes: the type is the one that cannot store an
        empty value."""
        before = set(self.schema_for()["required"])
        api.portal.set_registry_record(REQUIRED_FIELDS_RECORD, ("location",))

        assert before <= set(self.schema_for()["required"])

    def test_a_field_that_is_not_on_the_type_is_ignored(self):
        """A configuration mistake should say so, not produce a form nobody
        can satisfy."""
        api.portal.set_registry_record(REQUIRED_FIELDS_RECORD, ("not_a_field",))

        assert "not_a_field" not in self.schema_for()["required"]

    def test_another_type_is_left_alone(self):
        api.portal.set_registry_record(REQUIRED_FIELDS_RECORD, ("location",))

        assert "location" not in (self.schema_for("Document").get("required") or [])


class TestTheGroupsFieldsetReachesTheForm:
    """The behavior is enabled on the type and its field is still not on the
    form, unless the schema says it is a form field provider.

    Found by Érico on the demo (2026-08-29): ``/profiles/dana/edit`` had no
    Groups tab. Everything else about the behavior worked -- the FTI listed
    it, the attribute answered, the catalog indexed it, and every test passed
    -- because storage and forms are two different questions and only the
    first one was ever asked.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, schema_for) -> None:
        self.portal = portal
        self.schema_for = schema_for

    def fieldsets(self, portal_type: str = USER_TYPE) -> dict:
        """Return the fieldsets of a type's schema, keyed by id.

        :param portal_type: The type to ask about.
        :returns: Mapping of fieldset id to its list of field names.
        """
        schema = self.schema_for(portal_type)
        return {
            fieldset["id"]: fieldset["fields"]
            for fieldset in schema.get("fieldsets", [])
        }

    def test_the_user_form_offers_the_field(self):
        """A site administrator edits somebody's groups here."""
        assert "group_ids" in self.schema_for()["properties"]

    def test_it_is_on_its_own_tab(self):
        """Which is what the fieldset in the behavior asks for, and the
        reason membership is not mixed in with somebody's home page."""
        assert "group_ids" in self.fieldsets().get("groups", [])

    def test_the_group_form_offers_it_too(self):
        """On a Group the same field is the groups that group is inside, and
        nesting is unreachable from the UI without it."""
        assert "group_ids" in self.fieldsets("UserGroup").get("groups", [])
