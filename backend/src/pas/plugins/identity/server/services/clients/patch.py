"""``PATCH @identity-clients/<id>`` -- amend a registration."""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.server.controlpanel.clients import get_clients
from pas.plugins.identity.server.controlpanel.clients import set_clients
from pas.plugins.identity.server.services.clients import ClientsService
from plone.restapi.deserializer import json_body


#: Fields a PATCH may change. ``client_id`` is absent because renaming one
#: would orphan every token already minted for it, and ``auth_method`` is
#: absent because turning a confidential client public would leave a stored
#: secret hash that nothing checks -- both are a delete and a re-register.
EDITABLE = ("title", "redirect_uris", "grant_types", "scope", "enabled", "service_user")


class ClientsPatch(ClientsService):
    """Update a client registration."""

    def reply(self) -> JSONDict:
        """Amend a client.

        :returns: The updated client, or an error body.
        """
        refusal = self._refuse_unless_manager()
        if refusal is not None:
            return refusal
        self._disable_csrf()

        if len(self.segments) != 1:
            return self._error(400, "Bad request", "Expected @identity-clients/<id>")

        clients = get_clients()
        target = next((c for c in clients if c.client_id == self.segments[0]), None)
        if target is None:
            return self._error(404, "Unknown client", repr(self.segments[0]))

        data = json_body(self.request)
        unknown = set(data) - set(EDITABLE)
        if unknown:
            # Silently ignoring a field is how an operator ends up believing
            # they changed something they did not.
            return self._error(
                400,
                "Not editable",
                f"Cannot change: {' '.join(sorted(unknown))}. "
                "Changing a client id or its auth method means registering a "
                "new client.",
            )

        for field in EDITABLE:
            if field in data:
                setattr(target, field, data[field])
        set_clients(clients)
        return self._render(target)
