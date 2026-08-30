"""One profile installs the whole add-on.

There used to be three, and two of them were named after packages rather than
distributions so that the add-ons control panel would list them separately.
What is left is the ``[server]`` layer, which is genuinely optional: its
dependency is compiled, and a site that is not an authorization server has no
reason to carry it.
"""

from pas.plugins.identity import PACKAGE_NAME
from pas.plugins.identity.core.catalog import CATALOG_ID
from pas.plugins.identity.core.catalog import GROUP_PORTAL_TYPE
from pas.plugins.identity.core.catalog import INDEXES
from pas.plugins.identity.core.catalog import METADATA
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.controlpanel.interfaces import IProfileSettings
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.core.pas.profile import PLUGIN_ID as PROFILE_PLUGIN_ID
from plone import api
from zope.schema import getFieldNames

import pytest


@pytest.fixture(scope="class")
def portal(portal_class):
    """Return the portal."""
    yield portal_class


class TestHiddenProfiles:
    """The add-ons control panel should offer one thing: the add-on."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.non_installable = api.addon._get_non_installable_addons()

    @pytest.mark.parametrize(
        "profile",
        [
            f"{PACKAGE_NAME}:uninstall",
            f"{PACKAGE_NAME}.server:uninstall",
        ],
    )
    def test_uninstall_profiles_hidden(self, profile: str):
        """Uninstall profiles are reached through the add-on, not listed."""
        assert profile in self.non_installable.profiles

    @pytest.mark.parametrize(
        "profile",
        [
            f"{PACKAGE_NAME}:default",
        ],
    )
    def test_default_profile_stays_installable(self, profile: str):
        """Hiding must not hide the profile people actually install."""
        assert profile not in self.non_installable.profiles

    @pytest.mark.parametrize(
        "package",
        [
            f"{PACKAGE_NAME}.upgrades",
        ],
    )
    def test_upgrades_package_hidden(self, package: str):
        """The upgrades package is machinery, not a product."""
        assert package in self.non_installable.products


class TestTheServerLayerIsItsOwnProduct:
    """The optional layer installs as its own entry in the add-ons panel.

    That follows from where its ``registerProfile`` lives: GenericSetup builds
    the profile id from the package the directive is in, so the layer is
    ``pas.plugins.identity.server`` rather than an extra profile of the
    distribution.

    The installer resolves a product's version through
    ``importlib.metadata.distribution``, and that package name is not a
    distribution. That answers empty rather than raising -- but "rather than
    raising" is the whole reason this class exists, because it is the one way
    this arrangement could break the control panel for the whole site.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, installer) -> None:
        self.portal = portal
        self.installer = installer
        self.product = f"{PACKAGE_NAME}.server"

    def test_the_layer_is_installable(self):
        """The panel offers it, which means it found a default profile."""
        assert self.installer.is_product_installable(self.product) is True

    def test_the_install_profile_resolves(self):
        """``default`` is the name the panel's install button applies."""
        profile = self.installer.get_install_profile(self.product)
        assert profile is not None
        assert profile["id"] == f"{self.product}:default"

    def test_the_uninstall_profile_resolves(self):
        """Hidden from the list, still reachable through the add-on."""
        profile = self.installer.get_uninstall_profile(self.product)
        assert profile is not None
        assert profile["id"] == f"{self.product}:uninstall"

    def test_asking_for_a_version_does_not_raise(self):
        """A package that is not a distribution has no version to report.

        The panel renders the empty string; what it must not do is propagate
        ``PackageNotFoundError`` out of a listing that also has to render
        every other add-on on the site.
        """
        assert self.installer.get_product_version(self.product) == ""

    def test_the_content_layer_is_no_longer_a_product(self):
        """It was one, and the id is the thing an operator's notes remember.

        ``None`` rather than ``False``: the installer answers that for a name
        it has never heard of, where ``False`` means "known and not
        installable". Either way the panel offers no button, which is the
        point -- there is no such profile any more.
        """
        assert not self.installer.is_product_installable(f"{PACKAGE_NAME}.content")


