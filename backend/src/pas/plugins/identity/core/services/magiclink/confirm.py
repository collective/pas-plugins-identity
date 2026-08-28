"""``POST @magic-link-confirm`` -- redeem a link.

One endpoint for two purposes, because a clicked link looks the same either
way: the browser lands on the callback route carrying a token and nothing
else. What the token was minted for decides what happens -- a sign-in, or an
address attached to an account that is already signed in.
"""

from datetime import datetime
from datetime import UTC
from pas.plugins.identity import logger
from pas.plugins.identity.core import audit
from pas.plugins.identity.core.flows import magiclink
from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.interfaces import FlowError
from pas.plugins.identity.core.interfaces import IdentityCollision
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.interfaces import PrincipalUnavailable
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
    """Validate a magic-link token and honour whatever it was minted for."""

    def reply(self) -> JSONDict:
        """Validate and burn a token, then log in or link.

        :returns: A ``jwt_auth`` token, the linked identity, or an error body.
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
            # Both purposes are accepted here and separated below. The
            # acceptance is explicit rather than "any purpose we recognize":
            # a third kind of token added later must fail here until somebody
            # decides what redeeming it should do.
            claims = magiclink.verify(
                token, (magiclink.PURPOSE_LOGIN, magiclink.PURPOSE_LINK)
            )
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
        identity_claims: Claims = {
            "email": address,
            "email_verified": True,
            "raw": {},
        }

        if claims.get("purpose") == magiclink.PURPOSE_LINK:
            return self._link(claims.get("link_for") or "", address, identity_claims)

        self.request.other[CREDENTIALS_KEY] = {
            "provider": EMAIL_PROVIDER,
            "subject": address,
            "claims": identity_claims,
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

        try:
            token_value = mint_token(userid)
        except PrincipalUnavailable as exc:
            # The login worked and the account it names does not exist. A
            # site configuration, not a bad request, and the operator is the
            # only one who can fix it -- so it is logged in full and the
            # caller is told the site is misconfigured rather than that they
            # failed to authenticate.
            logger.error("%s", exc)
            return self._error(
                500,
                "Login failed",
                "Authentication succeeded but this site has no account for "
                "the user. See the log.",
            )
        if token_value is None:
            return self._error(
                501, "Login failed", "JWT authentication plugin not installed."
            )
        return {"token": token_value}

    def _link(self, link_for: str, address: str, claims: Claims) -> JSONDict:
        """Attach a proven address to the account that asked for it.

        The same rule the redirect linking flow enforces, for the same
        reason: whoever finishes the flow must be the user it was started
        for. Here the check is doing more work than it does there, because
        the token travels through a mailbox -- a link forwarded to somebody
        else, or clicked while signed in as another account, must add nothing
        to anybody.

        Burning has already happened, and deliberately: a link refused
        because the wrong person clicked it is spent, not retryable.

        :param link_for: Userid the token was minted for.
        :param address: The proven address.
        :param claims: Normalized claims for the identity.
        :returns: The linked identity, or an error body.
        """
        userid = None if api.user.is_anonymous() else api.user.get_current().getId()
        if not link_for or userid != link_for:
            logger.warning(
                "Refusing to complete an email link for %r as %r", link_for, userid
            )
            audit.record(
                link_for or None,
                audit.LINK_REFUSED,
                EMAIL_PROVIDER,
                False,
                {"reason": "completed by a different session"},
                request=self.request,
            )
            return self._error(
                403,
                "Link refused",
                "This link was sent to confirm an address for a different session.",
            )

        try:
            api.portal.get_tool("acl_users")[PLUGIN_ID].link(
                userid, EMAIL_PROVIDER, address, claims
            )
        except IdentityCollision as exc:
            # Never merge two people into one account.
            logger.warning("Identity collision on an email link: %s", exc)
            audit.record(
                userid,
                audit.LINK_COLLISION,
                EMAIL_PROVIDER,
                False,
                {"subject": address, "reason": str(exc)},
                request=self.request,
            )
            return self._error(409, "Identity already linked", str(exc))

        audit.record(
            userid,
            audit.MAGIC_LINK_CONFIRMED,
            EMAIL_PROVIDER,
            True,
            {"purpose": magiclink.PURPOSE_LINK},
            request=self.request,
        )
        return {"linked": {"provider": EMAIL_PROVIDER, "subject": address}}

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
