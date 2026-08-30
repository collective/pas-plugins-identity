"""``DELETE @identity-clients/<id>`` -- unregister."""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.server.controlpanel.clients import remove_client
from pas.plugins.identity.server.interfaces import ServerError
from pas.plugins.identity.server.services.clients import ClientsService


class ClientsDelete(ClientsService):
    """Remove a client registration."""

    def reply(self) -> JSONDict | None:
        """Unregister a client.

        Deleting is also this server's only revocation. Access tokens carry
        the client id as their audience and the Bearer plugin looks it up on
        every request, so removing a registration stops its tokens working
        at once -- which is worth knowing before doing it by accident.

        :returns: ``None`` with a 204, or an error body.
        """
        refusal = self._refuse_unless_manager()
        if refusal is not None:
            return refusal
        self._disable_csrf()

        if len(self.segments) != 1:
            return self._error(400, "Bad request", "Expected @identity-clients/<id>")

        try:
            remove_client(self.segments[0])
        except ServerError as exc:
            return self._error(404, "Unknown client", str(exc))
        self.request.response.setStatus(204)
        return None
