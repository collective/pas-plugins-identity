"""``@identity-callback`` -- finish a flow and hand back a token.

The provider redirects the browser to a route in Volto, which reads ``code``
and ``state`` off the query string and POSTs them here. This service does the
half that must happen on the backend: redeem the code, validate what comes
back, resolve it to a canonical userid through the PAS plugin, and issue a
``jwt_auth`` token.

This is the only place per login where network I/O and authentication happen
(I6). Every request afterwards rides the token.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.controlpanel import get_callback_url
from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.flows import FlowManager
from pas.plugins.identity.core.flows.metadata import metadata_for
from pas.plugins.identity.core.flows.session import FlowSession
from pas.plugins.identity.core.interfaces import ClaimsError
from pas.plugins.identity.core.interfaces import FlowError
from pas.plugins.identity.core.pas import CREDENTIALS_KEY
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.core.services.base import IdentityService
from plone import api
from plone.restapi.deserializer import json_body
from Products.PluggableAuthService.interfaces.plugins import IAuthenticationPlugin
from typing import Any
from zope.interface import alsoProvides

import plone.protect.interfaces


#: ``meta_type`` of the plugin that mints Volto's tokens.
JWT_PLUGIN_META_TYPE = "JWT Authentication Plugin"


class IdentityCallback(IdentityService):
    """Complete an authorization-code flow."""

    def reply(self) -> dict[str, Any]:
        """Finish the flow and answer with a token.

        :returns: The token and where to send the user, or an error body.
        """
        # The frontend POSTs from its own origin and carries no Plone form
        # token. The request is not unprotected: the flow's ``state`` is
        # single-use, bound to the signed session cookie and unguessable,
        # which is exactly the property a CSRF token provides.
        alsoProvides(self.request, plone.protect.interfaces.IDisableCSRFProtection)

        data = json_body(self.request)
        missing = [key for key in ("provider", "code", "state") if not data.get(key)]
        if missing:
            return self._error(
                400, "Missing parameters", f"Required: {', '.join(missing)}"
            )

        provider = get_provider(data["provider"])
        if provider is None or not provider.enabled or provider.driver is None:
            return self._error(404, "Unknown provider", repr(data["provider"]))

        try:
            attempt, payload = self._exchange(provider, data["state"], data["code"])
            subject = provider.driver.subject(payload)
            claims = provider.driver.normalize_claims(payload)
        except FlowError as exc:
            # S1 -- a bad state, a replayed code or a rejected id_token all
            # land here, and all read the same to the caller.
            logger.info("Refused callback for %r: %s", provider.provider_id, exc)
            return self._error(401, "Authentication failed", str(exc))
        except ClaimsError as exc:
            logger.info("Unusable payload from %r: %s", provider.provider_id, exc)
            return self._error(502, "Provider payload rejected", str(exc))

        userid = self._authenticate(provider.provider_id, subject, claims)
        token = self._token(userid)
        if token is None:
            # Matches what plone.restapi's own @login answers: the site is
            # misconfigured, not the request.
            return self._error(
                501,
                "Login failed",
                "JWT authentication plugin not installed.",
            )
        return {"token": token, "came_from": attempt.came_from}

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------

    def _exchange(
        self, provider: Any, state: str, code: str
    ) -> tuple[Any, dict[str, Any]]:
        """Redeem the authorization code.

        :param provider: The configured provider.
        :param state: The ``state`` echoed back by the provider.
        :param code: The authorization code.
        :returns: The consumed attempt and the raw claims payload.
        :raises FlowError: When any S1 precondition fails.
        """
        manager = FlowManager(
            FlowSession(self.request), api.portal.get().absolute_url()
        )
        return manager.finish(
            provider,
            get_callback_url(),
            metadata_for(provider),
            state,
            code,
        )

    def _authenticate(self, provider_id: str, subject: str, claims: dict) -> str:
        """Resolve an external identity to a canonical userid.

        Goes through the PAS plugin rather than around it, so first-login user
        creation, the identity store and the event contract all happen exactly
        as they do for any other caller.

        A login cannot collide: an identity already in the store resolves to
        whoever owns it, and one that is not is minted a fresh userid.
        ``IdentityCollision`` (I3/S3) belongs to the *linking* flow, where an
        identity is attached to an already-authenticated user -- Gate 2.

        :param provider_id: Provider id.
        :param subject: Provider-side subject identifier.
        :param claims: Normalized claims.
        :returns: The canonical userid.
        """
        plugin = api.portal.get_tool("acl_users")[PLUGIN_ID]
        self.request.other[CREDENTIALS_KEY] = {
            "provider": provider_id,
            "subject": subject,
            "claims": claims,
        }
        userid, _login = plugin.authenticateCredentials(
            plugin.extractCredentials(self.request)
        )
        return userid

    def _token(self, userid: str) -> str | None:
        """Mint a ``jwt_auth`` token for a userid.

        :param userid: Canonical Plone userid.
        :returns: The encoded token, or ``None`` when the site has no JWT
            plugin -- in which case Volto could not have logged anybody in by
            any route, and the caller is owed a 501 rather than a traceback.
        """
        acl_users = api.portal.get_tool("acl_users")
        for plugin in acl_users.plugins.listPlugins(IAuthenticationPlugin):
            if plugin[1].meta_type == JWT_PLUGIN_META_TYPE:
                user = acl_users.getUserById(userid)
                return plugin[1].create_token(
                    user.getId(), data={"fullname": user.getProperty("fullname", "")}
                )
        return None
