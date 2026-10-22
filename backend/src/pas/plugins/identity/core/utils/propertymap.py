"""Turn a provider's claims into the fields a Profile carries.

A provider carries its own map of claim to Profile field, because providers do
not agree on names: GitHub says ``login`` where an OIDC provider says
``preferred_username``, and a Keycloak realm may publish anything its
administrator configured.

The *target* side of a map is any field of the site's user type --
:func:`mappable_fields` -- except the ones :data:`UNMAPPABLE_FIELDS` names, for
the reasons written against it. A behavior a site adds to its user type is
therefore a destination as soon as it is enabled: a claim that already has
the field's shape needs a row in the map, not an
:class:`~pas.plugins.identity.core.interfaces.IProfileEnricher`. The registry
field is a ``Choice`` over the vocabulary built from the same function, so a
row naming anything else is refused where it is written rather than ignored
where it is read.

A claim is addressed by a **dotted path**. Lookup tries the normalized claims
first and then the raw payload, so ``fullname`` reaches the value this
package already derived while ``address.formatted`` reaches into the
provider's own document. This is where the shape differs from
``pas.plugins.authomatic``, which nests the map itself
(``{"claim": {"property": "subkey"}}``); a path keeps the map flat, which is
what lets it be stored as a single typed registry record.
"""

from pas.plugins.identity.core.behaviors.details import IProfileDetails
from pas.plugins.identity.core.contents.profile import IUserProfileSchema
from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.principal_types import user_portal_type
from plone.dexterity.utils import iterSchemataForType
from typing import Any
from zope.schema import getFieldsInOrder
from zope.schema.interfaces import IField


#: Fields of the user type a property map may never write, whatever the type
#: declares.
#:
#: **The one definition.** Two things ask which fields a map may write: a
#: login, through :func:`~pas.plugins.identity.core.profiles.claim_fields`,
#: and the control panel, through the ``Choice`` over the vocabulary built
#: from :func:`mappable_fields`. Both read this set, so a map cannot express a
#: row that does nothing.
#:
#: **Why each is here.** ``userid`` is the join to the identity store and is
#: permanent. ``login`` is half of the case-folded index the enumeration
#: plugin queries, and a provider renaming somebody would move their account.
#: ``group_ids`` and ``global_roles`` are membership and roles, and a provider
#: that could edit them could grant itself both. ``email``, ``emails`` and the
#: portrait (``image``, or ``portrait`` on a site's own type) are excluded for
#: a different reason: they are handled, just not here --
#: :func:`~pas.plugins.identity.core.profiles.sync_addresses` appends
#: addresses without taking any away, and a portrait is synced from the
#: normalized ``picture_url`` claim with no map entry at all. ``id``,
#: ``changeNote`` and ``versioning_enabled`` belong to the ``plone.shortname``
#: and ``plone.versioning`` behaviors: they describe the object, not the
#: person.
UNMAPPABLE_FIELDS: frozenset[str] = frozenset({
    "changeNote",
    "email",
    "emails",
    "global_roles",
    "group_ids",
    "id",
    "image",
    "login",
    "portrait",
    "userid",
    "versioning_enabled",
})


#: The text fields of the shipped user type, which a map may always write.
#:
#: Always, because a site's own user type need not declare them as schema
#: fields to have them: a ``fullname`` computed from two name fields is a
#: property with a setter, and every provider's default map writes it. A type
#: that does declare one is validated against its own declaration.
PROFILE_TEXT_FIELDS: tuple[str, ...] = (
    "fullname",
    "home_page",
    "description",
    "location",
)


def _shipped_field(name: str) -> IField:
    """Return the shipped declaration of one of :data:`PROFILE_TEXT_FIELDS`.

    :param name: The field name.
    :returns: The field, from the Profile schema or the details behavior.
    """
    return IUserProfileSchema.get(name) or IProfileDetails[name]


def mappable_fields(portal_type: str = "") -> dict[str, IField]:
    """Return the fields of the user type a property map may write.

    Read from the *type* rather than from an object, so the control panel can
    answer before anybody has signed in: ``iterSchemataForType`` yields the
    FTI's own schema and then the schemata of every behavior it enables. A
    readonly field is left out, and so is every name in
    :data:`UNMAPPABLE_FIELDS`. :data:`PROFILE_TEXT_FIELDS` the type does not
    declare come last, with their shipped declaration.

    :param portal_type: The type to read. Empty means the site's user type.
    :returns: Field name to unbound field, in schema order. The first schema
        declaring a name wins, as it does on the object.
    """
    fields: dict[str, IField] = {}
    for schema in iterSchemataForType(portal_type or user_portal_type()):
        for name, field in getFieldsInOrder(schema):
            if name in fields or name in UNMAPPABLE_FIELDS or field.readonly:
                continue
            fields[name] = field
    for name in PROFILE_TEXT_FIELDS:
        if name not in fields:
            fields[name] = _shipped_field(name)
    return fields


def resolve_claim(path: str, claims: Claims) -> Any:
    """Read one claim by dotted path.

    The normalized claims win over the raw payload, so a map written against
    ``email`` gets the address this package lower-cased rather than whatever
    casing the provider sent.

    :param path: Dotted path, for example ``email`` or ``address.formatted``.
    :param claims: Normalized claims, including ``raw``.
    :returns: The value, or ``None`` when the path does not resolve.
    """
    if not path:
        return None
    for source in (claims, claims.get("raw") or {}):
        value: Any = source
        for segment in path.split("."):
            if not isinstance(value, dict) or segment not in value:
                value = None
                break
            value = value[segment]
        # A claim that is present but empty is not an answer: falling through
        # lets the raw payload supply it, which is what an operator mapping
        # ``fullname`` from a provider that leaves ``name`` blank expects.
        if value not in (None, "", [], {}):
            return value
    return None


def apply_property_map(propertymap: dict[str, str], claims: Claims) -> dict[str, Any]:
    """Resolve a whole map against one set of claims.

    Unresolvable claims are left out rather than written as empty: a provider
    that omits a claim must not blank the property it maps to.

    :param propertymap: Claim path to user field name.
    :param claims: Normalized claims, including ``raw``.
    :returns: User field name to value, for the claims that resolved.
    """
    resolved: dict[str, Any] = {}
    for path, field in propertymap.items():
        if not field:
            continue
        value = resolve_claim(path, claims)
        if value is not None:
            resolved[field] = value
    return resolved
