"""The Profile container is configuration, not a constant (Érico, 2026-08-21).

Each project decides where profile data lives, so the parent path, the id, the
title and the type are all registry records. These tests are what stops a
later refactor from quietly hard-coding ``/identity-profiles`` again.
"""

from pas.plugins.identity.core import container
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.controlpanel.interfaces import IProfileSettings
from plone import api
from plone.base.interfaces.constrains import ENABLED
from plone.base.interfaces.constrains import ISelectableConstrainTypes
from plone.folder.unordered import UnorderedOrdering

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


class TestDefaults:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    @pytest.mark.no_profile_container
    def test_install_did_not_create_it(self):
        """Where Profiles live is a registry setting, and a profile layered
        on top of this one sets it *after* the install handler runs. Creating
        the container eagerly created it under the id this package ships and
        left the configured one to first login, so a site had two."""
        assert "identity-profiles" not in self.portal.objectIds()
        assert container.get_container() is None

    @pytest.mark.no_profile_container
    def test_it_is_created_on_demand(self):
        """Which is what first login does."""
        created = container.get_container(create=True)

        assert same(created, self.portal["identity-profiles"])

    def test_defaults_are_the_documented_ones(self):
        """The shipped registry values, read back through the helper."""
        assert container.settings() == {
            "parent": "",
            "id": "identity-profiles",
            "title": "Identity Profiles",
            "type": "PrincipalsContainer",
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
        api.portal.set_registry_record(container.TYPE_RECORD, "Folder")

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
    def _setup(self, portal, catalog, allow_principals) -> None:
        self.portal = portal
        self.allow_principals = allow_principals
        self.catalog = catalog

    def test_profile_outside_the_container_is_still_indexed(self):
        """Reorganising content is not a deauthentication."""
        elsewhere = self.allow_principals(
            api.content.create(
                container=self.portal, type="Folder", id="elsewhere", title="Elsewhere"
            )
        )
        api.content.create(
            container=elsewhere,
            type=PROFILE_PORTAL_TYPE,
            id="alice",
            userid="alice",
            login="alice@example.com",
        )

        assert self.catalog.unrestrictedSearchResults(userid="alice")


class TestThePrincipalsContainer:
    """What this package creates when no record names another type."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    @property
    def folder(self):
        """The container the harness created, as a first login would.

        :returns: The Profile container.
        """
        return self.portal["identity-profiles"]

    def test_it_is_the_shipped_type(self):
        assert self.folder.portal_type == container.CONTAINER_PORTAL_TYPE

    @pytest.mark.parametrize("name", ["profile_container_type", "group_container_type"])
    def test_both_type_fields_default_to_it(self, name: str):
        """The field default, not only the value the profile imports: it is
        what ``registerInterface`` resets a record to when the stored value no
        longer validates."""
        assert IProfileSettings[name].default == container.CONTAINER_PORTAL_TYPE

    def test_it_keeps_no_order(self):
        """A position per item, rewritten on every add, is a cost that grows
        with the user base and means nothing for a list of people."""
        assert isinstance(self.folder.getOrdering(), UnorderedOrdering)

    def test_its_page_starts_with_a_title_block(self):
        """Volto draws a page with blocks from its blocks alone, so a
        container created with none would be a blank page."""
        items = self.folder.blocks_layout["items"]

        assert len(items) == 1
        assert self.folder.blocks[items[0]] == {"@type": "title"}


class TestAParentThatRefusesTheType:
    """There is no fallback. A parent that will not take the configured type
    is a folder somebody restricted on purpose, and creating whatever it
    happens to allow instead filed principals in a type nobody chose."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.intranet = api.content.create(
            container=portal, type="Folder", id="intranet", title="Intranet"
        )
        constraints = ISelectableConstrainTypes(self.intranet)
        constraints.setConstrainTypesMode(ENABLED)
        constraints.setLocallyAllowedTypes(["Folder", "Document"])
        api.portal.set_registry_record(container.PARENT_RECORD, "intranet")
        api.portal.set_registry_record(container.ID_RECORD, "people")

    def test_creating_the_container_is_refused(self):
        with pytest.raises(container.ContainerNotFound):
            container.get_container(create=True)

    @pytest.mark.parametrize(
        "fragment",
        [
            pytest.param("profile_container_type", id="the-record"),
            pytest.param("'PrincipalsContainer'", id="the-type"),
            pytest.param("/plone/intranet", id="the-parent"),
        ],
    )
    def test_the_refusal_names(self, fragment: str):
        """The three things an operator needs in order to fix it."""
        with pytest.raises(container.ContainerNotFound) as refused:
            container.get_container(create=True)

        assert fragment in str(refused.value)

    def test_nothing_else_is_created_instead(self):
        """Which is what the fallback did, and ``Folder`` is allowed here."""
        with pytest.raises(container.ContainerNotFound):
            container.get_container(create=True)

        assert "people" not in self.intranet.objectIds()

    def test_a_type_the_parent_allows_is_used(self):
        """The refusal is about the type, not about the parent."""
        api.portal.set_registry_record(container.TYPE_RECORD, "Folder")

        created = container.get_container(create=True)

        assert created.portal_type == "Folder"
        assert same(created.__parent__, self.intranet)


class TestTheFolderishFilter:
    """A type that cannot hold content is refused even where it is allowed."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal):
        self.portal = portal

    def test_a_type_that_cannot_contain_anything_is_refused(self):
        """Which is what a plain ``Document`` is on a site without
        ``plone.volto``. Creating one produced a container at the configured
        path that could hold no Profile and could not be granted the add
        permission -- reported as an invalid *permission*, for a mistake
        about types."""
        allowed = [fti.getId() for fti in self.portal.allowedContentTypes()]
        assert "Document" in allowed
        api.portal.set_registry_record(container.ID_RECORD, "people")
        api.portal.set_registry_record(container.TYPE_RECORD, "Document")

        with pytest.raises(container.ContainerNotFound, match="'Document'"):
            container.get_container(create=True)

        assert "people" not in self.portal.objectIds()

    @pytest.mark.parametrize(
        "klass",
        [
            pytest.param("", id="no-class-at-all"),
            pytest.param("no.such.module.Thing", id="does-not-import"),
            pytest.param("os", id="not-a-class"),
        ],
    )
    def test_an_fti_that_answers_nothing_useful_is_not_folderish(self, klass: str):
        """Three ways to fail and one answer. The last is the one that would
        otherwise raise rather than decline: ``implementedBy`` refuses a
        module with a ``TypeError``."""

        class BrokenFTI:
            pass

        fti = BrokenFTI()
        if klass:
            fti.klass = klass

        assert container._holds_content(fti) is False
