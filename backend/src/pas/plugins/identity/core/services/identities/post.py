"""``POST @identities`` -- start a linking flow.

Two shapes, because there are two kinds of provider. A redirect provider
answers with an ``authorize_url`` for the browser to follow; the email
provider has no such URL to give -- its "provider" is a mailbox -- so it
answers ``{"sent": true}`` and the flow continues when the link is clicked.

Both end in the same place: :meth:`_link` on the callback service, or its
counterpart on ``@magic-link-confirm``, attaching the proven identity to the
account that started the flow and to no other.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core import audit
from pas.plugins.identity.core.controlpanel import get_callback_url
from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.flows import FlowManager
from pas.plugins.identity.core.flows import magiclink
from pas.plugins.identity.core.flows.metadata import metadata_for
from pas.plugins.identity.core.flows.session import FlowSession
from pas.plugins.identity.core.interfaces import FlowError
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.interfaces import ProviderUnusable
from pas.plugins.identity.core.interfaces import RateLimited
from pas.plugins.identity.core.services.identities import IdentitiesBase
from pas.plugins.identity.core.services.magiclink import check_rate_limits
from pas.plugins.identity.core.services.magiclink import send_link
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from pas.plugins.identity.core.subscribers import get_profile
from plone import api
from plone.restapi.deserializer import json_body


class IdentitiesPost(IdentitiesBase):
    """Start a flow that links another provider to the caller's account."""

    def reply(self) -> JSONDict:
        """Start a flow that will link a provider to the caller's account.

        :returns: The authorize URL, an acknowledged send, or an error body.
        """
        self._disable_csrf()
        userid = self._userid()
        if userid is None:
            # A linking flow may not even be *started* anonymously.
            return self._error(401, "Not authenticated", "Log in first.")

        data = json_body(self.request)
        provider_id = data.get("provider")
        if not provider_id:
            return self._error(400, "Missing parameters", "Required: provider")

        provider = get_provider(provider_id)
        if provider is None or not provider.enabled or provider.driver is None:
            return self._error(404, "Unknown provider", repr(provider_id))

        if provider.driver_id == EMAIL_PROVIDER:
            return self._start_email_link(provider, userid, data)

        try:
            manager = FlowManager(
                FlowSession(self.request), api.portal.get().absolute_url()
            )
            authorize_url = manager.start(
                provider,
                get_callback_url(),
                metadata_for(provider),
                came_from=data.get("came_from", ""),
                link_for=userid,
            )
        except ProviderUnusable as exc:
            # Permanent, so not an outage. A client that renders every
            # provider as a button lands here for anything that is not a
            # redirect flow, and telling it "unavailable" would have it
            # offering the same broken button again tomorrow.
            logger.info("Refusing to start a link for %r: %s", provider_id, exc)
            return self._error(400, "Provider cannot start this flow", str(exc))
        except FlowError as exc:
            logger.info("Refusing to start a link for %r: %s", provider_id, exc)
            return self._error(502, "Provider unavailable", str(exc))

        return {"provider": provider_id, "authorize_url": authorize_url}

    def _refuse_unless_own_address(self, userid: str, address: str) -> JSONDict | None:
        """Refuse to verify an address that is not on the caller's profile.

        This is what replaces the free-text address box the identities page
        used to have. A magic link proves control of whatever was typed, so an
        unguarded form here verifies *any* mailbox -- including one somebody
        has momentary access to -- and a verified address is what
        ``auto_link_by_email`` attaches a new provider account to. Naming the
        address on your profile first makes it a claim somebody can see and an
        administrator can audit, rather than a value that only ever existed
        inside one request.

        A caller with no Profile is not held to it. That is a site not keeping
        users as content, or an account that predates this add-on, and neither
        has a list to name an address on.

        :param userid: The caller.
        :param address: The address they asked to verify.
        :returns: An error body, or ``None`` when the address is theirs to
            verify.
        """
        profile = get_profile(userid)
        if profile is None:
            return None
        if address in (getattr(profile, "emails", None) or ()):
            return None
        return self._error(
            400,
            "Not one of your addresses",
            "Add the address to your profile before verifying it.",
        )

    def _start_email_link(
        self, provider: ProviderConfig, userid: str, data: JSONDict
    ) -> JSONDict:
        """Mail a link that will attach an address to the caller's account.

        Unlike ``@magic-link``, this one *may* tell the caller when it refuses:
        there is no address to enumerate, because the caller is authenticated
        and is naming a mailbox rather than guessing at one.

        The account is recorded in the token rather than in the flow cookie.
        The mail is very often opened in another browser -- a phone, a
        webmail tab in another profile -- where no cookie of ours exists, and
        a flow that only completed in the originating browser would be a
        linking feature that fails for most of the people using it. The
        same-session guarantee the cookie was providing is kept by requiring
        the redeeming session to *be* that user, which is checked when the
        link is clicked.

        :param provider: The email provider.
        :param userid: The account the address will be attached to.
        :param data: The request body.
        :returns: An acknowledgement, or an error body.
        """
        address = (data.get("email") or "").strip().lower()
        if not address or "@" not in address:
            return self._error(400, "Missing parameters", "Required: email")

        refusal = self._refuse_unless_own_address(userid, address)
        if refusal is not None:
            return refusal

        config = provider.config
        try:
            check_rate_limits(config, address, self.request)
        except RateLimited as exc:
            audit.record(
                userid,
                audit.MAGIC_LINK_REFUSED,
                EMAIL_PROVIDER,
                False,
                {"reason": "rate limited"},
                request=self.request,
            )
            return self._error(429, "Too many requests", str(exc))

        ttl = config.get("token_ttl")
        token, _jti = magiclink.issue(
            address,
            ttl,
            purpose=magiclink.PURPOSE_LINK,
            link_for=userid,
        )
        send_link(address, token, magiclink.ttl_for(ttl), userid=userid)
        audit.record(
            userid,
            audit.MAGIC_LINK_SENT,
            EMAIL_PROVIDER,
            True,
            {"purpose": magiclink.PURPOSE_LINK},
            request=self.request,
        )
        return {"provider": provider.provider_id, "sent": True}
