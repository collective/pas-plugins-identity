"""The authorization endpoint.

A browser view rather than a plone.restapi service, because this endpoint is
not consumed by the frontend: it is where a relying party sends a *browser*,
and what it returns is a redirect. The rest of this package's HTTP surface
answers JSON to Volto; this one answers 302 to whatever OAuth client the site
has been configured for.

The error handling is the part worth reading. RFC 6749 splits failures in two,
and the split is a security boundary rather than a nicety:

* If the client id or the redirect URI cannot be trusted, the error is shown
  *here*. Redirecting would mean sending the error -- and whatever the caller
  put in ``state`` -- to a URI this server has not verified, which is an open
  redirect wearing a specification as a hat.
* Every other failure goes back to the registered redirect URI as
  ``error=...``, because by then the destination is known-good and the client
  is the thing that needs to hear about it.
"""

from pas.plugins.identity.server.clients import get_client
from pas.plugins.identity.server.codes import ChallengeError
from pas.plugins.identity.server.codes import check_challenge
from pas.plugins.identity.server.pas import PLUGIN_ID
from plone import api
from plone.protect.interfaces import IDisableCSRFProtection
from Products.Five.browser import BrowserView
from urllib.parse import urlencode
from zope.interface import alsoProvides

import html


#: The only response type this server supports. Implicit and hybrid flows are
#: out: OAuth 2.1 removes the implicit grant, and this server has no reason to
#: put a token in a URL fragment.
RESPONSE_TYPE = "code"


class AuthorizationError(Exception):
    """A failure that must be reported to the client, not to the browser.

    :ivar error: The RFC 6749 error code.
    :ivar description: A human-readable explanation, safe to hand back.
    """

    def __init__(self, error: str, description: str) -> None:
        """Record an error to redirect back to the client.

        :param error: The RFC 6749 error code.
        :param description: A human-readable explanation. Required: an error
            code on its own tells a client integrator nothing, and every
            failure here has something specific to say.
        """
        super().__init__(description)
        self.error = error
        self.description = description


class AuthorizeView(BrowserView):
    """Issue an authorization code to a registered client."""

    def _param(self, name: str) -> str:
        """Return a request parameter as a stripped string.

        :param name: Parameter name.
        :returns: The value, or the empty string when absent.
        """
        return (self.request.form.get(name) or "").strip()

    def __call__(self) -> str:
        """Handle an authorization request.

        :returns: An error page when the client or redirect URI cannot be
            trusted; otherwise the empty string, having set a redirect.
        """
        # This endpoint is reached by a cross-site redirect by design, so
        # plone.protect's automatic CSRF handling must not rewrite it into a
        # confirmation page. Nothing here writes on GET except the code store,
        # which is the whole point of the endpoint.
        alsoProvides(self.request, IDisableCSRFProtection)

        client_id = self._param("client_id")
        redirect_uri = self._param("redirect_uri")

        client = get_client(client_id)
        if client is None or not client.enabled:
            return self._refuse(
                "Unknown client",
                f"No enabled client is registered as {client_id!r}.",
            )
        if not client.check_redirect_uri(redirect_uri):
            return self._refuse(
                "Unregistered redirect URI",
                "The redirect_uri does not exactly match one registered for "
                "this client.",
            )

        state = self._param("state")
        try:
            location = self._authorize(client, redirect_uri)
        except AuthorizationError as exc:
            params = {"error": exc.error, "error_description": exc.description}
            if state:
                params["state"] = state
            location = f"{redirect_uri}?{urlencode(params)}"

        self.request.response.redirect(location, status=302)
        return ""

    def _authorize(self, client, redirect_uri: str) -> str:
        """Validate the rest of the request and issue a code.

        :param client: The registered client.
        :param redirect_uri: The verified redirect URI.
        :returns: The URL to redirect the browser to.
        :raises AuthorizationError: For any failure the client should be told
            about at its redirect URI.
        """
        if self._param("response_type") != RESPONSE_TYPE:
            raise AuthorizationError(
                "unsupported_response_type",
                "Only the authorization code flow is supported.",
            )
        if not client.allows_grant("authorization_code"):
            raise AuthorizationError(
                "unauthorized_client",
                "This client is not registered for the authorization code grant.",
            )

        try:
            challenge = check_challenge(
                self._param("code_challenge"),
                self._param("code_challenge_method"),
                required=client.requires_pkce,
            )
        except ChallengeError as exc:
            raise AuthorizationError("invalid_request", str(exc)) from exc

        scope = self._param("scope")
        granted = client.scopes()
        requested = set(scope.split())
        if requested - granted:
            raise AuthorizationError(
                "invalid_scope",
                "The client is not registered for: "
                f"{' '.join(sorted(requested - granted))}.",
            )

        user = api.user.get_current()
        if api.user.is_anonymous():
            # Nothing to consent with. The relying party sent a browser here
            # expecting a login; where that login happens is the site's
            # business, so it is told to come back rather than guessed at.
            raise AuthorizationError(
                "login_required",
                "The end user is not authenticated at the authorization server.",
            )

        codes = api.portal.get_tool("acl_users")[PLUGIN_ID].codes
        code = codes.issue(
            client_id=client.client_id,
            subject=user.getId(),
            redirect_uri=redirect_uri,
            scope=scope,
            challenge=challenge,
        )
        params = {"code": code}
        state = self._param("state")
        if state:
            # Echoed verbatim and never interpreted: it is the client's CSRF
            # token, and this server's only job is to hand it back unchanged.
            params["state"] = state
        return f"{redirect_uri}?{urlencode(params)}"

    def _refuse(self, title: str, detail: str) -> str:
        """Report a failure that must not be redirected anywhere.

        :param title: Short heading.
        :param detail: Explanation.
        :returns: A minimal HTML page.
        """
        self.request.response.setStatus(400)
        self.request.response.setHeader("Content-Type", "text/html; charset=utf-8")
        # Both halves are escaped: `detail` quotes the client_id the caller
        # sent, and this page is rendered precisely when that value is not
        # one this server has agreed to trust.
        title = html.escape(title)
        detail = html.escape(detail)
        return (
            "<!DOCTYPE html><html><head><title>Authorization request "
            f"refused</title></head><body><h1>{title}</h1><p>{detail}</p>"
            "<p>This error is shown here rather than sent back, because the "
            "request did not establish a destination this server trusts.</p>"
            "</body></html>"
        )
