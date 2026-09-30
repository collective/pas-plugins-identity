"""Take a site to profile version 1010.

``identity_profile`` now answers ``IUserIntrospection``, the question PAS asks
to list every user rather than to search for some. Without it
``api.user.get_users()``, ``portal_membership.listMembers()`` and
``acl_users.getUserIds()`` left out every user who has a Profile and no
``source_users`` row, which is every user who signed in through a provider,
while searches found them.

The class implements the interface on every site as soon as the code is
deployed. What a site installed earlier lacks is the activation, which lives
in ``acl_users/plugins`` and is written once, at install. Only that interface
is activated here: re-running the whole install handler would also move the
plugin to the top of ``IPropertiesPlugin``, undoing an order a site may have
chosen since.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.pas.profile import PLUGIN_ID
from plone import api
from Products.GenericSetup.tool import SetupTool
from Products.PlonePAS.interfaces.plugins import IUserIntrospection


def activate_user_introspection(context: SetupTool) -> None:
    """Activate ``identity_profile`` for ``IUserIntrospection``.

    :param context: The setup tool running the upgrade.
    """
    plugins = api.portal.get_tool("acl_users").plugins
    if PLUGIN_ID in plugins.listPluginIds(IUserIntrospection):
        return
    plugins.activatePlugin(IUserIntrospection, PLUGIN_ID)
    logger.info("Activated %s for IUserIntrospection", PLUGIN_ID)
