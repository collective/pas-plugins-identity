"""The control panel entry for this package's settings.

The panel itself is rendered by the frontend, which drives the dedicated
``@identity-providers`` and ``@identity-drivers`` endpoints rather than the
generic registry form -- a provider's fields come from its driver, so there
is no fixed schema to render. What is registered here is the *entry*: without
it the panel exists but nothing links to it, and ``@controlpanels`` does not
list it.
"""

from pas.plugins.identity import _
from pas.plugins.identity import logger
from pas.plugins.identity.core.controlpanel.interfaces import IIdentityControlpanel
from pas.plugins.identity.core.controlpanel.interfaces import IProfileSettings
from pas.plugins.identity.core.controlpanel.interfaces import panel_schema
from pas.plugins.identity.core.principal_types import users_as_content
from pas.plugins.identity.interfaces import IBrowserLayer
from plone.registry.interfaces import IRegistry
from plone.restapi.controlpanels import RegistryConfigletPanel
from zope.component import adapter
from zope.component import getUtility
from zope.interface import implementer
from zope.interface import Interface


#: ``action_id`` of the configlet, and the name the panel is reachable under.
#: The frontend registers a route of the same name.
CONFIGLET_ID = "identity-providers"

#: Control panel category the configlet is filed under.
CONFIGLET_CATEGORY_ID = "plone-users"

#: Where every setting this panel serves lives in the registry.
SCHEMA_PREFIX = "pas.plugins.identity"


def served_schema() -> type[Interface]:
    """Return the schema the panel serves on this site.

    The Profile settings are served where the site keeps its users as
    content *and* holds a record for every one of them. The marker alone is
    not enough: a panel names every field of its schema, and one field
    without a record fails the whole panel with a ``KeyError`` -- the REST
    panel, the classic form, and with them every other setting on it. That
    is the state of a site marked and missing records, which a registry step
    gone wrong or a hand-edited registry can produce.

    Such a site gets the panel a site without Profiles gets, so the settings
    it does have stay editable, and the log says what to do about the rest.
    Nothing is written to fix it here: a panel being read is not where a
    site's registry gets changed.

    :returns: The panel schema.
    """
    if not users_as_content():
        return panel_schema(False)
    registry = getUtility(IRegistry)
    try:
        registry.forInterface(IProfileSettings, prefix=SCHEMA_PREFIX, check=True)
    except KeyError as error:
        logger.warning(
            "This site keeps its users as content but lacks a Profile setting "
            "(%s), so the Identity providers panel leaves the Profile settings "
            "out. Reapply the registry step of pas.plugins.identity:contenttypes "
            "to restore them.",
            error,
        )
        return panel_schema(False)
    return panel_schema(True)


@adapter(Interface, IBrowserLayer)
@implementer(IIdentityControlpanel)
class IdentityConfigletPanel(RegistryConfigletPanel):
    """Expose this package's settings through ``@controlpanels``."""

    schema_prefix = SCHEMA_PREFIX
    configlet_id = CONFIGLET_ID
    configlet_category_id = CONFIGLET_CATEGORY_ID
    title = _("Identity providers")
    group = ""

    @property
    def schema(self) -> type[Interface]:
        """Return the settings this site has records for.

        A property rather than a class attribute, because the answer depends
        on the site: the Profile settings are on the panel only where the
        ``contenttypes`` profile created them. The frontend renders whatever
        schema it is served, so it follows without knowing why. Which schema
        that is: :func:`served_schema`.

        :returns: The panel schema.
        """
        return served_schema()
