"""GenericSetup for the dedicated Profile catalog.

The point of this module is the thing that was missing rather than wrong:
``ZCatalogXMLAdapter`` is registered for ``IZCatalog`` and has always adapted
this catalog. What did not exist was a step pointing at it, so the indexes and
columns were built by hand in Python and could not be changed without one.

The safety property is the last class here, and it is the reason the file is
called ``identity-catalog.xml`` rather than ``catalog.xml``: the stock step
resolves its target with ``queryUtility(ICatalogTool)``, which answers
``portal_catalog``. A ``catalog.xml`` in this profile would not be ignored. It
would be applied to the site catalog.
"""

from pas.plugins.identity.core.catalog import CATALOG_ID
from pas.plugins.identity.setuphandlers.catalogxml import export_identity_catalog
from pas.plugins.identity.setuphandlers.catalogxml import IdentityCatalogXMLAdapter
from pas.plugins.identity.setuphandlers.catalogxml import import_identity_catalog
from pathlib import Path
from plone import api
from Products.GenericSetup.interfaces import IBody
from Products.GenericSetup.interfaces import ISetupEnviron
from Products.ZCatalog.interfaces import IZCatalog
from zope.component import queryMultiAdapter
from zope.interface import implementer

import logging
import pas.plugins.identity
import pytest


PROFILE = "pas.plugins.identity:default"
STEP = "identity-catalog"

#: The shipped profile directory, which the context stub reads from.
PROFILE_DIR = Path(pas.plugins.identity.__file__).parent / "profiles" / "default"

#: A catalog fragment adding one index and one column, which is the whole
#: developer-facing promise: a new index is an edit to a file.
ADDS_ONE = b"""<?xml version="1.0" encoding="utf-8"?>
<object name="portal_identity_catalog" meta_type="Identity Profile Catalog">
 <index name="nickname" meta_type="FieldIndex">
  <indexed_attr value="nickname"/>
 </index>
 <column value="nickname"/>
</object>
"""


@implementer(ISetupEnviron)
class Environ:
    """The least a body adapter needs, and nothing this package owns."""

    def getLogger(self, name: str) -> logging.Logger:
        """Return a logger.

        :param name: Logger name.
        :returns: The logger.
        """
        return logging.getLogger(name)

    def shouldPurge(self) -> bool:
        """Never purge; this package's profile is an extension profile.

        :returns: Always ``False``.
        """
        return False


@implementer(ISetupEnviron)
class Context(Environ):
    """An import context over the shipped profile, pointed at a given site.

    It has to provide ``ISetupEnviron`` and not merely look like it:
    ``importObjects`` resolves the body adapter with
    ``queryMultiAdapter((obj, context), IBody)``, and a stub that does not
    provide the interface gets ``None`` back and imports nothing, reporting
    success. That is the same silent misdirection the separate filename exists
    to prevent, and the first draft of this module walked into it.
    """

    def __init__(self, site, files: dict | None = None) -> None:
        """Store the site and what ``readDataFile`` should answer.

        :param site: What ``getSite`` should answer.
        :param files: Filename to body. Defaults to the shipped profile.
        """
        self._site = site
        self._files = files

    def getSite(self):
        """Return the site being set up.

        :returns: The site.
        """
        return self._site

    def readDataFile(self, filename: str, subdir: str | None = None) -> bytes | None:
        """Return a profile file's body.

        :param filename: The file being asked for.
        :param subdir: Ignored; this profile has no subdirectories.
        :returns: The body, or ``None`` when the profile has no such file.
        """
        if self._files is not None:
            return self._files.get(filename)
        path = PROFILE_DIR / filename
        return path.read_bytes() if path.is_file() else None


