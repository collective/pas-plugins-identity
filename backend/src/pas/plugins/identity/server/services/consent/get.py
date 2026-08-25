"""``GET @oauth-consent`` -- what a pending authorization request is asking for."""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.services.base import IdentityService
from pas.plugins.identity.server.browser.authorize import CARRIED_PARAMS
from pas.plugins.identity.server.claims import SCOPE_CLAIMS
from pas.plugins.identity.server.clients import get_client
from plone import api
from plone.protect.authenticator import createToken


class ConsentGet(IdentityService):
    """Describe the authorization request the caller's browser arrived with."""

    def reply(self) -> JSONDict:
        """Return what to put on the consent screen.

        :returns: The client, the signed-in user, the scopes being asked for
            and where to send the answer -- or an error body.
        """
        if api.user.is_anonymous():
            # The authorization endpoint sends an anonymous browser to log in
            # before it ever gets here, so this is a screen opened directly.
            return self._error(
                401,
                "Not authenticated",
                "Log in before answering an authorization request.",
            )

        client_id = self._param("client_id")
        client = get_client(client_id)
        if client is None or not client.enabled:
            return self._error(
                404,
                "Unknown client",
                f"No enabled client is registered as {client_id!r}.",
            )
        if not client.check_redirect_uri(self._param("redirect_uri")):
            # Refused rather than described. Rendering a consent screen for a
            # request this server would not honour is a page that asks for
            # somebody's account on behalf of nobody, served from the site's
            # own domain.
            return self._error(
                400,
                "Unregistered redirect URI",
                "The redirect_uri does not exactly match one registered for "
                "this client.",
            )

        user = api.user.get_current()
        return {
            "@id": f"{self.context.absolute_url()}/@oauth-consent",
            "client": {
                "id": client.client_id,
                # A client registered without a title is still something the
                # user has to be able to identify, and its id is what the
                # operator typed.
                "title": client.title or client.client_id,
            },
            "user": {
                "id": user.getId(),
                "label": user.getProperty("fullname", "") or user.getId(),
            },
            "scopes": self._scopes(),
            # Where the answer goes. The screen navigates the browser here
            # with `consent=allow` or anything else, and this server decides
            # again from scratch.
            "authorize_url": f"{self.context.absolute_url()}/@@oauth-authorize",
            # Carried so the screen can hand the request back unchanged. An
            # absent parameter stays absent: an empty `code_challenge` is not
            # the same request as no `code_challenge`, and PKCE turns on that
            # difference.
            "params": {
                name: self._param(name) for name in CARRIED_PARAMS if self._param(name)
            },
            # plone.protect's token, bound to this user. The authorization
            # endpoint refuses an answer without a valid one: a forged
            # consent POST is an attempt to authorize a client on somebody
            # else's behalf.
            "authenticator": createToken(),
        }

    def _param(self, name: str) -> str:
        """Return a query parameter as a stripped string.

        :param name: Parameter name.
        :returns: The value, or the empty string when absent.
        """
        return (self.request.form.get(name) or "").strip()

    def _scopes(self) -> list[JSONDict]:
        """Describe each requested scope.

        The claims are listed because "profile" means nothing to the person
        being asked, while "name, preferred_username, website, picture,
        description" is the actual question. A scope this server does not
        know releases nothing and is reported with an empty list rather than
        omitted: the client asked for it, and a screen that silently drops
        part of the request is describing a different request.

        :returns: One mapping per scope, in the order the client asked -- the
            order it will have documented them in.
        """
        return [
            {"id": scope, "claims": list(SCOPE_CLAIMS.get(scope, ()))}
            for scope in self._param("scope").split()
        ]
