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

Two claims released here are not registered OIDC claims: ``description`` and
``groups``. Both are emitted under ``profile`` rather than under a private
scope, because both are read by name elsewhere -- ``groups`` is what
Keycloak, Okta and Entra all call it -- and a namespaced claim only this
server's own peers would understand buys nothing but a second thing to
configure. A relying party that does not know a claim ignores it.

That is the whole of the extension, and it is not a general one: a site with
fields of its own still has no standard claim to put them in, and inventing
one per site would produce something no other implementation can read.

``groups`` riding on ``profile`` is a deliberate trade and worth naming.
``profile`` is granted for display, and group membership is authorization
data, so every relying party asking for a display scope receives it whether
it maps groups or not. What the server controls is the *content*: see
:data:`UNRELEASED_GROUPS`.
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
#: Every registered claim, plus the two unregistered ones the module docstring
#: accounts for. ``description`` -- Plone's free-text biography -- and
#: ``groups`` both ride on ``profile``: they are the same kind of thing the
#: rest of that scope is, and a relying party that does not know a name
#: ignores an unrecognised claim.
SCOPE_CLAIMS: dict[str, tuple[str, ...]] = {
    "profile": (
        "name",
        "preferred_username",
        "website",
        "picture",
        "description",
        "groups",
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
    "groups": lambda user: released_groups(user),
    "preferred_username": lambda user: user.getUserName(),
    "website": lambda user: user.getProperty("home_page", ""),
    "email": lambda user: user.getProperty("email", ""),
    "address": lambda user: user.getProperty("location", ""),
    "picture": lambda user: portrait_url(user.getId()),
    "description": lambda user: user.getProperty("description", ""),
}


#: Group ids this server never puts in a ``groups`` claim.
#:
#: ``AuthenticatedUsers`` is PAS's virtual group: every principal with a
#: session is in it, so it says nothing about anybody. Releasing it would
#: also be actively harmful at the far end, where a relying party that
#: mapped it would hand its local counterpart to every federated user.
UNRELEASED_GROUPS = frozenset({"AuthenticatedUsers"})


def released_groups(user) -> list[str]:
    """Return the group ids to release for a user.

    ``PropertiedUser.getGroups`` is what PAS resolved for this principal, so
    it already includes groups reached through another plugin and through
    nesting -- which is the answer a relying party wants, rather than the
    memberships one plugin happens to hold.

    Sorted, because a claim that reorders between two logins looks like a
    change to anything diffing tokens.

    :param user: The Plone user the token acts for.
    :returns: Group ids, sorted, minus :data:`UNRELEASED_GROUPS`.
    """
    return sorted(set(user.getGroups()) - UNRELEASED_GROUPS)


def portrait_url(userid: str) -> str:
    """Return the public URL of a user's portrait, or nothing.

    Only when a portrait is actually stored. Plone's
    ``getPersonalPortrait`` falls back to a default image, and publishing a
    ``picture`` claim that every user shares would tell a relying party that
    everybody uploaded the same photograph.

    Which store holds it is not this layer's business, so the question goes
    to :func:`pas.plugins.identity.core.portraits.has_picture`, which asks
    both. Asking ``portal_memberdata`` directly was correct only while every
    avatar landed there; once a site's Profiles started winning, this
    returned an empty string for users who plainly had a picture and the
    claim was dropped without a word.

    The URL is always ``@portrait``, whichever store answers. It is a public
    endpoint by design -- a relying party fetches it server to server with no
    credentials -- and it does not disclose where a Profile lives.

    Under ``++api++``, which is not decoration. ``@portrait`` is a
    ``plone.restapi`` service, and ``plone.rest`` only takes over traversal
    for a request that asks for JSON: published bare, the URL answered 404
    for every client that did not claim to want a JSON document -- our own
    fetcher, any relying party that is not a Plone site, and a browser
    rendering the claim in an ``<img>``. The namespace is what makes the URL
    resolve for all of them, and it is already public on any site that serves
    a REST API at all.

    Built from the configured issuer rather than from the portal URL, for the
    reason the issuer is configured at all: the portal URL is whatever the
    request came in on, and this URL is handed to another site to fetch.

    :param userid: Canonical Plone userid.
    :returns: An absolute URL, or an empty string.
    """
    from pas.plugins.identity.core.portraits import has_picture
    from pas.plugins.identity.server.tokens import ISSUER_RECORD

    if not has_picture(userid):
        return ""

    issuer = (api.portal.get_registry_record(ISSUER_RECORD, default="") or "").strip()
    if not issuer:
        return ""
    return f"{issuer.rstrip('/')}/++api++/@portrait/{quote(userid)}"


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