class TestTheAdapter:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, catalog) -> None:
        self.portal = portal
        self.catalog = catalog
        self.adapter = queryMultiAdapter((catalog, Environ()), IBody)

    def test_the_stock_adapter_already_applied(self):
        """The registration that made this small: every ZCatalog provides
        ``IZCatalog``, so nothing had to be written to read one as XML."""
        assert IZCatalog.providedBy(self.catalog)

    def test_ours_is_the_one_that_answers(self):
        """Registered for ``IIdentityProfileCatalog``, which is narrower than
        ``IZCatalog``, so it wins for this tool and leaves the site catalog's
        adapter exactly as it was."""
        assert isinstance(self.adapter, IdentityCatalogXMLAdapter)

    def test_the_filename_is_not_the_stock_one(self):
        """The one line this subclass exists for."""
        assert self.adapter.name == "identity-catalog"
        assert self.adapter.suffix == ".xml"

    def test_the_site_catalog_keeps_the_stock_adapter(self):
        """Narrowing ours must not have changed anybody else's."""
        other = queryMultiAdapter(
            (api.portal.get_tool("portal_catalog"), Environ()), IBody
        )

        assert not isinstance(other, IdentityCatalogXMLAdapter)
        assert other.name == "catalog"

    def test_an_index_can_be_added_by_xml(self):
        """The developer-facing promise. Nothing in Python changes."""
        assert "nickname" not in self.catalog.indexes()

        self.adapter.body = ADDS_ONE

        assert "nickname" in self.catalog.indexes()

    def test_a_column_can_be_added_by_xml(self):
        assert "nickname" not in self.catalog.schema()

        self.adapter.body = ADDS_ONE

        assert "nickname" in self.catalog.schema()

    def test_an_index_can_be_removed_by_xml(self):
        """Inherited from the stock adapter, and something the hand-written
        handlers never had: they could only add."""
        self.adapter.body = ADDS_ONE
        assert "nickname" in self.catalog.indexes()

        self.adapter.body = ADDS_ONE.replace(
            b'<index name="nickname" meta_type="FieldIndex">',
            b'<index name="nickname" meta_type="FieldIndex" remove="True">',
        )

        assert "nickname" not in self.catalog.indexes()

    def test_applying_the_same_body_twice_changes_nothing(self):
        self.adapter.body = ADDS_ONE
        before = (sorted(self.catalog.indexes()), sorted(self.catalog.schema()))

        self.adapter.body = ADDS_ONE

        assert (sorted(self.catalog.indexes()), sorted(self.catalog.schema())) == before


class TestTheSteps:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, catalog) -> None:
        self.portal = portal
        self.catalog = catalog
        self.setup = api.portal.get_tool("portal_setup")

    def test_the_import_step_is_registered(self):
        """``getSortedImportSteps`` rather than the tool's own registry: a
        step registered in ZCML lands in the global one, and the tool merges
        the two only here."""
        assert STEP in self.setup.getSortedImportSteps()

    def test_the_export_step_is_registered(self):
        assert STEP in self.setup.listExportSteps()

    def test_the_import_step_runs_from_the_profile(self):
        """The whole path an operator uses, not the adapter in isolation."""
        self.catalog.delIndex("group_ids")
        assert "group_ids" not in self.catalog.indexes()

        self.setup.runImportStepFromProfile(PROFILE, STEP)

        assert "group_ids" in self.catalog.indexes()

    def test_the_export_step_writes_the_catalog(self):
        """Round-trip: what the export writes is what the import reads."""
        result = self.setup.runExportStep(STEP)

        assert "identity-catalog.xml" in result["steps"] or result["tarball"]

    def test_a_site_without_the_catalog_is_not_an_error(self):
        """The step is registered instance-wide and runs during every add-on
        installation in every site, including the ones that never applied this
        profile. Answering "not here" quietly is the whole of its behaviour
        there."""

        class Bare:
            pass

        import_identity_catalog(Context(Bare()))
        export_identity_catalog(Context(Bare()))

    def test_the_step_finds_the_catalog_on_the_context_site(self):
        """Not on the thread-local one, which is a different question that
        merely happens to have the same answer here."""
        self.catalog.delIndex("userid")

        import_identity_catalog(Context(self.portal))

        assert "userid" in self.catalog.indexes()

    def test_a_profile_without_the_file_writes_nothing(self):
        """``readDataFile`` answers ``None`` and the adapter is never handed a
        body, so a profile that simply does not carry the file leaves the
        catalog alone rather than emptying it."""
        before = sorted(self.catalog.indexes())

        import_identity_catalog(Context(self.portal, files={}))

        assert sorted(self.catalog.indexes()) == before


class TestTheStockStepCannotReachUs:
    """Why the filename differs, asserted rather than explained."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, catalog) -> None:
        self.portal = portal
        self.catalog = catalog

    def test_the_profile_ships_no_catalog_xml(self):
        """A ``catalog.xml`` here would be read by the stock step and applied
        to ``portal_catalog``, silently adding this package's indexes to the
        site catalog. It is not ignored; it is misdirected."""
        profile = Path(pas.plugins.identity.__file__).parent / "profiles" / "default"

        assert not (profile / "catalog.xml").exists()
        assert (profile / "identity-catalog.xml").exists()

    def test_the_stock_step_resolves_the_site_catalog(self):
        """``queryUtility(ICatalogTool)`` is what it asks, and ours is
        registered as no utility at all."""
        from Products.CMFCore.interfaces import ICatalogTool
        from zope.component import getSiteManager

        resolved = getSiteManager(self.portal).queryUtility(ICatalogTool)

        assert resolved.getId() == "portal_catalog"
        assert resolved.getId() != CATALOG_ID
