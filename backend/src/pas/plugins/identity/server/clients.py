"""The OAuth client registry.

Clients live in a single registry record as a JSON list, the same shape the
provider configuration uses, which is what makes them GenericSetup-exportable
and importable.

The difference from a provider is the secret. A provider's client secret is
*masked* on the way out and can be echoed back unchanged, because this package
is the client and has to send it somewhere. Here this package is the server:
nothing ever needs the plaintext again, so S8 says store a hash. A secret is
returned exactly once, when it is minted, and is unrecoverable afterwards.
"""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.server.interfaces import ServerError
from plone import api

import hashlib
import hmac
import json
import secrets


#: Registry key holding the client list.
CLIENTS_RECORD = "pas.plugins.identity.server_clients"

#: Auth method of a client that has no secret. Public clients are the ones
#: PKCE is mandatory for (S8): a native or browser app cannot keep a secret,
#: so the proof of possession has to come from the exchange itself.
PUBLIC_AUTH_METHOD = "none"

#: scrypt parameters. Deliberately named rather than inlined, because they are
#: stored in each hash and must stay readable when they are changed later.
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SALT_BYTES = 16
_SECRET_BYTES = 32


def new_secret() -> str:
    """Mint a client secret.

    :returns: A URL-safe secret with 256 bits of entropy.
    """
    return secrets.token_urlsafe(_SECRET_BYTES)


