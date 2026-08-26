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
    the provider is -- see :mod:`pas.plugins.identity.core.controlpanel` and
    :class:`IProviderRecords`.
    """

    callback_url = schema.TextLine(
        title=_("Login callback URL"),
        description=_(
            "The frontend route the provider redirects to after login. A "
            "path such as /login-identity is resolved against this site's "
            "URL and is what most deployments want. Give an absolute URL "
            "instead when the frontend is served from another origin, "
            "since no portal URL can describe one Plone is never reached "
            "on. It is a route in the frontend rather than a backend view: "
            "the frontend reads code and state off the query string and "
            "posts them to @identity-callback. Either way it must match "
            "the redirect URI registered with every provider exactly."
        ),
        required=False,
        default="/login-identity",
    )

    user_content_type = schema.TextLine(
        title=_("User content type"),
        description=_(
            "Portal type created when somebody adds a user, on a site that "
            "keeps its users as content. Empty -- the default -- means this "
            "package adds no users and Plone's own source_users does it, "
            "exactly as before. The type must provide IUserContent, and one "
            "that does not is refused rather than created."
        ),
        required=False,
        default="",
    )

    user_container_path = schema.TextLine(
        title=_("User container path"),
        description=_(
            "Where those objects are created, as a path relative to the "
            "site root. Required alongside the type: a type with nowhere to "
            "go would fail at the moment somebody adds a user, which is the "
            "worst time to discover a configuration gap."
        ),
        required=False,
        default="",
    )

    group_content_type = schema.TextLine(
        title=_("Group content type"),
        description=_(
            "Portal type created when somebody adds a group, on a site that "
            "keeps its groups as content. Empty -- the default -- means "
            "Plone's own source_groups does it, exactly as before. The type "
            "must provide IGroupContent."
        ),
        required=False,
        default="",
    )

    group_container_path = schema.TextLine(
        title=_("Group container path"),
        description=_(
            "Where those objects are created, as a path relative to the "
            "site root. Required alongside the type, for the reason the "
            "user container path is."
        ),
        required=False,
        default="",
    )

    sync_portraits = schema.Bool(
        title=_("Copy provider avatars into portrait storage"),
        description=_(
            "Off by default. When on, a changed picture_url claim is "
            "fetched over HTTPS on login and stored as the user's "
            "portrait. The URL is a claim, so at many providers it is "
            "whatever the user typed: enabling this makes the login path "
            "fetch an address the user chose. See the documentation before "
            "turning it on."
        ),
        required=False,
        default=False,
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


class IProviderRecords(Interface):
    """The fields every provider has, whatever its driver.

    Registered once per provider, under
    ``pas.plugins.identity.providers.<id>`` as the prefix, so the records are
    ordinary interface-bound records rather than loose ones. That is what lets
    a profile declare a provider with a single ``<records interface=... />``
    node instead of restating a field type per record:

    .. code-block:: xml

        <records
            interface="pas.plugins.identity.core.controlpanel
                       .interfaces.IProviderRecords"
            prefix="pas.plugins.identity.providers.github"
        >
          <value key="driver">github</value>
          <value key="enabled">True</value>
        </records>

    (the interface name is one unbroken string in a real profile; it is
    wrapped here only to fit.)

    The driver's *configuration* records -- ``config.client_id`` and the rest
    -- stay outside any interface and keep carrying their own field type. They
    have to: which of them exist, and what type each one is, comes from the
    driver's ``config_schema`` at runtime, and no fixed schema can describe a
    set of fields that is chosen after the schema was written.
    """

    driver = schema.TextLine(
        title=_("Driver"),
        description=_("Id of the driver that talks to this provider."),
        required=False,
        default="",
    )

    title = schema.TextLine(
        title=_("Title"),
        description=_("Shown on the login button."),
        required=False,
        default="",
    )

    enabled = schema.Bool(
        title=_("Enabled"),
        description=_(
            "A disabled provider keeps its settings and its stored identities."
        ),
        required=False,
        default=True,
    )

    order = schema.Int(
        title=_("Order"),
        description=_(
            "Position among the providers. Stored rather than derived: "
            "records live in a BTree and read back alphabetically, and this "
            "is the order the login buttons appear in."
        ),
        required=False,
        default=0,
    )

    propertymap = schema.Dict(
        title=_("Property map"),
        description=_(
            "Claim path to Plone user field, applied on every login. One "
            "record rather than one per row: the keys are claim paths an "
            "operator types, so a record each would mean creating and "
            "deleting records as the map is edited."
        ),
        key_type=schema.TextLine(title=_("Claim")),
        value_type=schema.TextLine(title=_("User field")),
        required=False,
        default={},
    )


class IIdentityControlpanel(IControlpanel):
    """Marker for this package's control panel."""
