"""The registry records this package owns, as a schema.

Everything configurable lives under the ``pas.plugins.identity`` prefix, and
this interface is the single description of what each record is for. The
GenericSetup profile imports it -- see
``profiles/default/registry/pas.plugins.identity.core.controlpanel.interfaces.IIdentitySettings.xml``
-- and the control panel renders its form from it, so a record added here is
a record the site knows about everywhere.
"""

from pas.plugins.identity import _
from pas.plugins.identity.core.utils.svg import is_svg_upload
from plone.autoform import directives
from plone.restapi.controlpanels.interfaces import IControlpanel
from plone.supermodel import model
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
            "Portal type created when somebody adds a user. Installing this "
            "add-on points it at UserProfile; change it only to substitute a "
            "user type of your own. The type must provide IUserContent, and "
            "one that does not is refused rather than created -- adding a "
            "user then falls back to Plone's own source_users, which is "
            "stock behaviour rather than a failure. Empty does the same."
        ),
        required=False,
        default="",
    )

    user_container_path = schema.TextLine(
        title=_("User container path"),
        description=_(
            "Where those objects are created, as a path relative to the site "
            "root. Derived from the profile container settings and kept in "
            "step with them, so moving the container moves this. Required "
            "alongside the type: a type with nowhere to go would fail at the "
            "moment somebody adds a user, which is the worst time to "
            "discover a configuration gap."
        ),
        required=False,
        default="",
    )

    group_content_type = schema.TextLine(
        title=_("Group content type"),
        description=_(
            "Portal type created when somebody adds a group. Installing this "
            "add-on points it at UserGroup. The type must provide "
            "IGroupContent, and one that does not hands group creation back "
            "to Plone's own source_groups."
        ),
        required=False,
        default="",
    )

    group_container_path = schema.TextLine(
        title=_("Group container path"),
        description=_(
            "Where those objects are created, as a path relative to the "
            "site root. Derived and required alongside the type, for the "
            "reason the user container path is."
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


#: Fieldset the look of a login button is edited in.
STYLE_FIELDSET = "style"


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
    driver's ``settings_schema`` at runtime, and no fixed schema can describe a
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
            "Whether this provider can be used at all. A disabled provider "
            "keeps its settings and its stored identities, and nothing may "
            "sign in or link through it. Whether it is *offered* on the login "
            "screen is a separate setting."
        ),
        required=False,
        default=True,
    )

    show_in_login = schema.Bool(
        title=_("Show on the login screen"),
        description=_(
            "Whether the login screen offers a button for this provider. An "
            "enabled provider that is not shown still works: it stays "
            "linkable from a user's own identities page, and an account "
            "already linked to it still signs in through it. That is what a "
            "staff-only provider looks like -- usable, but not advertised to "
            "everybody who reaches the login form."
        ),
        required=False,
        default=True,
    )

    icon = schema.Bytes(
        title=_("Icon"),
        description=_(
            "An SVG file. Empty means no icon, and the frontend then draws "
            "the title alone rather than a placeholder every provider shares."
        ),
        required=False,
        constraint=is_svg_upload,
    )
    directives.widget("icon", frontendOptions={"widget": "provider_icon"})

    background_color = schema.TextLine(
        title=_("Background colour"),
        description=_(
            "The login button's background. Empty leaves the frontend's own "
            "styling alone."
        ),
        required=False,
        default="",
    )
    # directives.widget("background_color", frontendOptions={"widget": "color_picker"})

    foreground_color = schema.TextLine(
        title=_("Foreground colour"),
        description=_(
            "The login button's text and icon colour. Empty leaves the "
            "frontend's own styling alone."
        ),
        required=False,
        default="",
    )
    # directives.widget("foreground_color", frontendOptions={"widget": "color_picker"})

    model.fieldset(
        STYLE_FIELDSET,
        label=_("Style"),
        fields=["icon", "background_color", "foreground_color"],
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

    groupmap = schema.Dict(
        title=_("Group map"),
        description=_(
            "Provider-side group name to local group id, applied on every "
            "login. Empty by default: a provider grants no group until "
            "somebody says which of its groups mean something here, and a "
            "name with no entry grants nothing rather than creating a group. "
            "A login only ever takes back a group the same provider granted, "
            "so a group given to somebody by hand survives."
        ),
        key_type=schema.TextLine(title=_("Provider group")),
        value_type=schema.TextLine(title=_("Local group")),
        required=False,
        default={},
    )


class IProfileSettings(Interface):
    """Settings for the content objects that users and groups are.

    A second interface rather than more fields on :class:`IIdentitySettings`,
    and the split is by subject rather than by layer: these records say where
    principals are filed, which of their workflow states count, and what a
    profile must carry before its owner is let past the gate.

    Every record lives under the same ``pas.plugins.identity`` prefix as the
    rest, and this is the single description of what each one is for; the
    GenericSetup profile imports the schema rather than declaring the fields
    a second time.
    """

    profile_container_parent = schema.TextLine(
        title=_("Profile container parent"),
        description=_(
            "Path of the folder the profile container lives in, relative to "
            "the site root. Empty means the site root itself."
        ),
        required=False,
        default="",
    )

    profile_container_id = schema.TextLine(
        title=_("Profile container id"),
        description=_("Id of the folder holding user profiles."),
        required=False,
        default="identity-profiles",
    )

    profile_container_title = schema.TextLine(
        title=_("Profile container title"),
        description=_(
            "Title given to the profile container when this add-on creates "
            "it. Changing it later does not rename an existing folder."
        ),
        required=False,
        default="Identity Profiles",
    )

    profile_container_type = schema.TextLine(
        title=_("Profile container type"),
        description=_(
            "Portal type used when this add-on creates the profile container."
        ),
        required=False,
        default="Folder",
    )

    group_container_parent = schema.TextLine(
        title=_("Group container parent"),
        description=_(
            "Path of the folder the group container lives in, relative to "
            "the site root. Only read when a group container id is set."
        ),
        required=False,
        default="",
    )

    group_container_id = schema.TextLine(
        title=_("Group container id"),
        description=_(
            "Id of the folder holding groups. Empty means groups are filed "
            "with the profiles, which is what a site that has not thought "
            "about it wants."
        ),
        required=False,
        default="",
    )

    group_container_title = schema.TextLine(
        title=_("Group container title"),
        description=_(
            "Title given to the group container when this add-on creates it. "
            "Changing it later does not rename an existing folder."
        ),
        required=False,
        default="Groups",
    )

    group_container_type = schema.TextLine(
        title=_("Group container type"),
        description=_("Portal type used when this add-on creates the group container."),
        required=False,
        default="Folder",
    )

    profile_enumeration_states = schema.Tuple(
        title=_("Enumeration-active states"),
        description=_(
            "Profiles in these workflow states are visible to user "
            "enumeration and to the properties plugin."
        ),
        value_type=schema.TextLine(),
        required=False,
        default=("incomplete", "complete"),
    )

    gate_exempt_paths = schema.Tuple(
        title=_("Paths the profile gate leaves alone"),
        description=_(
            "Extra view names never redirected while a profile is "
            "incomplete, matched against the last segment of the path. The "
            "sign-in, sign-out and OAuth authorization endpoints are already "
            "exempt; this is for a browser-based flow another add-on "
            "publishes, which would otherwise be interrupted halfway."
        ),
        value_type=schema.TextLine(),
        required=False,
        default=(),
    )

    enforce_required_profile_fields = schema.Bool(
        title=_("Hold users on their profile until it is complete"),
        description=_(
            "While a profile is missing required information, every page its "
            "owner asks for is answered with a redirect to its edit form. "
            "Managers and site administrators are never held, so that a "
            "required field nobody can supply cannot lock the site. Turn "
            "this off to make the profile a suggestion rather than a gate."
        ),
        required=False,
        default=True,
    )

    required_profile_fields = schema.Tuple(
        title=_("Required profile fields"),
        description=_(
            "Fields a user must fill in before their profile counts as "
            "complete. Empty means the fields the profile type itself marks "
            "required, which is the right answer for a site that has not "
            "thought about it and for a site with its own user type. Naming "
            "a field here that the type does not require will keep asking "
            "for something the edit form does not insist on."
        ),
        value_type=schema.TextLine(),
        required=False,
        default=(),
    )

    group_enumeration_states = schema.Tuple(
        title=_("Enumeration-active group states"),
        description=_(
            "Groups in these workflow states are visible to group "
            "enumeration and grant membership."
        ),
        value_type=schema.TextLine(),
        required=False,
        default=("active",),
    )


class IIdentityControlpanel(IControlpanel):
    """Marker for this package's control panel."""
