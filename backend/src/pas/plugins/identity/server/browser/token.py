"""The token endpoint.

Form-encoded in, JSON out, because that is what RFC 6749 specifies and what
every OAuth client library sends. That is also why this is a browser view and
not a plone.restapi service: the services in this package read a JSON body,
and a relying party will not send one here.

Every failure answers ``invalid_grant`` with the same message. The temptation
is to be helpful -- "code expired", "wrong verifier", "that code was already
used" -- and each of those sentences is a probe result. A client that can tell
them apart can search.
"""

from pas.plugins.identity.server.clients import authenticate
from pas.plugins.identity.server.clients import get_client
from pas.plugins.identity.server.codes import CodeError
from pas.plugins.identity.server.interfaces import ServerError
from pas.plugins.identity.server.pas import PLUGIN_ID
from pas.plugins.identity.server.tokens import token_response
from plone import api
from plone.protect.interfaces import IDisableCSRFProtection
from Products.Five.browser import BrowserView
from zope.interface import alsoProvides

import json


#: The grant this endpoint implements. Client credentials arrive with the
#: Bearer plugin, which is what makes a token issued to nobody useful.
GRANT_TYPE = "authorization_code"


class TokenView(BrowserView):
    """Exchange an authorization code for an access token."""

    def _param(self, name: str) -> str:
        """Return a form parameter as a stripped string.

        :param name: Parameter name.
        :returns: The value, or the empty string when absent.
        """
        return (self.request.form.get(name) or "").strip()

    def __call__(self) -> str:
        """Handle a token request.

        :returns: A JSON body -- a token response, or an RFC 6749 error.
        """
        # A token request is a back-channel POST from a server that has no
        # Plone session and no CSRF token, and could not have one.
        alsoProvides(self.request, IDisableCSRFProtection)

        response = self.request.response
        response.setHeader("Content-Type", "application/json")
        # RFC 6749 §5.1: tokens must never be cached.
        response.setHeader("Cache-Control", "no-store")
        response.setHeader("Pragma", "no-cache")

        if self.request.get("REQUEST_METHOD", "GET").upper() != "POST":
            return self._error(response, 405, "invalid_request", "POST required.")

        if self._param("grant_type") != GRANT_TYPE:
            return self._error(
                response,
                400,
                "unsupported_grant_type",
                f"Only {GRANT_TYPE} is supported at this endpoint.",
            )

        client = self._authenticate_client()
        if client is None:
            # 401 rather than 400, and the header RFC 6749 §5.2 asks for.
            response.setHeader("WWW-Authenticate", 'Basic realm="oauth"')
            return self._error(
                response, 401, "invalid_client", "Client authentication failed."
            )

        try:
            body = self._exchange(client)
        except (CodeError, ServerError) as exc:
            return self._error(response, 400, self._error_code(exc), str(exc))
        return json.dumps(body)

    def _error_code(self, exc: Exception) -> str:
        """Map an exception to an RFC 6749 error code.

        :param exc: The failure.
        :returns: ``invalid_grant`` for anything about the code itself, and
            ``invalid_request`` for a server that cannot mint at all -- the
            second is a misconfiguration the operator has to see, not a
            refusal the client caused.
        """
        return "invalid_grant" if isinstance(exc, CodeError) else "invalid_request"

    def _authenticate_client(self):
        """Identify the client making the request.

        A confidential client authenticates with its secret. A public client
        has none, and is identified by its ``client_id`` alone -- which proves
        nothing, and is exactly why PKCE is mandatory for it. The proof of
        possession for a public client is the verifier, checked at redemption.

        :returns: The client, or ``None`` when authentication fails.
        """
        client_id = self._param("client_id")
        secret = self._param("client_secret")
        if secret:
            return authenticate(client_id, secret)

        client = get_client(client_id)
        if client is None or not client.enabled or not client.is_public:
            # A confidential client that sent no secret is not authenticated,
            # and must not be let through as though it were public.
            return None
        return client

    def _exchange(self, client):
        """Redeem the code and build the token response.

        :param client: The authenticated client.
        :returns: The token response body.
        :raises CodeError: When the code is refused.
        """
        if not client.allows_grant(GRANT_TYPE):
            raise CodeError("The authorization code was refused")

        codes = api.portal.get_tool("acl_users")[PLUGIN_ID].codes
        grant = codes.redeem(
            code=self._param("code"),
            client_id=client.client_id,
            redirect_uri=self._param("redirect_uri"),
            verifier=self._param("code_verifier"),
        )
        return token_response(
            client_id=client.client_id,
            subject=grant.subject,
            scope=grant.scope,
        )

    def _error(self, response, status: int, error: str, description: str) -> str:
        """Render an RFC 6749 error response.

        :param response: The HTTP response.
        :param status: HTTP status code.
        :param error: The RFC 6749 error code.
        :param description: A human-readable explanation.
        :returns: The JSON body.
        """
        response.setStatus(status)
        return json.dumps({"error": error, "error_description": description})
