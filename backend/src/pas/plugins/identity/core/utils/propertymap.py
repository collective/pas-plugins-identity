"""Turn a provider's claims into the fields a Profile carries.

A provider carries its own map of claim to Profile field, because providers do
not agree on names: GitHub says ``login`` where an OIDC provider says
``preferred_username``, and a Keycloak realm may publish anything its
administrator configured.

The *target* side of a map is a closed set -- :data:`MAPPABLE_FIELDS` -- for
the reasons written against it. A row naming anything else used to be stored
and then dropped on every login without a word; the field is now a ``Choice``
over the vocabulary built from that tuple, so such a row is refused where it
is written rather than ignored where it is read.

A claim is addressed by a **dotted path**. Lookup tries the normalized claims
first and then the raw payload, so ``fullname`` reaches the value this
package already derived while ``address.formatted`` reaches into the
provider's own document. This is where the shape differs from
``pas.plugins.authomatic``, which nests the map itself
(``{"claim": {"property": "subkey"}}``); a path keeps the map flat, which is
what lets it be stored as a single typed registry record.
"""

from pas.plugins.identity.core.interfaces import Claims
from typing import Any


#: The Profile fields a property map may write, in the order a form shows them.
#:
#: **The one definition.** Three things ask this question and used to answer it
#: separately: a login, through
#: :data:`~pas.plugins.identity.core.subscribers.WRITABLE_FIELDS`; a principal
#: document, through
#: :data:`~pas.plugins.identity.exportimport.schema.USER_FIELDS`; and the
#: control panel, which asked nothing at all and took free text. Both of the
#: first two are now this tuple, and the third is a ``Choice`` over the
#: vocabulary built from it, so a map cannot express a row that does nothing.
#:
#: **What is not here, and why.** ``userid`` is the join to the identity store
#: and is permanent. ``login`` is half of the case-folded index the enumeration
#: plugin queries, and a provider renaming somebody would move their account.
#: ``group_ids`` is membership, and a provider that could edit it could grant
#: itself roles. ``email`` and the portrait are excluded for a different
#: reason: they are handled, just not here --
#: :func:`~pas.plugins.identity.core.subscribers.sync_addresses` appends
#: addresses without taking any away, and a portrait is synced from the
#: normalized ``picture_url`` claim with no map entry at all.
#:
#: Anything else a deployment wants written is a
#: :class:`~pas.plugins.identity.core.interfaces.IProfileEnricher`. A map
#: carries one scalar to one field; that is the whole of what it can do.
MAPPABLE_FIELDS: tuple[str, ...] = (
    "fullname",
    "home_page",
    "description",
    "location",
)


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
