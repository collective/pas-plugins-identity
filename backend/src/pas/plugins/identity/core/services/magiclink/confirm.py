"""``POST @magic-link-confirm`` -- redeem a login link."""

from datetime import datetime
from datetime import UTC
from pas.plugins.identity import logger
from pas.plugins.identity.core import audit
from pas.plugins.identity.core.flows import magiclink
from pas.plugins.identity.core.interfaces import FlowError
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.pas import CREDENTIALS_KEY
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.core.services.base import IdentityService
from pas.plugins.identity.core.services.jwt import mint_token
from pas.plugins.identity.core.services.magiclink import get_provider_config
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from plone import api
from plone.restapi.deserializer import json_body
from zope.interface import alsoProvides

import plone.protect.interfaces


class MagicLinkConfirm(IdentityService):
    """Validate a magic-link token and log its holder in."""

    def reply(self) -> JSONDict:
        """Validate and burn a token, then issue credentials.

        :returns: A ``jwt_auth`` token, or an error body.
        """
        alsoProvides(self.request, plone.protect.interfaces.IDisableCSRFProtection)

        if get_provider_config() is None:
            return self._error(
                404, "Unknown provider", "No email provider is configured."
            )

        token = (json_body(self.request).get("token") or "").strip()
        if not token:
            return self._error(400, "Missing parameters", "Required: token")

        try:
            claims = magiclink.verify(token)
        except FlowError as exc:
            return self._refuse(str(exc))

        plugin = api.portal.get_tool("acl_users")[PLUGIN_ID]
        store = plugin.magic_links
        jti = claims["jti"]
        if store.is_burned(jti):
            # The second click on a forwarded link is worth nothing.
            return self._refuse("Magic link has already been used")

        store.burn(jti, datetime.fromtimestamp(claims["exp"], tz=UTC))

        address = claims["sub"]
        self.request.other[CREDENTIALS_KEY] = {
            "provider": EMAIL_PROVIDER,
            "subject": address,
            "claims": {"email": address, "email_verified": True, "raw": {}},
        }
        userid, _login = plugin.authenticateCredentials(
            plugin.extractCredentials(self.request)
        )
        audit.record(
            userid,
            audit.MAGIC_LINK_CONFIRMED,
            EMAIL_PROVIDER,
            True,
            request=self.request,
        )

        token_value = mint_token(userid)
        if token_value is None:
            return self._error(
                501, "Login failed", "JWT authentication plugin not installed."
            )
        return {"token": token_value}

    def _refuse(self, reason: str) -> JSONDict:
        """Refuse a token, audibly.

        Expired, forged, already-used and wrong-purpose all read identically
        to the caller; the audit entry carries the difference.

        :param reason: Why it was refused.
        :returns: The error body.
        """
        logger.info("Refused a magic link: %s", reason)
        audit.record(
            None,
            audit.MAGIC_LINK_REFUSED,
            EMAIL_PROVIDER,
            False,
            {"reason": reason},
            request=self.request,
        )
        return self._error(401, "Authentication failed", "Magic link is not valid.")
