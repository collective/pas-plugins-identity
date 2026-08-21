"""``@magic-link`` and ``@magic-link-confirm`` (Gate 3, S5/S2).

``POST @magic-link`` with ``{"email": "..."}``
    Sends a login link, and answers the same way whether or not the address
    is known. Anything else turns the endpoint into a way to ask Plone which
    addresses have accounts.

``POST @magic-link-confirm`` with ``{"token": "..."}``
    Validates the token, burns it, and answers with a ``jwt_auth`` token.

The identity this proves is ``("email", <address>)``, and it is verified by
construction: the only way to hold the token is to have received the mail.
That is what lets it satisfy the S4 unlink guard, and it is *not* the same
thing as a provider claiming ``email_verified`` about the same address (S2).
"""

from email.message import EmailMessage
from pas.plugins.identity import logger
from pas.plugins.identity.core.audit import MAGIC_LINK_CONFIRMED
from pas.plugins.identity.core.audit import MAGIC_LINK_REFUSED
from pas.plugins.identity.core.audit import MAGIC_LINK_SENT
from pas.plugins.identity.core.audit import record as audit
from pas.plugins.identity.core.controlpanel import get_callback_url
from pas.plugins.identity.core.flows import magiclink
from pas.plugins.identity.core.interfaces import FlowError
from pas.plugins.identity.core.interfaces import RateLimited
from pas.plugins.identity.core.pas import CREDENTIALS_KEY
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.core.services.base import IdentityService
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from plone import api
from plone.restapi.deserializer import json_body
from typing import Any
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
    """``POST @magic-link`` -- send a login link."""

    def reply(self) -> dict[str, Any]:
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
            # S5 -- and the refusal is visible, unlike the send itself: a
            # caller being throttled is not being told anything about which
            # addresses exist.
            audit(
                None,
                MAGIC_LINK_REFUSED,
                EMAIL_PROVIDER,
                False,
                {"reason": "rate limited"},
                request=self.request,
            )
            return self._error(429, "Too many requests", str(exc))

        token, _jti = magiclink.issue(address, config.get("token_ttl"))
        self._send(address, token, magiclink.ttl_for(config.get("token_ttl")))
        audit(
            None,
            MAGIC_LINK_SENT,
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
        decision (D7).

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


class MagicLinkConfirm(IdentityService):
    """``POST @magic-link-confirm`` -- redeem a login link."""

    def reply(self) -> dict[str, Any]:
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
            # S5 -- the second click on a forwarded link is worth nothing.
            return self._refuse("Magic link has already been used")

        from datetime import datetime
        from datetime import UTC

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
        audit(userid, MAGIC_LINK_CONFIRMED, EMAIL_PROVIDER, True, request=self.request)

        token_value = _jwt_token(userid)
        if token_value is None:
            return self._error(
                501, "Login failed", "JWT authentication plugin not installed."
            )
        return {"token": token_value}

    def _refuse(self, reason: str) -> dict[str, Any]:
        """Refuse a token, audibly.

        Expired, forged, already-used and wrong-purpose all read identically
        to the caller; the audit entry carries the difference.

        :param reason: Why it was refused.
        :returns: The error body.
        """
        logger.info("Refused a magic link: %s", reason)
        audit(
            None,
            MAGIC_LINK_REFUSED,
            EMAIL_PROVIDER,
            False,
            {"reason": reason},
            request=self.request,
        )
        return self._error(401, "Authentication failed", "Magic link is not valid.")


def get_provider_config():
    """Return the configured email provider, if there is one.

    :returns: The provider, or ``None`` when magic-link login is not enabled.
    """
    for provider in _email_providers():
        return provider
    return None


def _email_providers():
    """Yield enabled providers driven by the email driver.

    :returns: Generator of provider configurations.
    """
    from pas.plugins.identity.core.controlpanel import enabled_providers

    return (p for p in enabled_providers() if p.driver_id == EMAIL_PROVIDER)


def _jwt_token(userid: str) -> str | None:
    """Mint a ``jwt_auth`` token for a userid.

    :param userid: Canonical Plone userid.
    :returns: The encoded token, or ``None`` when the site has no JWT plugin.
    """
    from pas.plugins.identity.core.services.callback import JWT_PLUGIN_META_TYPE
    from Products.PluggableAuthService.interfaces.plugins import IAuthenticationPlugin

    acl_users = api.portal.get_tool("acl_users")
    for _id, plugin in acl_users.plugins.listPlugins(IAuthenticationPlugin):
        if plugin.meta_type == JWT_PLUGIN_META_TYPE:
            user = acl_users.getUserById(userid)
            return plugin.create_token(
                user.getId(), data={"fullname": user.getProperty("fullname", "")}
            )
    return None
