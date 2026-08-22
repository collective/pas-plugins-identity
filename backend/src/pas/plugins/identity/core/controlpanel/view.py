"""A Classic UI form for the identity settings.

The panel people are meant to use is the frontend one: it builds a form per
provider out of that provider's driver schema, which no fixed schema can do.
This form is the plain fallback -- a registry edit form over
:class:`~pas.plugins.identity.core.controlpanel.interfaces.IIdentitySettings`
-- so that a site without the frontend, or an operator already in the ZMI, has
somewhere to go. It is also what the configlet's URL points at, so the entry
in the Classic control panel leads to a real page rather than a 404.
"""

from pas.plugins.identity import _
from pas.plugins.identity.core.controlpanel.interfaces import IIdentitySettings
from plone.app.registry.browser import controlpanel


class IdentitySettingsForm(controlpanel.RegistryEditForm):
    """Edit the identity settings as plain registry records."""

    schema = IIdentitySettings
    schema_prefix = "pas.plugins.identity"
    label = _("Identity providers")
    description = _(
        "Site-wide settings for external identity providers. The provider "
        "list is stored as JSON; the frontend control panel edits it one "
        "provider at a time, with a form generated from each driver."
    )


class IdentitySettingsControlPanel(controlpanel.ControlPanelFormWrapper):
    """Wrap the form in the standard control panel chrome."""

    form = IdentitySettingsForm
