"""Adding this package's two PAS plugins to ``acl_users``.

Two, and they stay two. ``identity`` authenticates: it extracts credentials,
signs a person in, adds a user, manages groups. ``identity_profile`` serves
what a signed-in person *is*: their property sheet, their place in the user
and group enumerations. The interfaces barely overlap, and a single plugin
claiming all of them would be one object whose two halves are activated,
ordered and reasoned about separately anyway.

Both are installed by the same profile now, and neither is optional.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.core.pas import PLUGIN_TITLE
from pas.plugins.identity.core.pas.plugin import IdentityPlugin
from pas.plugins.identity.core.pas.profile import IdentityProfilePlugin
from pas.plugins.identity.core.pas.profile import PLUGIN_ID as PROFILE_PLUGIN_ID
from pas.plugins.identity.core.pas.profile import PLUGIN_TITLE as PROFILE_PLUGIN_TITLE
from Products.PlonePAS.interfaces.group import IGroupIntrospection
from Products.PlonePAS.interfaces.group import IGroupManagement
from Products.PlonePAS.interfaces.plugins import IUserManagement
from Products.PluggableAuthService.interfaces.plugins import IAuthenticationPlugin
from Products.PluggableAuthService.interfaces.plugins import ICredentialsResetPlugin
from Products.PluggableAuthService.interfaces.plugins import IExtractionPlugin
from Products.PluggableAuthService.interfaces.plugins import IGroupEnumerationPlugin
from Products.PluggableAuthService.interfaces.plugins import IGroupsPlugin
from Products.PluggableAuthService.interfaces.plugins import IPropertiesPlugin
from Products.PluggableAuthService.interfaces.plugins import IUserAdderPlugin
from Products.PluggableAuthService.interfaces.plugins import IUserEnumerationPlugin
from Products.PluggableAuthService.PluggableAuthService import PluggableAuthService


#: PAS interfaces the identity plugin is activated for on install.
#: ``IChallengePlugin`` is deliberately absent -- it is opt-in.
#:
#: ``IGroupManagement`` is PlonePAS's rather than PAS's -- there is no
#: ``IGroupAdderPlugin`` -- but PlonePAS registers it as a plugin type, so it
#: activates the same way.
ACTIVATED_INTERFACES = (
    IExtractionPlugin,
    IAuthenticationPlugin,
    ICredentialsResetPlugin,
    IUserAdderPlugin,
    IGroupManagement,
)

#: Interfaces where being asked *first* is the whole point, so the plugin is
#: moved to the top of each on install.
#:
#: Both work by refusal: PAS and PlonePAS walk their plugins and stop at the
#: first that returns true, and this plugin declines for anything it does not
#: own. Registered below ``source_users`` or ``source_groups`` it would never
#: be reached, because those never decline -- and the failure is silent. Every
#: unit test calling the plugin directly still passes while the feature does
#: nothing through ``api.user.create``, which is how this was found.
FIRST_REFUSAL_INTERFACES = (
    IUserAdderPlugin,
    IGroupManagement,
)

#: PAS interfaces the profile plugin is activated for. Properties,
#: enumeration and deletion: authentication stays in the other plugin, and
#: this one never becomes a way to log in.
#:
#: ``IUserManagement`` is PlonePAS's, and it is here because the object *is*
#: the account. Without it ``api.user.delete`` removed whatever
#: ``source_users`` held -- nothing, for a user who signed in through a
#: provider -- and left the Profile answering enumeration and serving
#: properties, so the user was not deleted and nothing said so.
PROFILE_ACTIVATED_INTERFACES = (
    IPropertiesPlugin,
    IUserEnumerationPlugin,
    IGroupsPlugin,
    IGroupEnumerationPlugin,
    IGroupIntrospection,
    IUserManagement,
)


def _activate(
    acl_users: PluggableAuthService,
    plugin_id: str,
    interfaces: tuple,
) -> None:
    """Activate a plugin for each interface it does not already serve.

    :param acl_users: The site's PAS instance.
    :param plugin_id: Id of the plugin in ``acl_users``.
    :param interfaces: Plugin interfaces to activate it for.
    """
    plugins = acl_users.plugins
    for interface in interfaces:
        if plugin_id not in plugins.listPluginIds(interface):
            plugins.activatePlugin(interface, plugin_id)


def _remove(acl_users: PluggableAuthService, plugin_id: str) -> None:
    """Deactivate a plugin everywhere and delete it.

    :param acl_users: The site's PAS instance.
    :param plugin_id: Id of the plugin in ``acl_users``.
    """
    if plugin_id not in acl_users:
        return
    plugins = acl_users.plugins
    for interface in plugins.listPluginTypeInfo():
        iface = interface["interface"]
        if plugin_id in plugins.listPluginIds(iface):
            plugins.deactivatePlugin(iface, plugin_id)
    acl_users._delObject(plugin_id)
    logger.info("Removed %s plugin from acl_users", plugin_id)


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
    _activate(acl_users, PLUGIN_ID, ACTIVATED_INTERFACES)
    for interface in FIRST_REFUSAL_INTERFACES:
        acl_users.plugins.movePluginsTop(interface, [PLUGIN_ID])
    return plugin


def uninstall_plugin(acl_users: PluggableAuthService) -> None:
    """Deactivate and remove the identity plugin.

    :param acl_users: The site's PAS instance.
    """
    _remove(acl_users, PLUGIN_ID)


def install_profile_plugin(
    acl_users: PluggableAuthService,
) -> IdentityProfilePlugin:
    """Add the profile plugin to PAS and activate its interfaces.

    Idempotent, and it moves the plugin to the top of ``IPropertiesPlugin``.
    That ordering is load-bearing rather than cosmetic: Plone resolves a member
    property by taking the first sheet that *has* it, so below
    ``mutable_properties`` the Profile would never be read at all and the
    plugin would look installed while doing nothing.

    :param acl_users: The site's PAS instance.
    :returns: The installed plugin.
    """
    if PROFILE_PLUGIN_ID not in acl_users:
        acl_users._setObject(
            PROFILE_PLUGIN_ID,
            IdentityProfilePlugin(PROFILE_PLUGIN_ID, PROFILE_PLUGIN_TITLE),
        )
        logger.info("Added %s plugin to acl_users", PROFILE_PLUGIN_ID)

    plugin = acl_users[PROFILE_PLUGIN_ID]
    _activate(acl_users, PROFILE_PLUGIN_ID, PROFILE_ACTIVATED_INTERFACES)
    acl_users.plugins.movePluginsTop(IPropertiesPlugin, [PROFILE_PLUGIN_ID])
    return plugin


def uninstall_profile_plugin(acl_users: PluggableAuthService) -> None:
    """Deactivate and remove the profile plugin.

    :param acl_users: The site's PAS instance.
    """
    _remove(acl_users, PROFILE_PLUGIN_ID)


__all__ = [
    "ACTIVATED_INTERFACES",
    "FIRST_REFUSAL_INTERFACES",
    "PROFILE_ACTIVATED_INTERFACES",
    "install_plugin",
    "install_profile_plugin",
    "uninstall_plugin",
    "uninstall_profile_plugin",
]
