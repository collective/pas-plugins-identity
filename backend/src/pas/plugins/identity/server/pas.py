"""The authorization server's PAS plugin.

Right now this plugin authenticates nothing. It exists because the
authorization codes need a persistent home, and every other persistent store
in this package lives on a PAS plugin -- the identity store, the magic-link
burn list and the audit log all sit on the core one. Putting the codes in a
site annotation instead would be the only such store in the package, and
reaching into core's plugin from here would cross the layer boundary the
import-linter contract exists to keep.

Bearer token validation arrives on this same plugin and is what will activate
its PAS interfaces. Until then the plugin is deliberately registered with none:
a plugin that claims an interface it does not yet implement would be asked to
answer, and answering nothing is not the same as not being asked.
"""

from AccessControl.class_init import InitializeClass
from pas.plugins.identity.server.codes import AuthorizationCodeStore
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin


#: Id of the plugin in ``acl_users``.
PLUGIN_ID = "identity_server"

#: Label shown in the ZMI.
PLUGIN_TITLE = "Identity: authorization server"


class IdentityServerPlugin(BasePlugin):
    """Persistent home for the authorization server's state."""

    meta_type = "Identity Server Plugin"

    def __init__(self, id: str = PLUGIN_ID, title: str = PLUGIN_TITLE) -> None:
        """Create the plugin and its stores.

        :param id: Plugin id.
        :param title: Label for the ZMI.
        """
        self._setId(id)
        self.title = title
        self._codes = AuthorizationCodeStore()

    @property
    def codes(self) -> AuthorizationCodeStore:
        """Return the authorization code store.

        Created on demand as well as in ``__init__`` so that a plugin
        persisted before this attribute existed keeps working: the alternative
        is an upgrade step for a store whose contents are worthless after
        sixty seconds anyway.

        :returns: The store.
        """
        store = getattr(self, "_codes", None)
        if store is None:
            store = self._codes = AuthorizationCodeStore()
        return store


InitializeClass(IdentityServerPlugin)
