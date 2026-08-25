"""What this server says about a user, and to whom.

The contract between an authorization server and its relying parties. A
relying party asks for scopes; this module decides which claims that releases
and where their values come from.

The important design decision is the source. Claims are read from **Plone user
properties**, never from a Profile. That is what keeps the ``[server]`` layer
independent of the ``[profile]`` layer, which the import-linter contract
requires -- but it is also simply correct: the profile layer serves its fields
*as* a property sheet through its ``IPropertiesPlugin``, so asking PAS for a
property gets Profile-backed data on a site that installed that layer and
stock ``mutable_properties`` data on one that did not. The federation scenario
looks like two hops -- provider to Profile, Profile to the relying party's
property sheet -- and is one, because both ends already speak properties.

Only registered OIDC claims are emitted. A site with fields of its own has no
standard claim to put them in, and inventing one would produce something no
other implementation can read; the extension point is a private scope, and it
is deliberately not built until somebody needs it.
"""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.pas import PLUGIN_ID as CORE_PLUGIN_ID
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from plone import api
from urllib.parse import quote


#: The scope every OIDC request carries. It releases nothing by itself: it
#: asks for an identity, and ``sub`` is not scope-gated.
OPENID_SCOPE = "openid"

#: Scope to the claims it releases.
#:
#: All registered claims but one. ``description`` -- Plone's free-text
#: biography -- has no registered claim to be, and is released under
#: ``profile`` anyway rather than under a private scope of its own: it is the
#: same kind of thing the rest of that scope is, a relying party that does not
#: know the name ignores an unrecognised claim, and a scope only this server's
#: own peers would ever ask for buys nothing but a second thing to configure.
SCOPE_CLAIMS: dict[str, tuple[str, ...]] = {
    "profile": (
        "name",
        "preferred_username",
        "website",
        "picture",
        "description",
    ),
    "email": ("email", "email_verified"),
    "address": ("address",),
}

#: Claim to where its value comes from. One table rather than a property map
#: plus a branch per computed claim: every value then passes the same
#: emptiness test on the way out, and "omit what we do not know" is enforced
#: in one place instead of being remembered four times.
#:
#: ``email_verified`` is deliberately absent -- it is a statement *about*
#: another claim rather than a value of its own, and is added afterwards.
CLAIM_SOURCES = {
    "name": lambda user: user.getProperty("fullname", ""),
    "preferred_username": lambda user: user.getUserName(),
    "website": lambda user: user.getProperty("home_page", ""),
    "email": lambda user: user.getProperty("email", ""),
    "address": lambda user: user.getProperty("location", ""),
    "picture": lambda user: portrait_url(user.getId()),
    "description": lambda user: user.getProperty("description", ""),
}


def portrait_url(userid: str) -> str:
    """Return the public URL of a user's portrait, or nothing.

    Only when a portrait is actually stored. Plone's
    ``getPersonalPortrait`` falls back to a default image, and publishing a
    ``picture`` claim that every user shares would tell a relying party that
    everybody uploaded the same photograph.

    Built from the configured issuer rather than from the portal URL, for the
    reason the issuer is configured at all: the portal URL is whatever the
    request came in on, and this URL is handed to another site to fetch.

    :param userid: Canonical Plone userid.
    :returns: An absolute URL, or an empty string.
    """
    from pas.plugins.identity.server.tokens import ISSUER_RECORD

    memberdata = api.portal.get_tool("portal_memberdata")
    membership = api.portal.get_tool("portal_membership")
    if memberdata._getPortrait(membership._getSafeMemberId(userid)) is None:
        return ""

    issuer = (api.portal.get_registry_record(ISSUER_RECORD, default="") or "").strip()
    if not issuer:
        return ""
    return f"{issuer.rstrip('/')}/@portrait/{quote(userid)}"


def released(scope: str) -> list[str]:
    """Return the claims a scope string releases.

    :param scope: Space-separated scopes as requested.
    :returns: Claim names, deduplicated, in a stable order. Unknown scopes
        release nothing rather than raising: the authorization endpoint has
        already refused any scope the client is not registered for, so an
        unknown one here is a site that removed a scope from a registration
        after a token was issued, and quietly releasing less is right.
    """
    names: list[str] = []
    for requested in scope.split():
        for claim in SCOPE_CLAIMS.get(requested, ()):
            if claim not in names:
                names.append(claim)
    return names


def email_is_verified(userid: str, address: str) -> bool:
    """Whether *this site* verified that address for that user.

    Not whether some provider said so. The whole of this package's
    auto-linking discipline rests on refusing a provider's word for a verified
    address, and emitting ``email_verified: true`` on that basis would export
    the problem: a relying party auto-linking on this claim would be trusting
    a chain this server has already decided not to trust.

    True means the user proved the address to this site with a magic link,
    which is recorded as an ``email`` identity whose subject is the address.

    :param userid: The Plone userid.
    :param address: The address being asserted.
    :returns: Whether it is verified.
    """
    plugin = api.portal.get_tool("acl_users").get(CORE_PLUGIN_ID)
    if plugin is None:  # pragma: no cover - can't-happen: core is always installed
        return False
    return any(
        record.provider == EMAIL_PROVIDER and record.subject == address.strip().lower()
        for record in plugin.store.identities_for(userid)
    )


def claims_for(userid: str, scope: str = "") -> JSONDict:
    """Return the claims to release about a user.

    :param userid: The Plone userid the token acts for.
    :param scope: Space-separated granted scopes.
    :returns: A claims mapping including ``sub``. Empty values are omitted
        rather than sent as empty strings: OIDC asks that a claim the server
        has no value for be absent, and a relying party can then tell "we do
        not know" from "it is blank".
    """
    claims: JSONDict = {"sub": userid}
    user = api.user.get(userid=userid)
    if user is None:  # pragma: no cover - can't-happen: the Bearer plugin checked
        return claims

    names = released(scope)
    for claim in names:
        source = CLAIM_SOURCES.get(claim)
        if source is None:
            continue
        value = source(user) or ""
        if value:
            claims[claim] = value

    if "address" in claims:
        # Plone's `location` is one free-text line, which is exactly what the
        # `formatted` member of the OIDC address claim is for. Splitting it
        # into street, locality and postal code would be guessing.
        claims["address"] = {"formatted": claims["address"]}

    if "email_verified" in names and "email" in claims:
        # Only alongside an address. `email_verified` with no `email` is a
        # claim about nothing, and OIDC readers differ on what to do with it.
        claims["email_verified"] = email_is_verified(userid, claims["email"])

    return claims
