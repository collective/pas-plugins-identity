"""``POST @identity-callback``.

The provider redirects the browser to a route in Volto, which reads ``code``
and ``state`` off the query string and POSTs them here. This service does the
half that must happen on the backend: redeem the code, validate what comes
back, resolve it to a canonical userid through the PAS plugin, and issue a
``jwt_auth`` token.

This is the only place per login where network I/O and authentication happen.
Every request afterwards rides the token.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core import audit
from pas.plugins.identity.core.controlpanel import get_callback_url
from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.flows import FlowAttempt
from pas.plugins.identity.core.flows import FlowManager
from pas.plugins.identity.core.flows.metadata import metadata_for
from pas.plugins.identity.core.flows.session import FlowSession
from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.interfaces import ClaimsError
from pas.plugins.identity.core.interfaces import FlowError
from pas.plugins.identity.core.interfaces import IdentityCollision
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.interfaces import PrincipalUnavailable
from pas.plugins.identity.core.interfaces import ProviderUnusable
from pas.plugins.identity.core.pas import CREDENTIALS_KEY
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.core.services.base import IdentityService
from pas.plugins.identity.core.services.jwt import mint_token
from plone import api
from plone.restapi.deserializer import json_body
from zope.interface import alsoProvides

import plone.protect.interfaces


class IdentityCallback(IdentityService):
    """Complete an authorization-code flow."""

    def reply(self) -> JSONDict:
        """Finish the flow and answer with a token.

        :returns: The token and where to send the user, or an error body.
        """
        # The frontend POSTs from its own origin and carries no Plone form
        # token. The request is not unprotected: the flow's ``state`` is
        # single-use, bound to the signed session cookie and unguessable,
        # which is exactly the property a CSRF token provides.
        alsoProvides(self.request, plone.protect.interfaces.IDisableCSRFProtection)

        data = json_body(self.request)
        missing = [key for key in ("code", "state") if not data.get(key)]
        if missing:
            return self._error(
                400, "Missing parameters", f"Required: {', '.join(missing)}"
            )

        # ``provider`` is accepted but not required. A provider redirects back
        # with ``code`` and ``state`` and nothing else, so the frontend route
        # the browser lands on cannot know which provider it is talking to --
        # it is a fresh page load, and the query string is all it has. This
        # session does know: ``state`` was minted against an attempt that
        # records the provider, and the code is redeemed against exactly that
        # attempt a moment later. Requiring the caller to tell us as well was
        # asking for something the caller does not have.
        provider_id = data.get("provider") or ""
        if not provider_id:
            try:
                provider_id = self._provider_for(data["state"])
            except FlowError as exc:
                logger.info("Refused callback with an unusable state: %s", exc)
                self._audit_failure("", audit.FLOW_REFUSED, exc)
                return self._error(401, "Authentication failed", str(exc))

        provider = get_provider(provider_id)
        if provider is None or not provider.enabled or provider.driver is None:
            return self._error(404, "Unknown provider", repr(provider_id))

        try:
            attempt, payload = self._exchange(provider, data["state"], data["code"])
            subject = provider.driver.subject(payload)
            claims = provider.driver.normalize_claims(payload)
        except ProviderUnusable as exc:
            # Not an authentication failure: nothing was wrong with the
            # credential, the provider simply cannot take part in this flow.
            # Answering 401 here would send a caller looking for a forged
            # state at what is really a configuration problem.
            logger.info("Unusable provider %r: %s", provider.provider_id, exc)
            self._audit_failure(provider.provider_id, audit.FLOW_REFUSED, exc)
            return self._error(400, "Provider cannot start this flow", str(exc))
        except FlowError as exc:
            # A bad state, a replayed code or a rejected id_token all land
            # here, and all read the same to the caller. They do not read the
            # same in the audit log, which is where an operator looking at a
            # run of refusals needs the detail.
            logger.info("Refused callback for %r: %s", provider.provider_id, exc)
            self._audit_failure(provider.provider_id, audit.FLOW_REFUSED, exc)
            return self._error(401, "Authentication failed", str(exc))
        except ClaimsError as exc:
            logger.info("Unusable payload from %r: %s", provider.provider_id, exc)
            self._audit_failure(provider.provider_id, audit.PAYLOAD_REJECTED, exc)
            return self._error(502, "Provider payload rejected", str(exc))

        if attempt.link_for is not None:
            return self._link(attempt.link_for, provider.provider_id, subject, claims)

        userid = self._authenticate(provider.provider_id, subject, claims)
        token = self._token_for(userid)
        if isinstance(token, dict):
            return token
        return {"token": token, "came_from": attempt.came_from}

    def _token_for(self, userid: str) -> str | JSONDict:
        """Mint the token, or return the error body that replaces it.

        Two ways this fails and they are not the same answer, so they are not
        the same status. A site with no JWT plugin could not have logged
        anybody in by any route; a userid nothing resolves means the login
        worked and the account it names does not exist.

        :param userid: The userid authentication resolved to.
        :returns: The encoded token, or an error body to answer with.
        """
        try:
            token = mint_token(userid)
        except PrincipalUnavailable as exc:
            # A site configuration, not a bad request, and the operator is
            # the only one who can fix it -- so it is logged in full and the
            # caller is told the site is misconfigured rather than that they
            # failed to authenticate.
            logger.error("%s", exc)
            return self._error(
                500,
                "Login failed",
                "Authentication succeeded but this site has no account for "
                "the user. See the log.",
            )
        if token is None:
            # Matches what plone.restapi's own @login answers: the site is
            # misconfigured, not the request.
            return self._error(
                501,
                "Login failed",
                "JWT authentication plugin not installed.",
            )
        return token

    def _link(
        self, link_for: str, provider_id: str, subject: str, claims: Claims
    ) -> JSONDict:
        """Attach the identity just proven to an already-authenticated user.

        A linking flow requires an authenticated session at initiation *and*
        completion by the same session. The attempt records whose account it
        was started for; if the browser finishing it is anonymous, or is
        somebody else, the link is refused. Without that check, an attacker
        who could get a victim to finish their flow would attach their own
        provider account to the victim's login.

        :param link_for: Userid the attempt was started for.
        :param provider_id: Provider id.
        :param subject: Provider-side subject identifier.
        :param claims: Normalized claims.
        :returns: The linked identity, or an error body.
        """
        current = api.user.get_current()
        userid = None if api.user.is_anonymous() else current.getId()
        if userid != link_for:
            logger.warning("Refusing to complete a link for %r as %r", link_for, userid)
            audit.record(
                link_for,
                audit.LINK_REFUSED,
                provider_id,
                False,
                {"reason": "completed by a different session"},
                request=self.request,
            )
            return self._error(
                403,
                "Link refused",
                "This linking flow was started by a different session.",
            )

        try:
            api.portal.get_tool("acl_users")[PLUGIN_ID].link(
                userid, provider_id, subject, claims
            )
        except IdentityCollision as exc:
            # Never merge two people into one account.
            logger.warning("Identity collision on %r: %s", provider_id, exc)
            audit.record(
                userid,
                audit.LINK_COLLISION,
                provider_id,
                False,
                {"subject": subject, "reason": str(exc)},
                request=self.request,
            )
            return self._error(409, "Identity already linked", str(exc))

        return {"linked": {"provider": provider_id, "subject": subject}}

    def _audit_failure(self, provider_id: str, event: str, exc: Exception) -> None:
        """Record a refused callback.

        There is no userid to attribute this to -- that is what being refused
        means -- so it lands in the unattributed bucket, which is where an
        operator investigating an attack will look.

        :param provider_id: Provider the callback claimed to come from.
        :param event: Audit event name.
        :param exc: The refusal, whose message names the precondition that
            failed. It carries no credential: the flow layer raises on state,
            nonce and signature, never echoing the code or the token.
        """
        audit.record(
            None,
            event,
            provider_id,
            False,
            {"reason": str(exc)},
            request=self.request,
        )

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------

    def _provider_for(self, state: str) -> str:
        """Return the provider a ``state`` was minted against.

        :param state: The ``state`` echoed back by the provider.
        :returns: The provider id recorded on the attempt.
        :raises FlowError: When the state is unknown, expired or already used.
        """
        manager = FlowManager(
            FlowSession(self.request), api.portal.get().absolute_url()
        )
        return manager.peek(state).provider_id

    def _exchange(
        self, provider: ProviderConfig, state: str, code: str
    ) -> tuple[FlowAttempt, JSONDict]:
        """Redeem the authorization code.

        :param provider: The configured provider.
        :param state: The ``state`` echoed back by the provider.
        :param code: The authorization code.
        :returns: The consumed attempt and the raw claims payload.
        :raises FlowError: When any security precondition fails.
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

    def _authenticate(self, provider_id: str, subject: str, claims: Claims) -> str:
        """Resolve an external identity to a canonical userid.

        Goes through the PAS plugin rather than around it, so first-login user
        creation, the identity store and the event contract all happen exactly
        as they do for any other caller.

        A login cannot collide: an identity already in the store resolves to
        whoever owns it, and one that is not is minted a fresh userid.
        ``IdentityCollision`` belongs to the *linking* flow, where an identity
        is attached to an already-authenticated user.

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
