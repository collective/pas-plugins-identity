"""The Profile container is configuration, not a constant (Érico, 2026-08-21).

Each project decides where profile data lives, so the parent path, the id, the
title and the type are all registry records. These tests are what stops a
later refactor from quietly hard-coding ``/identity-profiles`` again.
"""

from . import PROFILE_ID
from pas.plugins.identity.profile import container
from pas.plugins.identity.profile.catalog import PROFILE_PORTAL_TYPE
from plone import api

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


def same(left, right) -> bool:
    """Compare two objects by physical path.

    Acquisition hands out a fresh wrapper on every attribute access, so ``is``
    is false between two references to one object and the failure reads as a
    missing object rather than as a wrapper.

    :param left: An object in the site.
    :param right: Another object in the site.
    :returns: Whether they are the same object.
    """
    return left.getPhysicalPath() == right.getPhysicalPath()


class TestDefaults:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_install_created_it(self):
        """The container exists after the profile is applied."""
        assert same(container.get_container(), self.portal["identity-profiles"])

    def test_defaults_are_the_documented_ones(self):
        """The shipped registry values, read back through the helper."""
        assert container.settings() == {
            "parent": "",
            "id": "identity-profiles",
            "title": "Identity Profiles",
            "type": "Folder",
        }

    def test_parent_defaults_to_the_site_root(self):
        """An empty parent record means the portal itself."""
        assert same(container.get_parent(), self.portal)

    def test_excluded_from_navigation(self):
        """A folder of Profiles is not a section of the website."""
        assert self.portal["identity-profiles"].exclude_from_nav is True


class TestConfigured:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_parent_path_is_honoured(self):
        """A project that keeps member data under a section says so."""
        api.content.create(
            container=self.portal, type="Folder", id="intranet", title="Intranet"
        )
        api.portal.set_registry_record(container.PARENT_RECORD, "intranet")
        api.portal.set_registry_record(container.ID_RECORD, "people")

        created = container.get_container(create=True)

        assert created.getId() == "people"
        assert same(created.__parent__, self.portal["intranet"])

    def test_title_and_type_are_honoured(self):
        """Both are used at creation time."""
        api.portal.set_registry_record(container.ID_RECORD, "people")
        api.portal.set_registry_record(container.TITLE_RECORD, "Our People")

        created = container.get_container(create=True)

        assert created.Title() == "Our People"
        assert created.portal_type == "Folder"

    def test_leading_slashes_are_tolerated(self):
        """An operator typing an absolute-looking path gets what they meant."""
        api.content.create(
            container=self.portal, type="Folder", id="intranet", title="Intranet"
        )
        api.portal.set_registry_record(container.PARENT_RECORD, "/intranet/")

        assert same(container.get_parent(), self.portal["intranet"])

    def test_missing_parent_is_an_error(self):
        """Silently creating it at the root would hide the typo."""
        api.portal.set_registry_record(container.PARENT_RECORD, "nowhere")

        with pytest.raises(container.ContainerNotFound):
            container.get_parent()


class TestLookup:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_absent_container_reads_as_none(self):
        """Reading must not have a side effect."""
        api.portal.set_registry_record(container.ID_RECORD, "not-created-yet")

        assert container.get_container() is None
        assert "not-created-yet" not in self.portal.objectIds()

    def test_create_is_idempotent(self):
        """Applying the profile twice must not make a second folder."""
        first = container.get_container(create=True)
        second = container.get_container(create=True)

        assert same(first, second)

    def test_site_root_is_recognised(self):
        """The uninstall path must never try to remove the portal."""
        assert container.is_site_root(self.portal) is True
        assert container.is_site_root(self.portal["identity-profiles"]) is False


class TestCatalogIsNotScopedToTheContainer:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, catalog) -> None:
        self.portal = portal
        self.catalog = catalog

    def test_profile_outside_the_container_is_still_indexed(self):
        """Reorganising content is not a deauthentication."""
        elsewhere = api.content.create(
            container=self.portal, type="Folder", id="elsewhere", title="Elsewhere"
        )
        api.content.create(
            container=elsewhere,
            type=PROFILE_PORTAL_TYPE,
            id="alice",
            userid="alice",
            login="alice@example.com",
        )

        assert self.catalog.unrestrictedSearchResults(userid="alice")


class TestContainerTypeFallback:
    """The container type is a registry record, and its shipped default is
    ``Folder`` -- which a site built from the ``volto`` distribution does not
    allow at the portal root at all. Installing the layer there failed with a
    bare "Disallowed subobject type", naming neither the record to change nor
    the fact that a record exists. Volto is the frontend this package ships,
    so that is not an edge case to leave documented."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal):
        self.portal = portal

    def test_the_configured_type_is_used_when_it_is_allowed(self):
        """The ordinary case, and the only one on a site whose structure
        somebody has thought about."""
        assert container._creatable_type(self.portal, "Folder") == "Folder"

    def test_a_disallowed_type_falls_back_to_one_the_parent_takes(self):
        """``Document`` is first in the fallback order because it is the
        folderish type a Volto site has."""
        chosen = container._creatable_type(self.portal, "NoSuchType")

        assert chosen == "Document"

    def test_nothing_addable_is_an_error_that_names_the_record(self):
        """A site where neither fallback is allowed is misconfigured, and the
        message has to say which knob to turn."""

        class NoTypesAllowed:
            @staticmethod
            def allowedContentTypes():
                return []

            @staticmethod
            def getPhysicalPath():
                return ("", "Plone")

        with pytest.raises(container.ContainerNotFound, match="container_type"):
            container._creatable_type(NoTypesAllowed(), "Folder")
