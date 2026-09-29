"""The PAS plugins installed in this site.

Any plugin in ``acl_users``, not only this package's own: the lookup a
downstream package would otherwise write as
``api.portal.get_tool("acl_users")`` at every call site.
"""

from pas.plugins.identity.core.utils import plugins
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin


def get(name: str) -> BasePlugin | None:
    """Return a plugin by its id in ``acl_users``.

    :param name: The plugin's id.
    :returns: The plugin, or ``None`` when this site has no plugin by that id.
    """
    return plugins.get(name)


__all__ = [
    "get",
]
