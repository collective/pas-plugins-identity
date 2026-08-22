"""GenericSetup handlers.

Every profile here has a matching uninstall profile, and uninstall is tested
: install -> uninstall leaves no plugin behind and the site still works.
"""

from pas.plugins.identity import logger
from pas.plugins.identity import PACKAGE_NAME
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.core.pas import PLUGIN_TITLE
from pas.plugins.identity.core.pas.plugin import IdentityPlugin
from plone import api
from plone.base.interfaces.installable import INonInstallable
from Products.GenericSetup.tool import SetupTool
from Products.PluggableAuthService.interfaces.plugins import IAuthenticationPlugin
from Products.PluggableAuthService.interfaces.plugins import ICredentialsResetPlugin
from Products.PluggableAuthService.interfaces.plugins import IExtractionPlugin
from Products.PluggableAuthService.PluggableAuthService import PluggableAuthService
from zope.interface import implementer


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
    install_plugin(_acl_users())


def post_uninstall(context: SetupTool) -> None:
    """Remove the PAS plugin when the add-on is uninstalled.

    :param context: The setup tool running the import.
    """
    uninstall_plugin(_acl_users())
