"""GenericSetup handlers.

Every profile here has a matching uninstall profile, and uninstall is tested
: install -> uninstall leaves no plugin behind and the site still works.
"""

from pas.plugins.identity import logger
from pas.plugins.identity import PACKAGE_NAME
from pas.plugins.identity.core.controlpanel.interfaces import IIdentitySettings
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.core.pas import PLUGIN_TITLE
from pas.plugins.identity.core.pas.plugin import IdentityPlugin
from plone import api
from plone.base.interfaces.installable import INonInstallable
from plone.registry.interfaces import IRegistry
from Products.GenericSetup.tool import SetupTool
from Products.PluggableAuthService.interfaces.plugins import IAuthenticationPlugin
from Products.PluggableAuthService.interfaces.plugins import ICredentialsResetPlugin
from Products.PluggableAuthService.interfaces.plugins import IExtractionPlugin
from Products.PluggableAuthService.PluggableAuthService import PluggableAuthService
from zope.component import getUtility
from zope.interface import implementer
from zope.interface import Interface


#: PAS interfaces the plugin is activated for on install. ``IChallengePlugin``
#: is deliberately absent -- it is opt-in.
ACTIVATED_INTERFACES = (
    IExtractionPlugin,
    IAuthenticationPlugin,
    ICredentialsResetPlugin,
)


@implementer(INonInstallable)
class HiddenProfiles:
    """Keep helper profiles out of the add-ons control panel."""

    def getNonInstallableProfiles(self) -> list[str]:
        """Hide the uninstall profiles.

        :returns: Profile ids to hide.
        """
        return [
            f"{PACKAGE_NAME}:uninstall",
            f"{PACKAGE_NAME}:uninstall-profile",
            f"{PACKAGE_NAME}:uninstall-server",
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


def register_settings(interface: type[Interface]) -> None:
    """Create registry records for every field of a settings interface.

    Called from each layer's ``post_install``, which makes a re-install
    self-healing: a field added to the interface since the site was set up
    gets its record, with its schema default, without an upgrade step.

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


def install_plugin(acl_users: PluggableAuthService) -> IdentityPlugin:
    """Add the identity plugin to PAS and activate its interfaces.

    Idempotent: re-running against a site that already has the plugin
    activates any interface that is missing and returns the existing object,
    so its identity store survives a profile re-import.

    :param acl_users: The site's PAS instance.
    :returns: The installed plugin.
    """
    if PLUGIN_ID not in acl_users:
        acl_users._setObject(PLUGIN_ID, IdentityPlugin(PLUGIN_ID, PLUGIN_TITLE))
        logger.info("Added %s plugin to acl_users", PLUGIN_ID)

    plugin = acl_users[PLUGIN_ID]
    plugins = acl_users.plugins
    for interface in ACTIVATED_INTERFACES:
        if PLUGIN_ID not in plugins.listPluginIds(interface):
            plugins.activatePlugin(interface, PLUGIN_ID)
    return plugin


def uninstall_plugin(acl_users: PluggableAuthService) -> None:
    """Deactivate and remove the identity plugin.

    :param acl_users: The site's PAS instance.
    """
    if PLUGIN_ID not in acl_users:
        return
    plugins = acl_users.plugins
    for interface in plugins.listPluginTypeInfo():
        iface = interface["interface"]
        if PLUGIN_ID in plugins.listPluginIds(iface):
            plugins.deactivatePlugin(iface, PLUGIN_ID)
    acl_users._delObject(PLUGIN_ID)
    logger.info("Removed %s plugin from acl_users", PLUGIN_ID)


def post_install(context: SetupTool) -> None:
    """Install the PAS plugin after the ``default`` profile is imported.

    :param context: The setup tool running the import.
    """
    register_settings(IIdentitySettings)
    install_plugin(_acl_users())


def post_uninstall(context: SetupTool) -> None:
    """Remove the PAS plugin when the add-on is uninstalled.

    :param context: The setup tool running the import.
    """
    uninstall_plugin(_acl_users())
