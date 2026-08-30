"""The control panel entry for the authorization server.

The panel itself is rendered by the frontend against ``@identity-clients`` and
``@identity-keys``. What is registered here is the *entry*: without it the
panel exists but nothing links to it and ``@controlpanels`` does not list it.

Registered against the ``[server]`` browser layer, so it appears only in a
site that switched the authorization server on. A control panel for managing
OAuth clients on a site that issues no tokens would be a menu item leading to
an empty page and a question.
"""

from pas.plugins.identity import _
from pas.plugins.identity.server.interfaces import IIdentityServerLayer
from pas.plugins.identity.server.interfaces import IServerSettings
from plone.restapi.controlpanels import RegistryConfigletPanel
from plone.restapi.controlpanels.interfaces import IControlpanel
from zope.component import adapter
from zope.interface import implementer
from zope.interface import Interface


#: ``action_id`` of the configlet, and the name the panel is reachable under.
#: The frontend registers a route of the same name.
CONFIGLET_ID = "identity-clients"

#: Control panel category the configlet is filed under. The same one the
#: provider panel uses: an operator looking for "who may sign in here" and
#: "who may sign in to us" is looking in one place.
CONFIGLET_CATEGORY_ID = "plone-users"


class IIdentityServerControlpanel(IControlpanel):
    """Marker for the authorization server's control panel."""


@adapter(Interface, IIdentityServerLayer)
@implementer(IIdentityServerControlpanel)
class IdentityServerConfigletPanel(RegistryConfigletPanel):
    """Expose the server settings through ``@controlpanels``."""

    schema = IServerSettings
    schema_prefix = "pas.plugins.identity"
    configlet_id = CONFIGLET_ID
    configlet_category_id = CONFIGLET_CATEGORY_ID
    title = _("OAuth clients")
    group = ""
