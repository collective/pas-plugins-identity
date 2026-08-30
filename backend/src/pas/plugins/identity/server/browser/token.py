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

from pas.plugins.identity.server.controlpanel.clients import authenticate
from pas.plugins.identity.server.controlpanel.clients import get_client
from pas.plugins.identity.server.grants.codes import CodeError
from pas.plugins.identity.server.interfaces import AUTHORIZATION_CODE
from pas.plugins.identity.server.interfaces import CLIENT_CREDENTIALS
from pas.plugins.identity.server.interfaces import GRANT_TYPES
from pas.plugins.identity.server.interfaces import REFRESH_TOKEN
from pas.plugins.identity.server.interfaces import ServerError
from pas.plugins.identity.server.pas import PLUGIN_ID
from pas.plugins.identity.server.grants.refresh import RefreshError
from pas.plugins.identity.server.grants.tokens import token_response
from plone import api
from plone.protect.interfaces import IDisableCSRFProtection
from Products.Five.browser import BrowserView
from urllib.parse import unquote
from zope.interface import alsoProvides

import base64
import binascii
import json


#: The grants live in ``interfaces`` so the discovery document can advertise
#: exactly what this endpoint serves without importing a browser view. An
#: advertised grant nothing implements is a lie a client acts on.

#: Scheme prefix of the ``Authorization`` header carrying client credentials.
BASIC_PREFIX = "basic "


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
            elif grant_type == REFRESH_TOKEN:
                body = self._refresh(client)
            else:
                body = self._exchange(client)
        except GrantError as exc:
            return self._error(response, 400, exc.error, exc.description)
        except (CodeError, RefreshError, ServerError) as exc:
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
        if isinstance(exc, CodeError | RefreshError):
            return "invalid_grant"
        return "invalid_request"

    def _basic_credentials(self) -> tuple[str, str] | None:
        """Return the client credentials from an ``Authorization: Basic``
        header.

        The header is read off ``request._auth`` rather than through
        ``getHeader``: ZPublisher moves the ``Authorization`` header there
        during request construction and takes it out of the environment, so
        asking for the header by name finds nothing. The Bearer plugin reads
        it the same way, for the same reason.

        :returns: ``(client_id, secret)``, or ``None`` when the request
            carries no Basic header. A header that is present but malformed
            returns ``("", "")`` rather than ``None``, so the caller refuses
            it instead of falling through to the form and authenticating a
            request whose header it could not read.
        """
        header = getattr(self.request, "_auth", None) or ""
        if not header.lower().startswith(BASIC_PREFIX):
            return None

        encoded = header[len(BASIC_PREFIX) :].strip()
        try:
            decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            return ("", "")
        if ":" not in decoded:
            return ("", "")

        # RFC 6749 §2.3.1 says both halves are form-urlencoded before the
        # base64. Every id and secret this server mints is URL-safe already,
        # so this matters only for a client that was registered elsewhere.
        client_id, _, secret = decoded.partition(":")
        return (unquote(client_id), unquote(secret))

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

        Credentials arrive either in the form or in an ``Authorization:
        Basic`` header. RFC 6749 §2.3.1 requires a server to accept the
        header and says the form is optional, so a server that took only the
        form -- as this one did -- refuses most off-the-shelf clients,
        including authlib's, whose default is ``client_secret_basic``.

        :param grant_type: The requested grant.
        :returns: The client, or ``None`` when authentication fails.
        """
        client_id = self._param("client_id")
        secret = self._param("client_secret")

        basic = self._basic_credentials()
        if basic is not None:
            basic_id, basic_secret = basic
            # RFC 6749 §2.3 forbids sending credentials by both means at once,
            # and a mismatch between them is a client id being asserted twice
            # with two different answers. Refuse rather than pick a winner.
            if (client_id and client_id != basic_id) or secret:
                return None
            client_id, secret = basic_id, basic_secret

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
        body = token_response(
            client_id=client.client_id,
            subject=grant.subject,
            scope=grant.scope,
            # Recorded at the authorization request and echoed now. The
            # client-credentials path below has no nonce because it has no
            # authorization request and no browser to bind one to.
            nonce=grant.nonce,
        )
        return self._with_refresh(client, grant.subject, grant.scope, body)

    def _with_refresh(self, client, subject: str, scope: str, body):
        """Add a refresh token when the client is registered for one.

        Gated on the registration rather than on a scope, so whether a client
        may keep working without its user present is an operator's decision
        recorded where every other client permission lives -- not something a
        client grants itself by asking.

        :param client: The authenticated client.
        :param subject: The userid the tokens act for.
        :param scope: The granted scopes.
        :param body: The token response so far.
        :returns: The response, with a refresh token if one is due.
        """
        if not client.allows_grant(REFRESH_TOKEN):
            return body
        store = api.portal.get_tool("acl_users")[PLUGIN_ID].refresh
        body["refresh_token"] = store.issue(client.client_id, subject, scope)
        return body

    def _refresh(self, client):
        """Rotate a refresh token and mint a fresh access token.

        :param client: The authenticated client.
        :returns: The token response body.
        :raises GrantError: When the client may not use this grant, or asks
            to widen its scope.
        :raises RefreshError: When the token is refused.
        """
        if not client.allows_grant(REFRESH_TOKEN):
            raise GrantError(
                "unauthorized_client",
                "This client is not registered for the refresh token grant.",
            )

        store = api.portal.get_tool("acl_users")[PLUGIN_ID].refresh
        replacement, grant = store.rotate(
            self._param("refresh_token"), client.client_id
        )

        # RFC 6749 §6: a refresh request may narrow the scope, never widen
        # it. Silently granting more than the user agreed to at the
        # authorization endpoint would make consent a one-time formality.
        scope = self._param("scope") or grant.scope
        extra = set(scope.split()) - set(grant.scope.split())
        if extra:
            raise GrantError(
                "invalid_scope",
                f"The refresh token does not carry: {' '.join(sorted(extra))}.",
            )

        body = token_response(
            client_id=client.client_id,
            subject=grant.subject,
            scope=scope,
        )
        body["refresh_token"] = replacement
        return body

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
