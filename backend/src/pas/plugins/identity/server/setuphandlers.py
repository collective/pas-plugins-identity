"""Install and uninstall of the ``server`` GenericSetup profile.

The only thing that cannot be done declaratively is the signing key: it has to
be generated, not shipped, or every site running this add-on would sign its
tokens with the same key as every other one.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.server.keys import ensure_keys
from pas.plugins.identity.server.pas import IdentityServerPlugin
from pas.plugins.identity.server.pas import PLUGIN_ID
from pas.plugins.identity.server.pas import PLUGIN_TITLE
from plone import api
from Products.GenericSetup.tool import SetupTool
from Products.PluggableAuthService.PluggableAuthService import PluggableAuthService


def post_install(context: SetupTool) -> None:
    """Generate a signing key if the site has none.

    Idempotent: re-applying the profile must not rotate the key underneath
    tokens that are still inside their lifetime. Rotation is a deliberate act
    from the control panel, never a side effect of reinstalling.

    :param context: The setup tool running the import.
    """
    keys = ensure_keys()
    install_plugin(api.portal.get_tool("acl_users"))
    logger.info(
        "Authorization server ready with %s signing key(s); active kid %s",
        len(keys),
        keys[0]["kid"],
    )


def install_plugin(acl_users: PluggableAuthService) -> IdentityServerPlugin:
    """Add the server plugin to PAS.

    No interfaces are activated: the plugin is a persistent home for the
    authorization codes and nothing asks it anything yet. Bearer validation
    is what will activate them.

    :param acl_users: The site's PAS instance.
    :returns: The installed plugin.
    """
    if PLUGIN_ID not in acl_users:
        acl_users._setObject(PLUGIN_ID, IdentityServerPlugin(PLUGIN_ID, PLUGIN_TITLE))
        logger.info("Added %s plugin to acl_users", PLUGIN_ID)
    return acl_users[PLUGIN_ID]


def uninstall_plugin(acl_users: PluggableAuthService) -> None:
    """Remove the server plugin.

    No interfaces are deactivated first, because none are activated: this
    plugin is a persistent home and answers nothing. The deactivation loop
    belongs with the Bearer interfaces, and arrives when they do.

    :param acl_users: The site's PAS instance.
    """
    if PLUGIN_ID not in acl_users:
        return
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
    logger.info(
        "Authorization server uninstalled; the signing keys are gone and "
        "tokens minted with them will no longer verify"
    )
