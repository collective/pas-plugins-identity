"""The control panel entry for this package's settings.

The panel itself is rendered by the frontend, which drives the dedicated
``@identity-providers`` and ``@identity-drivers`` endpoints rather than the
generic registry form -- a provider's fields come from its driver, so there
is no fixed schema to render. What is registered here is the *entry*: without
it the panel exists but nothing links to it, and ``@controlpanels`` does not
list it.
"""

from pas.plugins.identity import _
from pas.plugins.identity.core.controlpanel.interfaces import IIdentityControlpanel
from pas.plugins.identity.core.controlpanel.interfaces import IIdentitySettings
from pas.plugins.identity.interfaces import IBrowserLayer
from plone.restapi.controlpanels import RegistryConfigletPanel
from zope.component import adapter
from zope.interface import implementer
from zope.interface import Interface


#: ``action_id`` of the configlet, and the name the panel is reachable under.
#: The frontend registers a route of the same name.
CONFIGLET_ID = "identity-providers"

#: Control panel category the configlet is filed under.
CONFIGLET_CATEGORY_ID = "plone-users"


@adapter(Interface, IBrowserLayer)
@implementer(IIdentityControlpanel)
class IdentityConfigletPanel(RegistryConfigletPanel):
    """Expose this package's settings through ``@controlpanels``."""

    schema = IIdentitySettings
    schema_prefix = "pas.plugins.identity"
    configlet_id = CONFIGLET_ID
    configlet_category_id = CONFIGLET_CATEGORY_ID
    title = _("Identity providers")
    group = ""
