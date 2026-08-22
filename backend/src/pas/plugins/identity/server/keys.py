"""The authorization server's signing keys.

Deliberately *not* the derivation :mod:`pas.plugins.identity.core.flows.session`
uses. That one is symmetric and derived from Plone's own keyring, which is
right for a cookie or a magic link: this site signs them and this site is the
only thing that ever verifies them.

Tokens minted here are verified by somebody else -- a relying party that must
not be handed a signing secret. So the server keeps an asymmetric key ring and
publishes only the public halves, as a JWKS.

The ring is ordered, newest first, the same convention ``signing_keys()`` uses
in core. Index 0 signs; every key in the ring verifies, which is what lets a
rotation happen without invalidating tokens that are still inside their
lifetime.
"""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.server.interfaces import ServerError
from plone import api

import json


#: Registry key holding the private key ring, newest first.
KEYS_RECORD = "pas.plugins.identity.server_signing_keys"

#: Signature algorithm. RS256 rather than something smaller because the
#: audience is off-the-shelf relying parties, and it is the one algorithm
#: every OIDC client library implements.
ALGORITHM = "RS256"

#: Key size for a newly generated key.
KEY_SIZE = 2048

#: How many keys the ring holds. One signs; the rest are kept only so tokens
#: minted before a rotation still verify. Access tokens live fifteen minutes
#: (D3), so two spares is already generous, and an unbounded ring would grow a
#: registry record forever.
RING_SIZE = 3


def generate_key() -> JSONDict:
    """Mint a signing key.

    :returns: A private JWK, including the ``kid`` authlib derives for it.
    """
    from authlib.jose import JsonWebKey

    key = JsonWebKey.generate_key("RSA", KEY_SIZE, is_private=True)
    return key.as_dict(is_private=True)


def get_keys() -> list[JSONDict]:
    """Return the private key ring, newest first.

    :returns: Private JWKs; empty when the server has never generated any.
    """
    raw = api.portal.get_registry_record(KEYS_RECORD, default="") or ""
    if not raw:
        return []
    return json.loads(raw)


def set_keys(keys: list[JSONDict]) -> None:
    """Replace the private key ring.

    :param keys: Private JWKs, newest first.
    """
    api.portal.set_registry_record(KEYS_RECORD, json.dumps(keys))


def ensure_keys() -> list[JSONDict]:
    """Generate a key if the ring is empty, and return the ring.

    Called from the ``server`` profile's install step, and idempotent so that
    re-running the profile does not rotate the key underneath live tokens.

    :returns: The key ring, newest first.
    """
    keys = get_keys()
    if not keys:
        keys = [generate_key()]
        set_keys(keys)
    return keys


def current_key() -> JSONDict:
    """Return the key to sign with.

    :returns: The newest private JWK.
    :raises ServerError: When the ring is empty, which means the ``server``
        profile was never applied. Signing with a key generated on the spot
        would produce tokens nothing could verify a request later.
    """
    keys = get_keys()
    if not keys:
        raise ServerError(
            "The authorization server has no signing key; apply the "
            "'server' GenericSetup profile"
        )
    return keys[0]


def rotate_keys() -> JSONDict:
    """Mint a new signing key, retiring the oldest.

    The previous keys stay in the ring so that tokens already issued keep
    verifying until they expire.

    :returns: The new private JWK.
    """
    keys = [generate_key(), *get_keys()][:RING_SIZE]
    set_keys(keys)
    return keys[0]


def public_jwks() -> JSONDict:
    """Return the public half of the ring, as a JWKS.

    Every key is published, not only the signing one: a relying party that
    cached a token minted before the last rotation still has to be able to
    verify it.

    :returns: ``{"keys": [...]}``, safe to publish.
    """
    from authlib.jose import JsonWebKey

    return {
        "keys": [
            JsonWebKey.import_key(key).as_dict(is_private=False) for key in get_keys()
        ]
    }


def key_set():
    """Return the ring as an authlib key set, for verification.

    :returns: A ``KeySet`` authlib can pick the right ``kid`` out of.
    :raises ServerError: When the ring is empty.
    """
    from authlib.jose import JsonWebKey

    jwks = public_jwks()
    if not jwks["keys"]:
        raise ServerError(
            "The authorization server has no signing key; apply the "
            "'server' GenericSetup profile"
        )
    return JsonWebKey.import_key_set(jwks)
