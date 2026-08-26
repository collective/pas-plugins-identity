"""``POST @magic-link`` -- send a login link."""

from pas.plugins.identity.core import audit
from pas.plugins.identity.core.flows import magiclink
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.interfaces import RateLimited
from pas.plugins.identity.core.services.base import IdentityService
from pas.plugins.identity.core.services.magiclink import check_rate_limits
from pas.plugins.identity.core.services.magiclink import get_provider_config
from pas.plugins.identity.core.services.magiclink import send_link
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from plone.restapi.deserializer import json_body
from zope.interface import alsoProvides

import plone.protect.interfaces


class MagicLinkSend(IdentityService):
    """Send a login link to an email address."""

    def reply(self) -> JSONDict:
        """Send a login link for an address.

        :returns: The same acknowledgement whatever happened, or an error for
            a malformed request or a rate-limited caller.
        """
        alsoProvides(self.request, plone.protect.interfaces.IDisableCSRFProtection)

        provider = get_provider_config()
        if provider is None:
            return self._error(
                404, "Unknown provider", "No email provider is configured."
            )

        data = json_body(self.request)
        address = (data.get("email") or "").strip().lower()
        if not address or "@" not in address:
            return self._error(400, "Missing parameters", "Required: email")

        config = provider.config
        try:
            check_rate_limits(config, address, self.request)
        except RateLimited as exc:
            # The refusal is visible, unlike the send itself: a caller being
            # throttled is not being told anything about which addresses
            # exist.
            audit.record(
                None,
                audit.MAGIC_LINK_REFUSED,
                EMAIL_PROVIDER,
                False,
                {"reason": "rate limited"},
                request=self.request,
            )
            return self._error(429, "Too many requests", str(exc))

        token, _jti = magiclink.issue(address, config.get("token_ttl"))
        send_link(address, token, magiclink.ttl_for(config.get("token_ttl")))
        audit.record(
            None,
            audit.MAGIC_LINK_SENT,
            EMAIL_PROVIDER,
            True,
            request=self.request,
        )

        # Always the same answer. Telling the caller whether the address was
        # known would turn this into an account-enumeration oracle.
        return {"sent": True}
