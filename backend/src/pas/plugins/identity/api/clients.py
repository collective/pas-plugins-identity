"""The OAuth clients registered against this site.

Part of the ``[server]`` layer, and the one namespace here whose operations
raise rather than answer ``None``: registering a client that already exists,
or rotating the secret of one that does not, is a caller mistake with no
sensible empty answer. Lookups still return ``None``.

A minted secret is returned once and hashed on the way in. It cannot be read
back afterwards -- not by this module, not by the control panel, not from the
registry.
"""

from pas.plugins.identity.server.controlpanel.clients import add_client
from pas.plugins.identity.server.controlpanel.clients import authenticate
from pas.plugins.identity.server.controlpanel.clients import ClientConfig
from pas.plugins.identity.server.controlpanel.clients import get_client
from pas.plugins.identity.server.controlpanel.clients import get_clients
from pas.plugins.identity.server.controlpanel.clients import remove_client
from pas.plugins.identity.server.controlpanel.clients import rotate_secret


def get(client_id: str) -> ClientConfig | None:
    """Return one registered client.

    :param client_id: The client id.
    :returns: The client, or ``None`` when it is not registered.
    """
    return get_client(client_id)


def get_all() -> list[ClientConfig]:
    """Return every registered client, enabled or not.

    :returns: The clients, in registry order.
    """
    return get_clients()


def add(
    client_id: str,
    title: str = "",
    redirect_uris: list[str] | None = None,
    grant_types: list[str] | None = None,
    scope: list[str] | tuple[str, ...] | str | None = None,
    public: bool = False,
    service_user: str = "",
) -> tuple[ClientConfig, str]:
    """Register a client, minting a secret for a confidential one.

    :param client_id: Site-unique client id.
    :param title: Label shown to the person on the consent screen.
    :param redirect_uris: The exact URIs this client may be redirected to.
    :param grant_types: Grants this client may use.
    :param scope: Scopes this client may ask for.
    :param public: Whether the client authenticates with no secret.
    :param service_user: Plone userid a client-credentials token acts as.
    :returns: The stored client and its plaintext secret, which is empty for a
        public client and unrecoverable afterwards for any other.
    :raises ServerError: When the client id is already registered. Replacing
        one silently would re-point every token minted for it.
    """
    return add_client(
        client_id,
        title=title,
        redirect_uris=redirect_uris,
        grant_types=grant_types,
        scope=scope,
        public=public,
        service_user=service_user,
    )


def remove(client_id: str) -> None:
    """Unregister a client.

    :param client_id: The client id.
    :raises ServerError: When the client is not registered.
    """
    remove_client(client_id)


def new_secret(client_id: str) -> str:
    """Mint a fresh secret for a client, discarding the old one.

    :param client_id: The client id.
    :returns: The new plaintext secret, unrecoverable afterwards.
    :raises ServerError: When the client is unknown, or is public and so has
        no secret to rotate.
    """
    return rotate_secret(client_id)


def check(client_id: str, secret: str) -> ClientConfig | None:
    """Authenticate a confidential client at the token endpoint.

    :param client_id: The presented client id.
    :param secret: The presented secret.
    :returns: The client, or ``None`` when authentication fails for any
        reason. The reasons are deliberately not distinguishable to the
        caller: unknown, disabled, public and wrong-secret all answer alike.
    """
    return authenticate(client_id, secret)


__all__ = [
    "ClientConfig",
    "add",
    "check",
    "get",
    "get_all",
    "new_secret",
    "remove",
]