class TestVersioningIsInstalled:
    """Versioning takes two pieces of configuration and a guard, and the FTI
    only shows one of them."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    @pytest.mark.parametrize("portal_type", ["UserProfile", "UserGroup"])
    def test_the_type_has_a_versioning_policy(self, portal_type: str):
        """``repositorytool.xml`` is the half a behaviour cannot provide, and
        CMFEditions' importer silently ignores a ``type`` element placed
        outside ``policymap`` -- so this is the assertion that catches a
        policy that looks right and was never read."""
        repository = api.portal.get_tool("portal_repository")

        assert portal_type in repository.getVersionableContentTypes()

    def test_the_credential_guard_is_registered(self):
        """CMFEditions copies annotations into a snapshot, and the password
        behaviour keeps its hash in one. Registered on install whether or not
        that behaviour is enabled anywhere."""
        from pas.plugins.identity.core.versioning import MODIFIER_ID

        assert MODIFIER_ID in api.portal.get_tool("portal_modifier").objectIds()

    def test_the_credential_guard_is_enabled(self):
        """A registered but disabled modifier is inert, which here would mean
        the guard visible in the ZMI and credentials going into history."""
        from pas.plugins.identity.core.versioning import MODIFIER_ID

        modifier = api.portal.get_tool("portal_modifier").get(MODIFIER_ID)

        assert modifier.isEnabled() is True


class TestSetupInstall:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_addon_installed(self, installer):
        """Test if pas.plugins.identity is installed."""
        assert installer.is_product_installed(PACKAGE_NAME) is True

    def test_browserlayer(self, browser_layers):
        """Test that IBrowserLayer is registered."""
        from pas.plugins.identity.interfaces import IBrowserLayer

        assert IBrowserLayer in browser_layers

    def test_latest_version(self, profile_last_version):
        """Test latest version of default profile."""
        assert profile_last_version(f"{PACKAGE_NAME}:default") == "1000"


class TestBothPluginsInstalled:
    """Two PAS plugins, and the one profile installs both.

    They used to arrive from two profiles, which meant a site could have the
    authenticating half without the half that serves what a user *is*. The
    symptom of that combination was a login that succeeded and returned a
    principal nothing could describe.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.acl_users = api.portal.get_tool("acl_users")

    @pytest.mark.parametrize("plugin_id", [PLUGIN_ID, PROFILE_PLUGIN_ID])
    def test_plugin_present(self, plugin_id: str):
        """Both objects are in ``acl_users``."""
        assert plugin_id in self.acl_users.objectIds()


class TestContentInstalled:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.catalog = api.portal.get_tool(CATALOG_ID)

    def test_catalog_tool_present(self):
        """The dedicated catalog is added by toolset.xml."""
        assert self.catalog.getId() == CATALOG_ID

    def test_indexes_created(self):
        """Every declared index exists; GenericSetup cannot do this for us."""
        assert set(self.catalog.indexes()) >= {name for name, _ in INDEXES}

    def test_metadata_created(self):
        """Brains carry the whole property sheet."""
        assert set(self.catalog.schema()) >= set(METADATA)

    @pytest.mark.parametrize("portal_type", [PROFILE_PORTAL_TYPE, GROUP_PORTAL_TYPE])
    def test_type_registered(self, portal_type: str):
        """Both FTIs are installed."""
        types = api.portal.get_tool("portal_types")
        assert portal_type in types.objectIds()

    @pytest.mark.parametrize(
        "portal_type,workflow",
        [
            (PROFILE_PORTAL_TYPE, "user_profile_workflow"),
            (GROUP_PORTAL_TYPE, "user_group_workflow"),
        ],
    )
    def test_workflow_bound(self, portal_type: str, workflow: str):
        """Each type gets its own workflow."""
        workflows = api.portal.get_tool("portal_workflow")

        assert workflows.getChainForPortalType(portal_type) == (workflow,)

    def test_container_not_created(self):
        """Install deliberately leaves it to the first person who needs one.

        Where Profiles live is a registry setting, and a profile layered on
        top sets it *after* this handler has run. See ``post_install``.
        """
        assert "identity-profiles" not in self.portal.objectIds()

    def test_core_records_point_at_the_types(self):
        """Which is what makes users content without anybody configuring it."""
        assert (
            api.portal.get_registry_record("pas.plugins.identity.user_content_type")
            == PROFILE_PORTAL_TYPE
        )
        assert (
            api.portal.get_registry_record("pas.plugins.identity.group_content_type")
            == GROUP_PORTAL_TYPE
        )


class TestProfileSettings:
    """The profile imports its settings schema, so the two cannot drift."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    @pytest.mark.parametrize("name", getFieldNames(IProfileSettings))
    def test_record_exists(self, name: str):
        """Every field in the schema is a record the profile created."""
        record = f"pas.plugins.identity.{name}"

        assert api.portal.get_registry_record(record, default=None) is not None

    @pytest.mark.parametrize(
        "name,expected",
        [
            ("profile_container_parent", ""),
            ("profile_container_id", "identity-profiles"),
            ("profile_container_title", "Identity Profiles"),
            ("profile_container_type", "Folder"),
            ("profile_enumeration_states", ("incomplete", "complete")),
            ("group_enumeration_states", ("active",)),
        ],
    )
    def test_default_value(self, name: str, expected):
        """The shipped defaults."""
        assert (
            api.portal.get_registry_record(f"pas.plugins.identity.{name}") == expected
        )
