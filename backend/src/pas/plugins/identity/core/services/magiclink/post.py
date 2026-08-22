"""``POST @magic-link`` -- send a login link."""

from email.message import EmailMessage
from pas.plugins.identity.core import audit
from pas.plugins.identity.core.controlpanel import get_callback_url
from pas.plugins.identity.core.flows import magiclink
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.interfaces import RateLimited
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.core.services.base import IdentityService
from pas.plugins.identity.core.services.magiclink import get_provider_config
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from plone import api
from plone.restapi.deserializer import json_body
from urllib.parse import urlencode
from zope.interface import alsoProvides

import plone.protect.interfaces


#: Subject line of the login mail.
SUBJECT = "Your sign-in link"

#: The mail body. Deliberately plain: an HTML mail with a disguised link is
#: the shape of a phishing message, and this one asks somebody to click.
BODY = """\
Someone asked to sign in to {site} as {address}.

Use this link within {minutes} minutes:

{url}

The link works once. If you did not ask for it, ignore this message -- it
cannot be used unless it is clicked, and nobody else received it.
"""


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

        store = api.portal.get_tool("acl_users")[PLUGIN_ID].magic_links
        config = provider.config
        try:
            store.check_and_record(
                f"address:{address}",
                int(config.get("rate_limit_per_hour") or magiclink.DEFAULT_RATE_LIMIT),
            )
            store.check_and_record(
                f"ip:{self._client_ip()}",
                int(
                    config.get("ip_rate_limit_per_hour")
                    or magiclink.DEFAULT_IP_RATE_LIMIT
                ),
            )
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
        self._send(address, token, magiclink.ttl_for(config.get("token_ttl")))
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

    def _client_ip(self) -> str:
        """Return the caller's address for rate-limiting purposes.

        Not stored anywhere: this is a bucket key, and the bucket is swept an
        hour later. Recording it in the audit log is a separate, opt-in
        decision.

        :returns: The client IP, or an empty string when there is none.
        """
        return (
            (
                self.request.get("HTTP_X_FORWARDED_FOR")
                or self.request.get("REMOTE_ADDR")
                or ""
            )
            .split(",")[0]
            .strip()
        )

    def _send(self, address: str, token: str, ttl: int) -> None:
        """Post the login link.

        :param address: Where to send it.
        :param token: The magic-link token.
        :param ttl: Lifetime in seconds, for the human-readable text.
        """
        portal = api.portal.get()
        url = f"{get_callback_url()}?{urlencode({'magic_link': token})}"
        message = EmailMessage()
        message["Subject"] = SUBJECT
        message["To"] = address
        message.set_content(
            BODY.format(
                site=portal.Title(),
                address=address,
                minutes=max(1, ttl // 60),
                url=url,
            )
        )
        api.portal.send_email(
            recipient=address,
            subject=SUBJECT,
            body=message.get_content(),
        )
