"""Install and uninstall of the ``server`` GenericSetup profile.

The only thing that cannot be done declaratively is the signing key: it has to
be generated, not shipped, or every site running this add-on would sign its
tokens with the same key as every other one.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.server.interfaces import IServerSettings
from pas.plugins.identity.server.utils.keys import ensure_keys
from pas.plugins.identity.server.pas import IdentityServerPlugin
from pas.plugins.identity.server.pas import PLUGIN_ID
from pas.plugins.identity.server.pas import PLUGIN_TITLE
from pas.plugins.identity.server.utils.session import IdentityAuthorizeSessionPlugin
from pas.plugins.identity.server.utils.session import PLUGIN_ID as SESSION_PLUGIN_ID
from pas.plugins.identity.server.utils.session import (
    PLUGIN_TITLE as SESSION_PLUGIN_TITLE,
)
from pas.plugins.identity.setuphandlers import register_settings
from plone import api
from Products.GenericSetup.tool import SetupTool
from Products.PluggableAuthService.interfaces.plugins import IAuthenticationPlugin
from Products.PluggableAuthService.interfaces.plugins import IExtractionPlugin
from Products.PluggableAuthService.PluggableAuthService import PluggableAuthService


#: PAS interfaces the plugin is activated for on install. ``IChallengePlugin``
#: is absent on purpose: a request that fails to authenticate here should fall
#: through to whatever the site already does, not be answered with
#: ``WWW-Authenticate: Bearer`` by an add-on that has decided the site is an
#: API.
ACTIVATED_INTERFACES = (
    IExtractionPlugin,
    IAuthenticationPlugin,
)


def post_install(context: SetupTool) -> None:
    """Generate a signing key if the site has none.

    Idempotent: re-applying the profile must not rotate the key underneath
    tokens that are still inside their lifetime. Rotation is a deliberate act
    from the control panel, never a side effect of reinstalling.

    :param context: The setup tool running the import.
    """
    register_settings(IServerSettings)
    keys = ensure_keys()
    install_plugin(api.portal.get_tool("acl_users"))
    install_session_plugin(api.portal.get_tool("acl_users"))
    logger.info(
        "Authorization server ready with %s signing key(s); active kid %s",
        len(keys),
        keys[0]["kid"],
    )


def install_plugin(acl_users: PluggableAuthService) -> IdentityServerPlugin:
    """Add the server plugin to PAS and activate its interfaces.

    Idempotent, and it does not reorder anything: extraction and
    authentication are a chain rather than a priority list, so this plugin
    sits wherever it lands and answers only for tokens it minted.

    :param acl_users: The site's PAS instance.
    :returns: The installed plugin.
    """
    if PLUGIN_ID not in acl_users:
        acl_users._setObject(PLUGIN_ID, IdentityServerPlugin(PLUGIN_ID, PLUGIN_TITLE))
        logger.info("Added %s plugin to acl_users", PLUGIN_ID)

    plugin = acl_users[PLUGIN_ID]
    plugins = acl_users.plugins
    for interface in ACTIVATED_INTERFACES:
        if PLUGIN_ID not in plugins.listPluginIds(interface):
            plugins.activatePlugin(interface, PLUGIN_ID)
    return plugin


def install_session_plugin(
    acl_users: PluggableAuthService,
) -> IdentityAuthorizeSessionPlugin:
    """Add the Volto-session plugin to PAS and activate its interfaces.

    Installed with the ``[server]`` layer because that is the layer that
    creates the authorization endpoint it exists for. A site with no
    authorization endpoint has nothing for this plugin to answer.

    :param acl_users: The site's PAS instance.
    :returns: The installed plugin.
    """
    if SESSION_PLUGIN_ID not in acl_users:
        acl_users._setObject(
            SESSION_PLUGIN_ID,
            IdentityAuthorizeSessionPlugin(SESSION_PLUGIN_ID, SESSION_PLUGIN_TITLE),
        )
        logger.info("Added %s plugin to acl_users", SESSION_PLUGIN_ID)

    plugin = acl_users[SESSION_PLUGIN_ID]
    plugins = acl_users.plugins
    for interface in ACTIVATED_INTERFACES:
        if SESSION_PLUGIN_ID not in plugins.listPluginIds(interface):
            plugins.activatePlugin(interface, SESSION_PLUGIN_ID)
    return plugin


def uninstall_session_plugin(acl_users: PluggableAuthService) -> None:
    """Deactivate and remove the Volto-session plugin.

    :param acl_users: The site's PAS instance.
    """
    if SESSION_PLUGIN_ID not in acl_users:
        return
    plugins = acl_users.plugins
    for info in plugins.listPluginTypeInfo():
        iface = info["interface"]
        if SESSION_PLUGIN_ID in plugins.listPluginIds(iface):
            plugins.deactivatePlugin(iface, SESSION_PLUGIN_ID)
    acl_users._delObject(SESSION_PLUGIN_ID)
    logger.info("Removed %s plugin from acl_users", SESSION_PLUGIN_ID)


def uninstall_plugin(acl_users: PluggableAuthService) -> None:
    """Deactivate and remove the server plugin.

    Every interface is deactivated, not only the ones install activates: a
    site that switched one on by hand in the ZMI must not be left with a
    registration pointing at an object that no longer exists.

    :param acl_users: The site's PAS instance.
    """
    if PLUGIN_ID not in acl_users:
        return
    plugins = acl_users.plugins
    for info in plugins.listPluginTypeInfo():
        iface = info["interface"]
        if PLUGIN_ID in plugins.listPluginIds(iface):
            plugins.deactivatePlugin(iface, PLUGIN_ID)
    acl_users._delObject(PLUGIN_ID)
    logger.info("Removed %s plugin from acl_users", PLUGIN_ID)


def post_uninstall(context: SetupTool) -> None:
    """Report what uninstalling leaves behind.

    The registry records go with ``registry.xml``, and that includes the key
    ring -- which is the point: a site that removes the authorization server
    should stop being able to sign as itself. Any token still in flight stops
    verifying, which is the correct outcome and worth saying out loud, because
    it is not recoverable by reinstalling.

    :param context: The setup tool running the import.
    """
    uninstall_plugin(api.portal.get_tool("acl_users"))
    uninstall_session_plugin(api.portal.get_tool("acl_users"))
    logger.info(
        "Authorization server uninstalled; the signing keys are gone and "
        "tokens minted with them will no longer verify"
    )
