"""``@types`` for the user type: what the edit form is built from.

Two corrections live here and both exist to stop the same shape of loop --
a form that does not ask for what the flow insists on, so the user saves,
stays `incomplete`, and is sent straight back.

The first is the site's required fields, which `plone.restapi` cannot know
about because it reads `required` off the type and nothing else. The second is
the addresses a provider offered without choosing between: the profile arrives
without one, and asking the user to retype an address the site was handed a
list of would be a poor way to end the hold.
"""

from pas.plugins.identity.core.completeness import REQUIRED_FIELDS_RECORD
from pas.plugins.identity.core.pas import PLUGIN_ID as CORE_PLUGIN_ID
from pas.plugins.identity.core.services.types import ProfileTypesGet
from plone import api
from plone.app.testing import TEST_USER_ID
from zope.lifecycleevent import modified

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


class TestTheOfferedAddresses:
    """The form asks with what the provider handed over."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, schema_for, make_profile) -> None:
        self.portal = portal
        self.schema_for = schema_for
        self.profile = make_profile(TEST_USER_ID)
        self.store = portal.acl_users[CORE_PLUGIN_ID].store

    def offer(self, *addresses) -> None:
        """Record a GitHub identity offering these addresses.

        :param addresses: The addresses offered.
        """
        self.store.add(
            "github",
            "1",
            TEST_USER_ID,
            {
                "email_choices": tuple(
                    {"address": address, "verified": True, "primary": False}
                    for address in addresses
                )
            },
        )

    def email(self):
        """Return the `email` property of the user type's schema.

        :returns: The property.
        """
        return self.schema_for()["properties"]["email"]

    def test_a_plain_box_when_nothing_was_offered(self):
        """Every provider that sends one address looks like this."""
        assert "choices" not in self.email()

    def test_the_offered_addresses_become_the_choices(self):
        self.offer("me@example.com", "other@example.com")

        assert self.email()["enum"] == ["me@example.com", "other@example.com"]

    def test_the_trio_restapi_emits_for_a_choice_is_complete(self):
        """`enum`/`enumNames`/`choices` together, so a widget that renders a
        Choice field renders this without being taught anything new."""
        self.offer("me@example.com")

        email = self.email()

        assert email["choices"] == [["me@example.com", "me@example.com (github)"]]
        assert email["enumNames"] == ["me@example.com (github)"]

    def test_each_choice_names_the_provider_that_offered_it(self):
        """Somebody with two linked accounts is shown two lists merged into
        one, and the address alone does not say which is which."""
        self.offer("me@example.com")

        assert "(github)" in self.email()["enumNames"][0]

    def test_the_question_stops_once_it_is_answered(self):
        """Turning somebody's own field into a list of suggestions they have
        already declined is a worse form than the plain box."""
        self.offer("me@example.com", "other@example.com")
        self.profile.email = "chosen@example.com"
        modified(self.profile)

        assert "choices" not in self.email()

    def test_the_field_is_still_free_text(self):
        """Advisory, not binding: the list is what the person was handed, not
        the set of addresses they are allowed to have."""
        self.offer("me@example.com")

        assert self.email()["type"] == "string"
