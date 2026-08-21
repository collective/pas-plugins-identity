"""The Profile container is configuration, not a constant (Érico, 2026-08-21).

Each project decides where profile data lives, so the parent path, the id, the
title and the type are all registry records. These tests are what stops a
later refactor from quietly hard-coding ``/identity-profiles`` again.
"""

from pas.plugins.identity.profile import container
from pas.plugins.identity.profile.catalog import PROFILE_PORTAL_TYPE
from plone import api

import pytest


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


@pytest.fixture
def manager(portal):
    """Run the test body with Manager rights.

    :param portal: The Plone site.
    :returns: The Plone site.
    """
    with api.env.adopt_roles(["Manager"]):
        yield portal


class TestDefaults:
    def test_install_created_it(self, portal):
        """The container exists after the profile is applied."""
        assert same(container.get_container(), portal["identity-profiles"])

    def test_defaults_are_the_documented_ones(self, portal):
        """The shipped registry values, read back through the helper."""
        assert container.settings() == {
            "parent": "",
            "id": "identity-profiles",
            "title": "Identity Profiles",
            "type": "Folder",
        }

    def test_parent_defaults_to_the_site_root(self, portal):
        """An empty parent record means the portal itself."""
        assert same(container.get_parent(), portal)

    def test_excluded_from_navigation(self, portal):
        """A folder of Profiles is not a section of the website."""
        assert portal["identity-profiles"].exclude_from_nav is True


class TestConfigured:
    def test_parent_path_is_honoured(self, manager):
        """A project that keeps member data under a section says so."""
        api.content.create(
            container=manager, type="Folder", id="intranet", title="Intranet"
        )
        api.portal.set_registry_record(container.PARENT_RECORD, "intranet")
        api.portal.set_registry_record(container.ID_RECORD, "people")

        created = container.get_container(create=True)

        assert created.getId() == "people"
        assert same(created.__parent__, manager["intranet"])

    def test_title_and_type_are_honoured(self, manager):
        """Both are used at creation time."""
        api.portal.set_registry_record(container.ID_RECORD, "people")
        api.portal.set_registry_record(container.TITLE_RECORD, "Our People")

        created = container.get_container(create=True)

        assert created.Title() == "Our People"
        assert created.portal_type == "Folder"

    def test_leading_slashes_are_tolerated(self, manager):
        """An operator typing an absolute-looking path gets what they meant."""
        api.content.create(
            container=manager, type="Folder", id="intranet", title="Intranet"
        )
        api.portal.set_registry_record(container.PARENT_RECORD, "/intranet/")

        assert same(container.get_parent(), manager["intranet"])

    def test_missing_parent_is_an_error(self, portal):
        """Silently creating it at the root would hide the typo."""
        api.portal.set_registry_record(container.PARENT_RECORD, "nowhere")

        with pytest.raises(container.ContainerNotFound):
            container.get_parent()


class TestLookup:
    def test_absent_container_reads_as_none(self, manager):
        """Reading must not have a side effect."""
        api.portal.set_registry_record(container.ID_RECORD, "not-created-yet")

        assert container.get_container() is None
        assert "not-created-yet" not in manager.objectIds()

    def test_create_is_idempotent(self, manager):
        """Applying the profile twice must not make a second folder."""
        first = container.get_container(create=True)
        second = container.get_container(create=True)

        assert same(first, second)

    def test_site_root_is_recognised(self, portal):
        """The uninstall path must never try to remove the portal."""
        assert container.is_site_root(portal) is True
        assert container.is_site_root(portal["identity-profiles"]) is False


class TestCatalogIsNotScopedToTheContainer:
    def test_profile_outside_the_container_is_still_indexed(self, manager, catalog):
        """Reorganising content is not a deauthentication."""
        elsewhere = api.content.create(
            container=manager, type="Folder", id="elsewhere", title="Elsewhere"
        )
        api.content.create(
            container=elsewhere,
            type=PROFILE_PORTAL_TYPE,
            id="alice",
            userid="alice",
            login="alice@example.com",
        )

        assert catalog.unrestrictedSearchResults(userid="alice")
