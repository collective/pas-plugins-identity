"""Minting the token Volto logs in with.

Both ways into the site -- the provider callback and a magic link -- end by
handing the browser a ``jwt_auth`` token, so the minting lives here rather
than once per service.
"""

from plone import api
from Products.PluggableAuthService.interfaces.plugins import IAuthenticationPlugin


#: ``meta_type`` of the plugin that mints Volto's tokens.
JWT_PLUGIN_META_TYPE = "JWT Authentication Plugin"


def mint_token(userid: str) -> str | None:
    """Mint a ``jwt_auth`` token for a userid.

    :param userid: Canonical Plone userid.
    :returns: The encoded token, or ``None`` when the site has no JWT plugin
        -- in which case Volto could not have logged anybody in by any route,
        and the caller is owed a 501 rather than a traceback.
    """
    acl_users = api.portal.get_tool("acl_users")
    for _id, plugin in acl_users.plugins.listPlugins(IAuthenticationPlugin):
        if plugin.meta_type == JWT_PLUGIN_META_TYPE:
            user = acl_users.getUserById(userid)
            return plugin.create_token(
                user.getId(), data={"fullname": user.getProperty("fullname", "")}
            )
    return None
