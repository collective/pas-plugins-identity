"""``GET @identity-clients`` -- list registrations, or read one."""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.services.schema import jsonschema_for
from pas.plugins.identity.server.controlpanel.interfaces import IClientRecords
from pas.plugins.identity.server.controlpanel.clients import get_client
from pas.plugins.identity.server.controlpanel.clients import get_clients
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
                # The form the panel is built from, serialized by
                # `plone.restapi` from `IClientRecords`. Sent with the listing
                # rather than from an endpoint of its own, because the panel
                # needs both on the same page load and a second round trip
                # buys nothing. See `core.services.providers.drivers`.
                "schema": jsonschema_for(IClientRecords, self.context, self.request),
            }

        client = get_client(self.segments[0])
        if client is None:
            return self._error(404, "Unknown client", repr(self.segments[0]))
        return self._render(client)
