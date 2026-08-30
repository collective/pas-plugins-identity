"""``POST @identity-clients`` -- register one, or rotate its secret."""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.server.controlpanel.clients import add_client
from pas.plugins.identity.server.controlpanel.clients import get_client
from pas.plugins.identity.server.controlpanel.clients import rotate_secret
from pas.plugins.identity.server.interfaces import ServerError
from pas.plugins.identity.server.services import ROTATE_SECRET_ACTION
from pas.plugins.identity.server.services.clients import ClientsService
from plone.restapi.deserializer import json_body


class ClientsPost(ClientsService):
    """Register a client, or mint it a fresh secret."""

    def reply(self) -> JSONDict:
        """Create a client, or run ``rotate-secret`` on one.

        :returns: The created client and its secret, the new secret, or an
            error body.
        """
        refusal = self._refuse_unless_manager()
        if refusal is not None:
            return refusal
        self._disable_csrf()

        if len(self.segments) == 2 and self.segments[1] == ROTATE_SECRET_ACTION:
            return self._rotate(self.segments[0])
        if self.segments:
            return self._error(
                400,
                "Bad request",
                f"Expected @identity-clients/<id>/{ROTATE_SECRET_ACTION}",
            )
        return self._create()

    def _create(self) -> JSONDict:
        """Register a new client.

        :returns: The client and its secret, or an error body.
        """
        data = json_body(self.request)
        client_id = (data.get("client_id") or "").strip()
        if not client_id:
            return self._error(400, "Missing parameters", "Required: client_id")

        redirect_uris = data.get("redirect_uris") or []
        public = bool(data.get("public", False))
        grant_types = data.get("grant_types") or ["authorization_code"]
        if "authorization_code" in grant_types and not redirect_uris:
            # A code-grant client with nowhere to be redirected cannot
            # complete a flow, and the failure would surface much later as a
            # refusal at /authorize that reads like a client bug.
            return self._error(
                400,
                "Missing parameters",
                "A client using the authorization code grant needs at least "
                "one redirect_uri.",
            )

        try:
            client, secret = add_client(
                client_id=client_id,
                title=data.get("title", ""),
                redirect_uris=redirect_uris,
                grant_types=grant_types,
                scope=data.get("scope", ""),
                public=public,
                service_user=data.get("service_user", ""),
            )
        except ServerError as exc:
            # Reusing an id would silently re-point every token already
            # minted for it.
            return self._error(409, "Already registered", str(exc))

        self.request.response.setStatus(201)
        return self._render(client, secret=secret)

    def _rotate(self, client_id: str) -> JSONDict:
        """Mint a client a fresh secret, discarding the old one.

        :param client_id: The client to rotate.
        :returns: The client and its new secret, or an error body.
        """
        if get_client(client_id) is None:
            return self._error(404, "Unknown client", repr(client_id))
        try:
            secret = rotate_secret(client_id)
        except ServerError as exc:
            # A public client has no secret to rotate.
            return self._error(400, "Not applicable", str(exc))
        return self._render(get_client(client_id), secret=secret)
