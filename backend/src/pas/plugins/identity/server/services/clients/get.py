"""``GET @identity-clients`` -- list registrations, or read one."""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.server.clients import get_client
from pas.plugins.identity.server.clients import get_clients
from pas.plugins.identity.server.services.clients import ClientsService


class ClientsGet(ClientsService):
    """Read the client registry."""

    def reply(self) -> JSONDict:
        """List every client, or return one.

        :returns: The listing, one client, or an error body.
        """
        refusal = self._refuse_unless_manager()
        if refusal is not None:
            return refusal

        if not self.segments:
            clients = get_clients()
            return {
                "@id": self._base(),
                "items_total": len(clients),
                "items": [self._render(client) for client in clients],
            }

        client = get_client(self.segments[0])
        if client is None:
            return self._error(404, "Unknown client", repr(self.segments[0]))
        return self._render(client)
