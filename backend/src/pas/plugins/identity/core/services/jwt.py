"""Minting the token Volto logs in with.

Both ways into the site -- the provider callback and a magic link -- end by
handing the browser a ``jwt_auth`` token, so the minting lives here rather
than once per service.
"""

from pas.plugins.identity.core.interfaces import PrincipalUnavailable
from plone import api
from Products.PluggableAuthService.interfaces.plugins import IAuthenticationPlugin


#: ``meta_type`` of the plugin that mints Volto's tokens.
JWT_PLUGIN_META_TYPE = "JWT Authentication Plugin"


def mint_token(userid: str) -> str | None:
    """Mint a ``jwt_auth`` token for a userid.

    Two different failures, and they are not the same answer. No JWT plugin
    means Volto could not have logged anybody in by any route, and the caller
    is owed a 501. A userid that resolves to nothing means the login worked
    and the account it names does not exist -- a site whose users are content
    where nothing created the object -- and reporting that as a missing JWT
    plugin sends whoever reads it to the wrong control panel.

    :param userid: Canonical Plone userid.
    :returns: The encoded token, or ``None`` when the site has no JWT plugin.
    :raises PrincipalUnavailable: When no account can be resolved for
        *userid*. Raised rather than returned so it cannot be mistaken for
        the other case, and because dereferencing the ``None`` is what used
        to happen: ``AttributeError: 'NoneType' object has no attribute
        'getId'``, from a traceback naming neither the user nor the reason.
    """
    acl_users = api.portal.get_tool("acl_users")
    for _id, plugin in acl_users.plugins.listPlugins(IAuthenticationPlugin):
        if plugin.meta_type == JWT_PLUGIN_META_TYPE:
            user = acl_users.getUserById(userid)
            if user is None:
                raise PrincipalUnavailable(
                    f"Authenticated {userid!r}, and this site has no account "
                    f"for it: nothing created the user record. On a site that "
                    f"keeps its users as content, that is the content object."
                )
            return plugin.create_token(
                user.getId(), data={"fullname": user.getProperty("fullname", "")}
            )
    return None
