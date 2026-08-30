"""``GET @oauth-grants`` -- what this user has authorized."""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.services.base import IdentityService
from pas.plugins.identity.server.claims import SCOPE_CLAIMS
from pas.plugins.identity.server.controlpanel.clients import get_client
from pas.plugins.identity.server.pas import PLUGIN_ID
from pas.plugins.identity.server.grants.tokens import TTL_RECORD
from plone import api


class GrantsGet(IdentityService):
    """List the caller's standing agreements with OAuth clients."""

    def reply(self) -> JSONDict:
        """Return every application this user has authorized.

        :returns: The listing, or an error body.
        """
        if api.user.is_anonymous():
            return self._error(
                401,
                "Not authenticated",
                "Only a signed-in user has authorized anything.",
            )

        userid = api.user.get_current().getId()
        plugin = api.portal.get_tool("acl_users")[PLUGIN_ID]
        base = f"{self.context.absolute_url()}/@oauth-grants"

        return {
            "@id": base,
            "items": [
                self._render(client_id, record, base)
                for client_id, record in plugin.consent.for_user(userid)
            ],
            # How long access already granted can outlive a withdrawal. Sent
            # so the screen can say it rather than guess: an access token is
            # self-encoded with no denylist, so withdrawing consent cannot
            # reach one already minted.
            "access_token_ttl": int(
                api.portal.get_registry_record(TTL_RECORD, default=900)
            ),
        }

    def _render(self, client_id: str, record, base: str) -> JSONDict:
        """Describe one agreement.

        :param client_id: The client it is with.
        :param record: The stored :class:`ConsentRecord`.
        :param base: This endpoint's URL, for the item's own.
        :returns: The item.
        """
        client = get_client(client_id)
        return {
            "@id": f"{base}/{client_id}",
            "client_id": client_id,
            # A client the operator has since unregistered still has a
            # standing agreement, and the user should be able to see it and
            # withdraw it. Named by its id, because there is nothing left to
            # ask for a title.
            "title": (client.title or client_id) if client else client_id,
            "registered": client is not None,
            "enabled": bool(client and client.enabled),
            "granted_at": record.granted_at.isoformat(),
            "scopes": self._scopes(record.scopes),
        }

    def _scopes(self, scopes) -> list[JSONDict]:
        """Describe the scopes agreed to.

        Each with the claims it releases, for the reason the consent screen
        lists them: "profile" tells the person nothing, and the list of
        claims is what they actually agreed to hand over.

        :param scopes: The agreed scope names.
        :returns: One mapping per scope, in a stable order.
        """
        return [
            {"id": scope, "claims": list(SCOPE_CLAIMS.get(scope, ()))}
            for scope in sorted(scopes)
        ]
