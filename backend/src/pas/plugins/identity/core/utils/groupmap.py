"""Turning a provider's group claim into local group ids.

The counterpart of :mod:`pas.plugins.identity.core.utils.propertymap`, and it works
the same way: a per-provider mapping an operator edits, resolved against the
claims of the login that is happening. It is deliberately *not* on the driver.
A driver is one class shared by every provider using it -- two Keycloak realms
configured on one site are both ``oidc-generic`` -- so a mapping stored there
would be shared by providers that have nothing to do with each other. The
driver seeds a default; the provider owns the map.

Nothing here decides membership. It answers "which local groups is this
provider asking for", and :meth:`~pas.plugins.identity.core.pas.plugin.
IdentityPlugin._sync_federated_groups` decides what to do about it -- which is
where the rule that a provider may only take back what it granted lives.

An unmapped value is dropped, never auto-created. A group claim is whatever
the provider's own directory happens to be called, and minting local groups
from it would let anyone who can name a group at the far end create one here.
"""

from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.utils.propertymap import resolve_claim


#: The claim a driver reads groups from when it does not say otherwise.
#:
#: Not a registered OIDC claim. It is the name Keycloak, Okta and Entra all
#: use, and the one this package's own ``[server]`` layer releases.
DEFAULT_GROUP_CLAIM = "groups"


def claimed_groups(claim_path: str, claims: Claims) -> list[str]:
    """Read the group names a provider asserted, as strings.

    Providers disagree about the shape. A list of strings is the common case
    and what this package's own server emits; a single string is what a
    provider with one group per user sends. Anything else -- a list of
    objects, a number -- is ignored rather than coerced, because a group name
    invented by stringifying a payload matches nothing in the map anyway and
    a silent near-miss is worse than an absence.

    Values are stripped and deduplicated, order preserved, because the map is
    keyed on what an operator typed.

    :param claim_path: Dotted claim path, e.g. ``groups`` or ``realm.roles``.
    :param claims: Normalized claims, including ``raw``.
    :returns: The asserted group names.
    """
    value = resolve_claim(claim_path, claims)
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []

    seen: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        name = item.strip()
        if name and name not in seen:
            seen.append(name)
    return seen


def map_groups(groupmap: dict[str, str], names: list[str]) -> set[str]:
    """Resolve asserted group names to local group ids.

    :param groupmap: Provider-side group name to local group id.
    :param names: What the provider asserted, from :func:`claimed_groups`.
    :returns: The local group ids the provider is asking for. A name with no
        entry in the map contributes nothing; so does an entry mapped to an
        empty string, which is how the control panel represents a row an
        operator cleared without deleting.
    """
    return {
        local.strip() for name in names if (local := groupmap.get(name) or "").strip()
    }
