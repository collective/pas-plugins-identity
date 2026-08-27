"""``@types/UserProfile`` reports what the site requires, not only the type.

The edit form Volto builds is this JSON schema. ``plone.restapi`` fills its
``required`` list from ``field.required`` and from nothing else, so a field
named in ``required_profile_fields`` but left optional on the type would hold
a profile ``incomplete`` while the form happily accepted a save without it.
The user saves, nothing changes, they are asked again: a loop produced by one
registry record.

Through the real publisher rather than by constructing the service. The whole
question here is whether a registration on this layer wins over
``plone.restapi``'s own, and a constructed service answers that no matter how
the ZCML reads.

Filed under ``functional`` rather than beside the other service tests because
it commits, and ``tests/content`` runs on the integration layer, which aborts
between tests and refuses to have committed to. No Dex here, so no docker
marker: the fixtures in this package that need one are all opt-in.
"""

from pas.plugins.identity import PACKAGE_NAME
from pas.plugins.identity.content.completeness import REQUIRED_FIELDS_RECORD
from plone import api
from plone.app.testing import applyProfile
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD

import pytest
import requests
import transaction


@pytest.fixture
def url(functional) -> str:
    """Return the portal URL, with the ``[content]`` layer installed.

    Applied here rather than in a layer: the functional layer stacks a
    DemoStorage per test, so the commit is rolled back afterwards and no other
    functional test sees the extra.

    :param functional: The functional layer.
    :returns: The portal URL as the test server publishes it.
    """
    portal = functional["portal"]
    applyProfile(portal, f"{PACKAGE_NAME}.content:default")
    transaction.commit()
    return portal.absolute_url()


def require(portal, *names: str) -> None:
    """Set the required-fields record and commit.

    :param portal: The Plone site.
    :param names: Field names to require.
    """
    api.portal.set_registry_record(REQUIRED_FIELDS_RECORD, names)
    transaction.commit()


class TestTheUserTypeSchema:
    @pytest.fixture(autouse=True)
    def _setup(self, functional, url: str) -> None:
        self.portal = functional["portal"]
        self.url = url

    def required(self, portal_type: str = "UserProfile") -> list[str]:
        """Fetch a type's JSON schema and return its required list.

        :param portal_type: The type to ask about.
        :returns: Field names the form will insist on.
        """
        response = requests.get(
            f"{self.url}/@types/{portal_type}",
            headers={"Accept": "application/json"},
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD),
            timeout=30,
        )
        assert response.status_code == 200, response.text
        return response.json()["required"]

    def test_the_types_own_required_fields_are_reported(self):
        """The base behaviour, and the control for everything below."""
        assert set(self.required()) >= {"login", "email"}

    def test_a_configured_field_becomes_required(self):
        """``location`` is optional on the type. The site wants it anyway."""
        require(self.portal, "email", "location")

        assert "location" in self.required()

    def test_the_types_own_required_fields_survive(self):
        """The record adds; it never takes away.

        ``login`` is not named here and must stay required: the type is the
        one that cannot store an empty value, and a form that let somebody
        clear it would fail on save rather than on the field.
        """
        require(self.portal, "location")

        assert "login" in self.required()

    def test_a_field_that_is_not_on_the_type_is_ignored(self):
        """A configuration mistake should not produce a form nobody can
        submit, asking for a field that is not rendered."""
        require(self.portal, "email", "not-a-field")

        assert "not-a-field" not in self.required()

    def test_another_type_is_untouched(self):
        """The override applies to the user type and to nothing else."""
        require(self.portal, "location")

        assert "location" not in self.required("Document")
