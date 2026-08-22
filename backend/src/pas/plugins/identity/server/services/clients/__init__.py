"""``@identity-clients`` -- the OAuth client registry, over HTTP."""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.server.services import ServerAdminService


class ClientsService(ServerAdminService):
    """Base for the client CRUD verbs."""

    def _base(self) -> str:
        """Return this service's canonical URL.

        :returns: The URL.
        """
        return f"{self.context.absolute_url()}/@identity-clients"

    def _render(self, client, secret: str = "") -> JSONDict:
        """Render one client for an API response.

        :param client: The client registration.
        :param secret: The plaintext secret, when this response is the one
            that minted it. Included exactly once and never recoverable
            afterwards, which is what ``include_hash=False`` guarantees for
            every other response.
        :returns: JSON-ready mapping.
        """
        payload = client.serialize()
        payload["@id"] = f"{self._base()}/{client.client_id}"
        if secret:
            payload["secret"] = secret
            payload["notice"] = (
                "This is the only time this secret is shown. It is stored "
                "hashed and cannot be read back; if it is lost, rotate it."
            )
        return payload
