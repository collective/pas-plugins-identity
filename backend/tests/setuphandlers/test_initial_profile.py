"""The ``initial`` profile is a developer's quick start.

``make backend-create-site`` applies it to a fresh site: a front page carrying
the sign-in block, and GitHub and Google providers whose applications accept a
``localhost`` callback. Nothing applies it anywhere else, so nothing else would
notice it had broken.
"""

from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.setuphandlers import initial
from plone import api
from plone.registry.interfaces import IRegistry
from zope.component import getUtility

import pytest
import shutil


PROVIDER_IDS = ["github", "plone-org"]


class TestInitialRegistry:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, initial_registry):
        self.portal = portal
        self.registry = getUtility(IRegistry)
        initial_registry()

    def test_the_providers_are_offered_in_order(self):
        """``get_providers`` answers in stored order, which is the order of
        the buttons on the login page."""
        assert [p.provider_id for p in get_providers()] == PROVIDER_IDS

    @pytest.mark.parametrize(
        "provider_id,driver_id,title",
        [
            ("github", "github", "GitHub"),
            ("plone-org", "google", "@plone.org email"),
        ],
    )
    def test_provider_is_readable_through_the_api(
        self, provider_id: str, driver_id: str, title: str
    ):
        provider = get_provider(provider_id)
        assert provider.driver_id == driver_id
        assert provider.title == title
        assert provider.enabled is True

    @pytest.mark.parametrize("provider_id", PROVIDER_IDS)
    def test_provider_carries_its_client_secret(self, provider_id: str):
        """The point of the quick start: signing in needs no application
        registered first."""
        assert get_provider(provider_id).config["client_secret"]

    @pytest.mark.parametrize("provider_id", PROVIDER_IDS)
    def test_an_empty_group_map_is_a_mapping(self, provider_id: str):
        """The export writes it as an empty element, and every login applies
        the map."""
        assert get_provider(provider_id).groupmap == {}

    @pytest.mark.parametrize("name", ["gate_exempt_paths", "required_profile_fields"])
    def test_an_empty_tuple_is_a_tuple(self, name: str):
        """Also written as empty elements, and read by the profile gate on
        every request."""
        assert self.registry[f"pas.plugins.identity.{name}"] == ()


class TestExampleContent:
    """Imported from a copy, because the import removes a file from the
    folder it reads -- and stripped of what ``.gitignore`` keeps out of the
    repository, so the copy is what a fresh checkout has."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, tmp_path, monkeypatch):
        self.portal = portal
        # ``create_site.py`` creates a Volto site, whose root has blocks. The
        # test site is a classic one, and the import drops what its root has
        # no field for without a word.
        fti = api.portal.get_tool("portal_types")["Plone Site"]
        fti.manage_changeProperties(behaviors=(*fti.behaviors, "volto.blocks"))
        self.folder = tmp_path / "examplecontent"
        shutil.copytree(initial.EXAMPLE_CONTENT_FOLDER, self.folder)
        for name in (self.folder / ".gitignore").read_text().split():
            (self.folder / name).unlink(missing_ok=True)
        monkeypatch.setattr(initial, "EXAMPLE_CONTENT_FOLDER", self.folder)

    def create(self) -> None:
        """Run the pre-handler as ``create_site.py`` does, as a manager."""
        with api.env.adopt_roles(["Manager"]):
            initial.create_example_content(api.portal.get_tool("portal_setup"))

    def test_the_front_page_carries_the_sign_in_block(self):
        self.create()

        inside_grids = [
            block
            for grid in self.portal.blocks.values()
            if grid["@type"] == "gridBlock"
            for block in grid["blocks"].values()
        ]
        assert "identitySignIn" in {block["@type"] for block in inside_grids}

    def test_an_exported_principals_file_is_removed_first(self):
        """``make export-content`` writes one beside the content, and
        importing it would create the exporting site's users."""
        (self.folder / "principals.json").write_text('{"groups": [], "members": []}')

        self.create()

        assert not (self.folder / "principals.json").exists()