def hash_secret(secret: str) -> str:
    """Hash a client secret for storage.

    :param secret: The plaintext secret.
    :returns: ``scrypt$n$r$p$salt$hash``, all hex where it is not decimal.
    """
    salt = secrets.token_bytes(_SALT_BYTES)
    derived = hashlib.scrypt(
        secret.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${derived.hex()}"


def verify_secret(secret: str, stored: str) -> bool:
    """Check a presented secret against a stored hash.

    The parameters come out of the stored value rather than the constants
    above, so hashes written before a parameter change keep verifying.

    :param secret: The plaintext secret as presented.
    :param stored: The stored ``scrypt$...`` value.
    :returns: Whether they match. A malformed or empty stored value is False,
        never an exception: this runs on the token endpoint, where a raised
        error would be a distinguishable answer.
    """
    try:
        scheme, n, r, p, salt, expected = stored.split("$")
        if scheme != "scrypt":
            return False
        derived = hashlib.scrypt(
            secret.encode("utf-8"),
            salt=bytes.fromhex(salt),
            n=int(n),
            r=int(r),
            p=int(p),
        )
    except (AttributeError, ValueError):
        return False
    return hmac.compare_digest(derived.hex(), expected)


class ClientConfig:
    """One registered OAuth client.

    :ivar client_id: Site-unique client id.
    :ivar title: Label shown to the user on the consent screen.
    :ivar redirect_uris: The exact URIs this client may be redirected to.
    :ivar grant_types: Grants this client may use.
    :ivar scope: Space-separated scopes the client may ask for.
    :ivar auth_method: Token-endpoint authentication method;
        :data:`PUBLIC_AUTH_METHOD` for a client with no secret.
    :ivar secret_hash: Stored hash of the client secret, empty for a public
        client.
    :ivar enabled: Whether the client may obtain tokens at all.
    """

    def __init__(
        self,
        client_id: str,
        title: str = "",
        redirect_uris: list[str] | None = None,
        grant_types: list[str] | None = None,
        scope: str = "",
        auth_method: str = PUBLIC_AUTH_METHOD,
        secret_hash: str = "",
        enabled: bool = True,
    ) -> None:
        """Build a client registration.

        :param client_id: Site-unique client id.
        :param title: Label for the consent screen.
        :param redirect_uris: Exact redirect URIs.
        :param grant_types: Grants this client may use.
        :param scope: Space-separated scopes.
        :param auth_method: Token-endpoint auth method.
        :param secret_hash: Stored secret hash.
        :param enabled: Whether the client is usable.
        """
        self.client_id = client_id
        self.title = title
        self.redirect_uris = redirect_uris or []
        self.grant_types = grant_types or ["authorization_code"]
        self.scope = scope
        self.auth_method = auth_method
        self.secret_hash = secret_hash
        self.enabled = enabled

    @property
    def is_public(self) -> bool:
        """Whether this client authenticates with no secret.

        :returns: True for a public client.
        """
        return self.auth_method == PUBLIC_AUTH_METHOD

    @property
    def requires_pkce(self) -> bool:
        """Whether PKCE is mandatory for this client (S8).

        Public clients must use it. Confidential ones are not forced to here,
        because a client that authenticates at the token endpoint already
        proves possession; the authorization endpoint still accepts PKCE from
        them and will enforce it once offered.

        :returns: Whether the authorization endpoint must refuse a request
            from this client that carries no code challenge.
        """
        return self.is_public

    def check_redirect_uri(self, uri: str) -> bool:
        """Whether a redirect URI is registered for this client.

        Exact string comparison, per S8. No prefix matching, no ignoring the
        query string, no treating a trailing slash as equivalent: every one of
        those has been an open-redirect in somebody's authorization server.

        :param uri: The redirect URI as presented.
        :returns: Whether it is registered.
        """
        return uri in self.redirect_uris

    def check_secret(self, secret: str) -> bool:
        """Whether a presented client secret is correct.

        :param secret: The plaintext secret as presented.
        :returns: Whether it matches. Always False for a public client -- one
            has no secret, so presenting any is wrong.
        """
        if self.is_public or not self.secret_hash:
            return False
        return verify_secret(secret, self.secret_hash)

    def allows_grant(self, grant_type: str) -> bool:
        """Whether this client may use a grant.

        :param grant_type: The requested grant type.
        :returns: Whether it is registered for this client.
        """
        return grant_type in self.grant_types

    def scopes(self) -> set[str]:
        """Return the scopes this client may ask for.

        :returns: The scope string split on whitespace.
        """
        return set(self.scope.split())

    def serialize(self, include_hash: bool = False) -> JSONDict:
        """Render the client for storage or for an API response.

        :param include_hash: Whether to include the stored secret hash. True
            only when writing back to the registry. A hash is not a secret,
            but publishing one invites an offline attack on a value the site
            owner cannot rotate without breaking the client.
        :returns: JSON-ready mapping.
        """
        data: JSONDict = {
            "client_id": self.client_id,
            "title": self.title,
            "redirect_uris": list(self.redirect_uris),
            "grant_types": list(self.grant_types),
            "scope": self.scope,
            "auth_method": self.auth_method,
            "public": self.is_public,
            "enabled": self.enabled,
        }
        if include_hash:
            data["secret_hash"] = self.secret_hash
        return data

    @classmethod
    def deserialize(cls, data: JSONDict) -> "ClientConfig":
        """Build a client from its stored representation.

        :param data: Mapping as produced by :meth:`serialize`.
        :returns: The client registration.
        """
        return cls(
            client_id=data["client_id"],
            title=data.get("title", ""),
            redirect_uris=list(data.get("redirect_uris", [])),
            grant_types=list(data.get("grant_types", ["authorization_code"])),
            scope=data.get("scope", ""),
            auth_method=data.get("auth_method", PUBLIC_AUTH_METHOD),
            secret_hash=data.get("secret_hash", ""),
            enabled=data.get("enabled", True),
        )

    def __repr__(self) -> str:
        """Return a debugging representation.

        :returns: Client id and whether it is public.
        """
        kind = "public" if self.is_public else "confidential"
        return f"<ClientConfig {self.client_id} ({kind})>"


def get_clients() -> list[ClientConfig]:
    """Return every registered client, enabled or not.

    :returns: Clients in registry order.
    """
    raw = api.portal.get_registry_record(CLIENTS_RECORD, default="") or ""
    if not raw:
        return []
    return [ClientConfig.deserialize(entry) for entry in json.loads(raw)]


def get_client(client_id: str) -> ClientConfig | None:
    """Return one registered client.

    :param client_id: The client id.
    :returns: The client, or ``None`` when it is not registered.
    """
    for client in get_clients():
        if client.client_id == client_id:
            return client
    return None


def set_clients(clients: list[ClientConfig]) -> None:
    """Replace the stored client list.

    :param clients: The clients to store.
    """
    payload = [c.serialize(include_hash=True) for c in clients]
    api.portal.set_registry_record(CLIENTS_RECORD, json.dumps(payload))


def add_client(
    client_id: str,
    title: str = "",
    redirect_uris: list[str] | None = None,
    grant_types: list[str] | None = None,
    scope: str = "",
    public: bool = False,
) -> tuple[ClientConfig, str]:
    """Register a client, minting a secret for a confidential one.

    :param client_id: Site-unique client id.
    :param title: Label for the consent screen.
    :param redirect_uris: Exact redirect URIs.
    :param grant_types: Grants this client may use.
    :param scope: Space-separated scopes.
    :param public: Whether the client authenticates with no secret.
    :returns: The stored client and its plaintext secret. The secret is empty
        for a public client, and this is the only time it exists: it is hashed
        on the way in and cannot be read back.
    :raises ServerError: When the client id is already registered. Silently
        replacing one would re-point every token minted for it.
    """
    if get_client(client_id) is not None:
        raise ServerError(f"Client {client_id!r} is already registered")

    secret = "" if public else new_secret()
    client = ClientConfig(
        client_id=client_id,
        title=title,
        redirect_uris=redirect_uris,
        grant_types=grant_types,
        scope=scope,
        auth_method=PUBLIC_AUTH_METHOD if public else "client_secret_post",
        secret_hash="" if public else hash_secret(secret),
    )
    set_clients([*get_clients(), client])
    return client, secret


def rotate_secret(client_id: str) -> str:
    """Mint a fresh secret for a client, discarding the old one.

    :param client_id: The client id.
    :returns: The new plaintext secret, which is not recoverable afterwards.
    :raises ServerError: When the client is unknown or is public.
    """
    clients = get_clients()
    for client in clients:
        if client.client_id != client_id:
            continue
        if client.is_public:
            raise ServerError(f"Client {client_id!r} is public and has no secret")
        secret = new_secret()
        client.secret_hash = hash_secret(secret)
        set_clients(clients)
        return secret
    raise ServerError(f"Client {client_id!r} is not registered")


def remove_client(client_id: str) -> None:
    """Unregister a client.

    :param client_id: The client id.
    :raises ServerError: When the client is not registered.
    """
    clients = get_clients()
    remaining = [c for c in clients if c.client_id != client_id]
    if len(remaining) == len(clients):
        raise ServerError(f"Client {client_id!r} is not registered")
    set_clients(remaining)


def authenticate(client_id: str, secret: str) -> ClientConfig | None:
    """Authenticate a confidential client at the token endpoint.

    An unknown client and a wrong secret must not be distinguishable, so an
    unknown id still pays for a hash computation rather than returning early.

    :param client_id: The presented client id.
    :param secret: The presented secret.
    :returns: The client, or ``None`` when authentication fails for any
        reason -- unknown, disabled, public, or wrong secret.
    """
    client = get_client(client_id)
    if client is None:
        # Burn the same work an unknown id would have skipped.
        verify_secret(secret, hash_secret("decoy"))
        return None
    if not client.enabled or not client.check_secret(secret):
        return None
    return client
