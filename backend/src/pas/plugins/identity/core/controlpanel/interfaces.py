"""The registry records this package owns, as a schema.

Everything configurable lives under the ``pas.plugins.identity`` prefix, and
this interface is the single description of what each record is for. The
GenericSetup profile imports it -- see
``profiles/default/registry/pas.plugins.identity.core.controlpanel.interfaces.IIdentitySettings.xml``
-- and the control panel renders its form from it, so a record added here is
a record the site knows about everywhere.
"""

from pas.plugins.identity import _
from plone.restapi.controlpanels.interfaces import IControlpanel
from zope import schema
from zope.interface import Interface


class IIdentitySettings(Interface):
    """Site-wide settings for external identity providers.

    Providers themselves are *not* declared here. Each one owns a set of
    records named ``pas.plugins.identity.providers.<id>.<field>``, created as
    the provider is -- see :mod:`pas.plugins.identity.core.controlpanel`. A
    fixed schema could not describe them: which config records exist depends
    on the driver.
    """

    callback_url = schema.TextLine(
        title=_("Login callback URL"),
        description=_(
            "Absolute URL of the frontend route the provider redirects to "
            "after login, for example https://example.com/login-identity. "
            "It is a route in the frontend rather than a backend view: the "
            "frontend reads code and state off the query string and posts "
            "them to @identity-callback. It must match the redirect URI "
            "registered with every provider exactly, which is why it is "
            "configured rather than derived from the portal URL."
        ),
        required=False,
        default="",
    )

    audit_max_entries = schema.Int(
        title=_("Audit entries kept per user"),
        description=_("Older entries are dropped once a user passes this many."),
        required=False,
        default=500,
    )

    audit_max_days = schema.Int(
        title=_("Audit retention in days"),
        description=_("Entries older than this are dropped."),
        required=False,
        default=180,
    )

    audit_record_pii = schema.Bool(
        title=_("Record IP address and user agent"),
        description=_(
            "Off by default. Enabling this stores personal data; see the "
            "privacy notes in the documentation."
        ),
        required=False,
        default=False,
    )


class IIdentityControlpanel(IControlpanel):
    """Marker for this package's control panel."""
