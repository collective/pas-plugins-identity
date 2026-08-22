"""The token endpoint.

Form-encoded in, JSON out, because that is what RFC 6749 specifies and what
every OAuth client library sends. That is also why this is a browser view and
not a plone.restapi service: the services in this package read a JSON body,
and a relying party will not send one here.

Two grants live here, and they fail differently on purpose.

The authorization code grant answers ``invalid_grant`` with the same message
for every refusal. The temptation is to be helpful -- "code expired", "wrong
verifier", "that code was already used" -- and each of those sentences is a
probe result. A client that can tell them apart can search.

The client-credentials grant has nothing to hide by the time it gets that far:
the caller has already authenticated with its secret, so every remaining
failure is about its own registration -- a grant it is not registered for, a
scope it may not ask for, a service user the site has not created. Those are
integration errors an operator has to be able to read, and saying so tells an
attacker nothing they did not already have the secret to learn.
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


#: The authorization code grant: a human authorized this at ``/authorize``.
AUTHORIZATION_CODE = "authorization_code"

#: The client-credentials grant: no human, no redirect, no code. The client
#: authenticates as itself and acts as its registered service user.
CLIENT_CREDENTIALS = "client_credentials"

#: Everything this endpoint implements. Refresh and device code are out of
#: scope for v1 and are named in the plan rather than half-built here.
GRANT_TYPES = (AUTHORIZATION_CODE, CLIENT_CREDENTIALS)


class GrantError(Exception):
    """A grant is refused with a specific RFC 6749 error code.

    Used where naming the failure is safe and useful -- the client-credentials
    path, past authentication. The authorization code path does not raise this
    and must not start: its whole discipline is that every refusal looks the
    same.

    :ivar error: The RFC 6749 error code.
    :ivar description: A human-readable explanation.
    """

    def __init__(self, error: str, description: str) -> None:
        """Record a refusal the client is allowed to understand.

        :param error: The RFC 6749 error code.
        :param description: A human-readable explanation.
        """
        super().__init__(description)
        self.error = error
        self.description = description


class TokenView(BrowserView):
    """Issue an access token to an authenticated client."""

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

        grant_type = self._param("grant_type")
        if grant_type not in GRANT_TYPES:
            return self._error(
                response,
                400,
                "unsupported_grant_type",
                f"Supported grants: {', '.join(GRANT_TYPES)}.",
            )

        client = self._authenticate_client(grant_type)
        if client is None:
            # 401 rather than 400, and the header RFC 6749 §5.2 asks for.
            response.setHeader("WWW-Authenticate", 'Basic realm="oauth"')
            return self._error(
                response, 401, "invalid_client", "Client authentication failed."
            )

        try:
            if grant_type == CLIENT_CREDENTIALS:
                body = self._client_credentials(client)
            else:
                body = self._exchange(client)
        except GrantError as exc:
            return self._error(response, 400, exc.error, exc.description)
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

    def _authenticate_client(self, grant_type: str):
        """Identify the client making the request.

        A confidential client authenticates with its secret. A public client
        has none, and is identified by its ``client_id`` alone -- which proves
        nothing, and is exactly why PKCE is mandatory for it. The proof of
        possession for a public client is the verifier, checked at redemption.

        That reasoning is specific to the authorization code grant, where a
        code the client could only have obtained through a browser redirect
        does part of the work. Client credentials have no such second factor:
        RFC 6749 §4.4 requires client authentication outright, so a public
        client is refused here before it can ask.

        :param grant_type: The requested grant.
        :returns: The client, or ``None`` when authentication fails.
        """
        client_id = self._param("client_id")
        secret = self._param("client_secret")
        if secret:
            return authenticate(client_id, secret)

        if grant_type == CLIENT_CREDENTIALS:
            return None

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
        if not client.allows_grant(AUTHORIZATION_CODE):
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

    def _client_credentials(self, client):
        """Mint a token for the client acting as its service user.

        The subject is a real Plone userid rather than the client id. A token
        whose ``sub`` names nothing would authenticate a principal Plone has
        never heard of: PAS would hand back a userid, every roles plugin would
        find nothing for it, and the request would run as somebody who exists
        only inside the token. Requiring the site to nominate a real user
        keeps authorization where an operator can see and change it.

        :param client: The authenticated client.
        :returns: The token response body.
        :raises GrantError: When the client is not registered for this grant,
            asks for a scope it does not have, or has no usable service user.
        """
        if not client.allows_grant(CLIENT_CREDENTIALS):
            raise GrantError(
                "unauthorized_client",
                "This client is not registered for the client credentials grant.",
            )

        scope = self._param("scope") or client.scope
        extra = set(scope.split()) - client.scopes()
        if extra:
            raise GrantError(
                "invalid_scope",
                f"The client is not registered for: {' '.join(sorted(extra))}.",
            )

        if not client.service_user:
            raise GrantError(
                "invalid_client",
                "This client has no service user, so a token for it would act "
                "as nobody. Nominate one on the client registration.",
            )
        if api.user.get(userid=client.service_user) is None:
            raise GrantError(
                "invalid_client",
                f"The service user {client.service_user!r} does not exist.",
            )

        return token_response(
            client_id=client.client_id,
            subject=client.service_user,
            scope=scope,
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
