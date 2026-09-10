"""What this site releases about a person, when it is the provider.

Part of the ``[server]`` layer: meaningful only where this Plone site is the
authorization server other applications sign in against. Importing this module
on a site without the extra is safe -- it costs nothing until a function is
called -- which is the property the leaf contract exists to keep true.

Scopes are the unit. A relying party asks in scopes, a person consents in
scopes, and one serializer answers for each. Registering your own is a named
adapter implementing
:class:`~pas.plugins.identity.server.interfaces.IScopeSerializer`.
"""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.server.claims import claims_for
from pas.plugins.identity.server.claims import released
from pas.plugins.identity.server.claims import scopes as _scopes
from pas.plugins.identity.server.serializers import declared_claims
from pas.plugins.identity.server.serializers import declared_scopes


def get(userid: str, scope: str = "") -> JSONDict:
    """Return the claims this server releases about a user.

    :param userid: Canonical Plone userid.
    :param scope: The granted scope string, space-separated as it arrives on
        the wire. Empty releases only what every token carries.
    :returns: JSON-ready claims, with ``sub`` set to the userid. A claim
        nobody has a value for is absent rather than null -- but a claim whose
        value is ``False`` is present, because absence and falsity are
        different answers.
    """
    return claims_for(userid, scope)


def get_scopes() -> list[str]:
    """Return every scope this server will release claims for.

    :returns: The scope names, which is what the discovery document publishes
        as ``scopes_supported``.
    """
    return _scopes()


def get_released(scope: str) -> list[str]:
    """Return the claim names one scope releases.

    Answered with no user in hand, because the discovery document and the
    consent screen both have to ask it before anybody has signed in. A scope
    whose claims cannot be enumerated would tell somebody they are releasing
    less than they are.

    :param scope: A single scope name.
    :returns: The claim names, empty when nothing serializes that scope.
    """
    return released(scope)


__all__ = [
    "declared_claims",
    "declared_scopes",
    "get",
    "get_released",
    "get_scopes",
]
