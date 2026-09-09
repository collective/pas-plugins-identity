"""What this server says about a user, and to whom.

The contract between an authorization server and its relying parties. A
relying party asks for scopes; this module turns the granted ones into the
claims they release.

**Where the answers come from.** One serializer per scope, registered as a
named adapter, in :mod:`~pas.plugins.identity.server.serializers`. This module
does not know what a scope releases and has no table of claims: it finds the
serializer for each granted scope, merges what they return, and applies the
two rules that must hold for every scope alike -- ``sub`` is minted here and
nowhere else, and a value this server does not have is omitted rather than
sent blank.

That split is what makes a downstream package able to add a claim, or a whole
scope, by registering an adapter rather than by mutating a dict in this
module at import time. See :doc:`/how-to-guides/serialize-a-claim`.

**The source of a value.** Claims are read from **Plone user properties**,
never from a Profile. That is what keeps the ``[server]`` layer independent of
where a user's fields are stored -- but it is also simply correct: the profile
plugin serves a Profile's fields *as* a property sheet through its
``IPropertiesPlugin``, so asking PAS for a property gets Profile-backed data
for a user who has one and stock ``mutable_properties`` data for a userid that
does not. The federation scenario looks like two hops -- provider to Profile,
Profile to the relying party's property sheet -- and is one, because both ends
already speak properties.

That rule binds the serializers this package ships. It does not bind anybody
else's: it exists so this layer works on a site without the profile layer
installed, which is not a constraint a downstream serializer is under.
"""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.server.serializers import declared_claims
from pas.plugins.identity.server.serializers import declared_scopes
from pas.plugins.identity.server.serializers import serializer_for
from plone import api


#: The scope every OIDC request carries. It releases nothing by itself: it
#: asks for an identity, and ``sub`` is not scope-gated. No serializer is
#: registered for it, which is why :func:`scopes` names it separately.
OPENID_SCOPE = "openid"

#: Claims this server sets itself, whatever a serializer returns under the
#: same name.
#:
#: ``sub`` is the join every relying party stores against its local account.
#: A serializer able to change it could silently re-identify every federated
#: user at every relying party, with nothing to migrate back from, so it is
#: minted in :func:`claims_for` and applied last. ``iss``, ``aud``, ``exp``
#: and ``iat`` are set when a token is signed -- see
#: :func:`~pas.plugins.identity.server.grants.tokens.mint_id_token`, which
#: spreads these claims and then sets those four over the top. That ordering
#: is deliberate rather than incidental, and this tuple is what says so.
RESERVED_CLAIMS = ("sub", "iss", "aud", "exp", "iat")


def scopes() -> list[str]:
    """Return every scope this server issues tokens for.

    :returns: ``openid`` first, then every scope a serializer is registered
        for, sorted. Byte-stable between requests, so a client that caches
        the discovery document and diffs on change sees a change only when
        one happened.
    """
    return [OPENID_SCOPE, *declared_scopes()]


def scope_claims(scope: str) -> tuple[str, ...]:
    """Return the claim names one scope declares.

    Read from the serializer's declaration rather than by serializing
    somebody, because this answers the consent screen and the discovery
    document -- both of which are asked with no user in hand, and neither of
    which may depend on who is signing in.

    :param scope: The scope name.
    :returns: Claim names, empty for a scope nothing is registered for.
    """
    return declared_claims(scope)


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
        for claim in scope_claims(requested):
            if claim not in names:
                names.append(claim)
    return names


def _has_value(value: object) -> bool:
    """Whether a claim value is worth releasing.

    Absence, not falsehood. OIDC asks that a claim the server has no value
    for be absent, so a relying party can tell "we do not know" from "it is
    blank" -- but ``email_verified`` is legitimately ``False``, and a rule
    that dropped falsy values would silently turn "this site checked and the
    address is unverified" into "this site said nothing".

    :param value: Whatever a serializer returned for the claim.
    :returns: Whether to include it.
    """
    return value not in (None, "", [], {})


def claims_for(userid: str, scope: str = "") -> JSONDict:
    """Return the claims to release about a user.

    :param userid: The Plone userid the token acts for.
    :param scope: Space-separated granted scopes.
    :returns: A claims mapping including ``sub``. Values this server does not
        have are omitted rather than sent as empty strings.
    """
    claims: JSONDict = {}
    user = api.user.get(userid=userid)
    if user is None:  # pragma: no cover - can't-happen: the Bearer plugin checked
        return {"sub": userid}

    seen: set[str] = set()
    for requested in scope.split():
        if requested in seen:
            continue
        seen.add(requested)
        serializer = serializer_for(requested)
        if serializer is None:
            continue
        for claim, value in serializer(user).items():
            if claim in RESERVED_CLAIMS:
                # Not an error worth failing a login over, and not something
                # to honour either: a serializer that returns `sub` is
                # ignored on that key and releases the rest.
                continue
            if _has_value(value):
                claims[claim] = value

    claims["sub"] = userid
    return claims
