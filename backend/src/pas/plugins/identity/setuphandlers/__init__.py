"""GenericSetup handlers.

One ``default`` profile installs the whole add-on: the control panel, both PAS
plugins, the two content types users and groups are, and the catalog they are
filed in. There is no longer a second profile to remember, and no site where
half of this is present.

Every profile here has a matching uninstall profile, and uninstall is tested:
install -> uninstall leaves no plugin behind and the site still works.
"""

from pas.plugins.identity import logger
from pas.plugins.identity import PACKAGE_NAME
from pas.plugins.identity.core.catalog import CATALOG_ID
from pas.plugins.identity.core.catalog import query_catalog
from pas.plugins.identity.core.container import grant_add_permissions
from pas.plugins.identity.core.controlpanel.interfaces import IIdentitySettings
from pas.plugins.identity.core.controlpanel.interfaces import IProfileSettings
from pas.plugins.identity.core.subscribers.principals import sync_core_records
from pas.plugins.identity.core.versioning import register_modifier
from pas.plugins.identity.core.versioning import unregister_modifier
from pas.plugins.identity.setuphandlers.catalog import add_indexes
from pas.plugins.identity.setuphandlers.catalog import add_lexicon
from pas.plugins.identity.setuphandlers.catalog import add_metadata
from pas.plugins.identity.setuphandlers.plugins import install_plugin
from pas.plugins.identity.setuphandlers.plugins import install_profile_plugin
from pas.plugins.identity.setuphandlers.plugins import uninstall_plugin
from pas.plugins.identity.setuphandlers.plugins import uninstall_profile_plugin
from plone import api
from plone.base.interfaces.installable import INonInstallable
from plone.registry.interfaces import IRegistry
from Products.GenericSetup.tool import SetupTool
from Products.PluggableAuthService.PluggableAuthService import PluggableAuthService
from zope.component import getUtility
from zope.interface import implementer
from zope.interface import Interface


@implementer(INonInstallable)
class HiddenProfiles:
    """Keep helper profiles out of the add-ons control panel."""

    def getNonInstallableProfiles(self) -> list[str]:
        """Hide the uninstall profiles.

        :returns: Profile ids to hide.
        """
        return [
            f"{PACKAGE_NAME}:uninstall",
            f"{PACKAGE_NAME}.server:uninstall",
        ]

    def getNonInstallableProducts(self) -> list[str]:
        """Hide the upgrades package.

        :returns: Product names to hide.
        """
        return [f"{PACKAGE_NAME}.upgrades"]


#: Prefix every settings interface in this package is registered under. The
#: registry XML states it too; they have to agree or a re-install creates a
#: second, parallel set of records.
SETTINGS_PREFIX = PACKAGE_NAME

#: Every settings schema the ``default`` profile owns records for.
SETTINGS_INTERFACES = (IIdentitySettings, IProfileSettings)


def register_settings(interface: type[Interface]) -> None:
    """Create registry records for every field of a settings interface.

    Called from ``post_install``, which makes a re-install self-healing: a
    field added to the interface since the site was set up gets its record,
    with its schema default, without an upgrade step.

    Existing values are kept -- ``registerInterface`` re-reads each record it
    already finds and only falls back to the default when the stored value no
    longer validates. That is what makes this safe to run on every install
    rather than only on the first.

    Not a substitute for the profile's ``registry.xml``: that is what states
    the *shipped* values, and a fresh site still gets them from there. This
    covers the site that was installed before the field existed, which is
    otherwise a ``KeyError`` from every control panel reading the interface.

    :param interface: The settings schema to register.
    """
    registry = getUtility(IRegistry)
    registry.registerInterface(interface, prefix=SETTINGS_PREFIX)


def _acl_users() -> PluggableAuthService:
    """Return the site's PAS instance.

    :returns: The ``acl_users`` folder of the current site.
    """
    return api.portal.get_tool("acl_users")


def post_install(context: SetupTool) -> None:
    """Finish the install once the ``default`` profile is imported.

    Order matters. The settings come first because everything below reads
    them; the catalog before the plugin that queries it; the core principal
    records before anything asks where a user goes.

    The Profile *container* is deliberately not created here. Where Profiles
    live is a registry setting, and a profile layered on top of this one -- a
    policy package, a demo, anything with its own ``registry.xml`` -- sets it
    *after* this handler has run. Creating the container eagerly therefore
    created it under whatever id this package happens to ship, and the site
    ended up with two: the one nobody asked for, and the one the first login
    made under the configured id. A container with no Profiles in it does no
    work, and one is made on demand the first time somebody needs it.

    :param context: The setup tool running the import.
    """
    for interface in SETTINGS_INTERFACES:
        register_settings(interface)

    catalog = api.portal.get_tool(CATALOG_ID)
    add_lexicon(catalog)
    add_indexes(catalog)
    add_metadata(catalog)

    acl_users = _acl_users()
    install_plugin(acl_users)
    install_profile_plugin(acl_users)

    # Both principal types are versionable, and CMFEditions deep-copies
    # annotations -- which is where the optional password behavior keeps its
    # hash. Registered whether or not that behavior is enabled anywhere: a
    # site that switches it on later must not start writing credentials into
    # its history with nothing in place to stop it.
    register_modifier(api.portal.get_tool("portal_modifier"))

    # The subscriber in ``core.principals`` has already run for any container
    # setting this profile's registry.xml wrote. Doing it again here covers
    # the site that reinstalls without changing one, and costs a write.
    sync_core_records()
    # A container an operator made by hand, or one left behind by an earlier
    # install, has no add permission on it and nothing else would ever give it
    # one -- the grant otherwise only happens when this package creates the
    # folder itself.
    grant_add_permissions()


def rebuild_catalog(context: SetupTool) -> None:
    """Clear the Profile catalog and index every Profile again.

    Its own re-runnable profile rather than an upgrade step: drift is not
    tied to a version bump, and an operator who has just been handed a list of
    findings by :func:`~pas.plugins.identity.core.doctor.check` needs to be
    able to run this now and again next week.

    A profile rather than a site-wide import step, which is registered once
    for the whole site and runs during every add-on installation in it. That
    took a marker file in the profile directory and a guard reading it to stop
    an unrelated install from clearing a catalog that had nothing wrong with
    it; a profile simply does not run unless somebody applies it.

    :param context: The setup tool running the import.
    """
    catalog = query_catalog()
    if catalog is None:  # pragma: no cover - toolset.xml guarantees the tool
        return
    catalog.clearFindAndRebuild()


def post_uninstall(context: SetupTool) -> None:
    """Remove both PAS plugins; leave every Profile where it is.

    Uninstalling an add-on is a configuration change, not an instruction to
    delete everyone's account data, so the Profiles and their container stay.
    The same reasoning already governs provider deletion in the control panel.

    :param context: The setup tool running the import.
    """
    acl_users = _acl_users()
    uninstall_profile_plugin(acl_users)
    uninstall_plugin(acl_users)
    unregister_modifier(api.portal.get_tool("portal_modifier"))
    # The records naming the user and group types are removed declaratively,
    # by this profile's ``registry.xml``. Blanking them here as well would run
    # after they are already gone, and ``set_registry_record`` raises for a
    # record that does not exist.
    logger.info("Uninstalled pas.plugins.identity; Profile content was left in place.")
