"""The back-channel logout endpoint.

A browser view rather than a plone.restapi service, for the same reason the
token endpoint is one: the caller is a *provider*, posting a form to a URL it
was configured with, and it will not send a JSON body or an Accept header this
package would like.

The responses are the ones OpenID Connect Back-Channel Logout 1.0 §2.8 asks
for: ``200`` with an empty body on success, ``400`` with a JSON ``error`` when
the token cannot be acted on, and ``Cache-Control: no-store`` on both.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.events import SessionsRevoked
from pas.plugins.identity.core.logout import LogoutError
from pas.plugins.identity.core.logout import revoke_sessions
from pas.plugins.identity.core.logout import validate_logout_token
from pas.plugins.identity.core.pas import PLUGIN_ID
from plone import api
from plone.protect.interfaces import IDisableCSRFProtection
from Products.Five.browser import BrowserView
from zope.event import notify
from zope.interface import alsoProvides

import json


class BackChannelLogoutView(BrowserView):
    """Accept a provider's logout token and end the user's session here."""

    def __call__(self) -> str:
        """Handle a back-channel logout.

        :returns: An empty body on success, or a JSON error.
        """
        # A back-channel POST from a provider has no Plone session and no
        # CSRF token, and could not have one.
        alsoProvides(self.request, IDisableCSRFProtection)

        response = self.request.response
        response.setHeader("Cache-Control", "no-store")
        # Set on the success path too, and not only because the error bodies
        # are JSON. Zope's `finalize` turns a 200 with an empty body and no
        # content type into a 204, and OpenID Connect Back-Channel Logout
        # 1.0 §2.8 asks for a 200 -- so without this the endpoint answers a
        # status the specification does not list, which a strict provider is
        # entitled to treat as a failed delivery and retry.
        response.setHeader("Content-Type", "application/json")

        if self.request.get("REQUEST_METHOD", "GET").upper() != "POST":
            return self._error(response, 405, "POST required.")

        token = (self.request.form.get("logout_token") or "").strip()
        if not token:
            return self._error(response, 400, "No logout_token.")

        try:
            provider_id, claims = validate_logout_token(token)
        except LogoutError as exc:
            return self._error(response, 400, str(exc))

        plugin = api.portal.get_tool("acl_users")[PLUGIN_ID]
        jti = claims["jti"]
        if plugin.logout_jtis.seen(jti):
            # Back-Channel Logout 1.0 §2.6 requires a replay to be refused.
            # Recorded before any work is done below, so a token cannot be
            # acted on twice even if the first attempt failed halfway.
            return self._error(response, 400, "logout_token replayed.")
        plugin.logout_jtis.record(jti)

        subject = claims.get("sub", "")
        userid = plugin.store.userid_for(provider_id, subject) if subject else None
        if userid is None:
            # Nothing to end. A success rather than an error on purpose:
            # answering differently would tell an unauthenticated caller
            # which of a provider's subjects have accounts on this site.
            logger.info(
                "Back-channel logout from %s for an identity this site does not know",
                provider_id,
            )
            return ""

        ended = revoke_sessions(userid)
        notify(
            SessionsRevoked(
                userid=userid,
                provider=provider_id,
                subject=subject,
                sessions_ended=ended,
            )
        )
        return ""

    def _error(self, response, status: int, description: str) -> str:
        """Render a refusal.

        :param response: The HTTP response.
        :param status: HTTP status code.
        :param description: What went wrong.
        :returns: The JSON body.
        """
        response.setStatus(status)
        logger.warning("Back-channel logout refused: %s", description)
        return json.dumps({
            "error": "invalid_request",
            "error_description": description,
        })
