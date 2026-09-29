"""Finding a PAS plugin in the current site.

One lookup instead of ``api.portal.get_tool("acl_users")`` spelled out at
every call site. It answers ``None`` for a plugin the site does not have,
because for several callers that is an ordinary state rather than a fault: a
site without ``plone.restapi``'s JWT plugin, or with this package's server
layer not installed. A caller that cannot proceed without the plugin says so
itself, where it knows what the absence means.

It lives in ``core`` so that every layer may use it. The public façade offers
the same function as ``api.plugin.get``, but nothing inside this package may
import the façade.
"""

from plone import api
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin


def get(plugin_id: str) -> BasePlugin | None:
    """Return a plugin from the current site's ``acl_users``.

    :param plugin_id: The plugin's id in ``acl_users``.
    :returns: The plugin, or ``None`` when the site has no plugin by that id.
    """
    return api.portal.get_tool("acl_users").get(plugin_id)
