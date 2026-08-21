"""Authorization-code flows (§4.4, S1).

Every byte of OAuth/OIDC wire protocol goes through authlib (I2): this module
builds authlib clients from provider configuration, holds the per-attempt
security material in the session, and hands the callback's payload back to the
caller. It constructs no authorize URLs, no token requests and parses no JWTs
by hand.

The security material -- ``state``, the PKCE ``code_verifier`` and the OIDC
``nonce`` -- is generated here, stored against the initiating session, and
required to match at callback time. A callback that cannot produce all three
is refused (S1).
"""

from authlib.integrations.requests_client import OAuth2Session
from datetime import datetime
from datetime import timedelta
from datetime import UTC
from pas.plugins.identity import logger
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.interfaces import FlowError
from typing import Any
from urllib.parse import urlparse

import secrets


#: Session key holding pending flow attempts.
SESSION_KEY = "pas.plugins.identity.flows"

#: How long an unfinished attempt stays valid. Longer than any human takes to
#: type a password at their provider, short enough that a stolen ``state`` is
#: useless by the time it is replayed.
ATTEMPT_TTL = timedelta(minutes=10)

#: PKCE method. ``plain`` is never offered: it defeats the point.
CODE_CHALLENGE_METHOD = "S256"


class FlowAttempt:
    """One in-flight authorization attempt.

    :ivar state: The OAuth ``state`` value; also the attempt's id.
    :ivar provider_id: Provider the attempt is against.
    :ivar code_verifier: PKCE verifier, never sent to the authorize endpoint.
    :ivar nonce: OIDC nonce, echoed in the ``id_token``.
    :ivar came_from: Where to send the user afterwards, already validated.
    :ivar link_for: Userid this attempt links an identity *to*, when the flow
        was started from the linking UI rather than the login page. ``None``
        for an ordinary login.
    :ivar created: When the attempt started.
    """

    def __init__(
        self,
        state: str,
        provider_id: str,
        code_verifier: str,
        nonce: str,
        came_from: str = "",
        link_for: str | None = None,
    ) -> None:
        """Record an attempt.

        :param state: The OAuth ``state`` value.
        :param provider_id: Provider the attempt is against.
        :param code_verifier: PKCE verifier.
        :param nonce: OIDC nonce.
        :param came_from: Validated post-login redirect target.
        :param link_for: Userid to link to, for a linking flow.
        """
        self.state = state
        self.provider_id = provider_id
        self.code_verifier = code_verifier
        self.nonce = nonce
        self.came_from = came_from
        self.link_for = link_for
        self.created = datetime.now(UTC)

    @property
    def expired(self) -> bool:
        """Report whether the attempt has aged out.

        :returns: Whether more than :data:`ATTEMPT_TTL` has passed.
        """
        return datetime.now(UTC) - self.created > ATTEMPT_TTL

    def serialize(self) -> dict[str, Any]:
        """Render the attempt for session storage.

        :returns: JSON-ready mapping.
        """
        return {
            "state": self.state,
            "provider_id": self.provider_id,
            "code_verifier": self.code_verifier,
            "nonce": self.nonce,
            "came_from": self.came_from,
            "link_for": self.link_for,
            "created": self.created.isoformat(),
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> "FlowAttempt":
        """Rebuild an attempt from session storage.

        :param data: Mapping as produced by :meth:`serialize`.
        :returns: The attempt.
        """
        attempt = cls(
            state=data["state"],
            provider_id=data["provider_id"],
            code_verifier=data["code_verifier"],
            nonce=data["nonce"],
            came_from=data.get("came_from", ""),
            link_for=data.get("link_for"),
        )
        attempt.created = datetime.fromisoformat(data["created"])
        return attempt


def validate_came_from(came_from: str, portal_url: str) -> str:
    """Reduce a post-login redirect target to something safe (S6).

    Anything that is not inside the portal is dropped rather than corrected:
    a redirect an attacker chose is not made safe by rewriting its host.

    :param came_from: Requested redirect target.
    :param portal_url: Absolute URL of the portal.
    :returns: The target, or ``""`` when it is not safe to use.
    """
    if not came_from:
        return ""
    parsed = urlparse(came_from)
    if not parsed.scheme and not parsed.netloc:
        # A relative path stays inside the site by construction, but a
        # protocol-relative URL ("//evil.example") also parses with no
        # scheme -- and urlparse puts its host in netloc, so it is caught.
        return came_from
    portal = urlparse(portal_url)
    if (parsed.scheme, parsed.netloc) != (portal.scheme, portal.netloc):
        logger.info("Refused off-site came_from %r", came_from)
        return ""
    if not parsed.path.startswith(portal.path):
        logger.info("Refused out-of-portal came_from %r", came_from)
        return ""
    return came_from


class FlowManager:
    """Starts and finishes authorization-code flows for one request."""

    def __init__(self, session: dict[str, Any], portal_url: str) -> None:
        """Bind the manager to a session and a portal.

        :param session: Mutable mapping surviving between the two requests of
            a flow -- in Plone, the browser session.
        :param portal_url: Absolute URL of the portal.
        """
        self.session = session
        self.portal_url = portal_url

    # ------------------------------------------------------------------
    # Attempt bookkeeping
    # ------------------------------------------------------------------

    def _attempts(self) -> dict[str, Any]:
        """Return the pending attempts, dropping expired ones.

        :returns: Mapping of state to serialized attempt.
        """
        attempts = self.session.get(SESSION_KEY) or {}
        live = {
            state: data
            for state, data in attempts.items()
            if not FlowAttempt.deserialize(data).expired
        }
        if len(live) != len(attempts):
            self.session[SESSION_KEY] = live
        return live

    def _store(self, attempt: FlowAttempt) -> None:
        """Persist an attempt against the session.

        :param attempt: The attempt to remember.
        """
        attempts = self._attempts()
        attempts[attempt.state] = attempt.serialize()
        self.session[SESSION_KEY] = attempts

    def pop(self, state: str) -> FlowAttempt:
        """Consume an attempt, refusing anything that does not match (S1).

        Single-use by construction: the attempt is removed whether or not the
        rest of the callback succeeds, so a replayed ``state`` finds nothing.

        :param state: The ``state`` echoed back by the provider.
        :returns: The matching attempt.
        :raises FlowError: When the state is unknown, expired or replayed --
            all of which are reported identically, so a caller cannot probe
            which states exist.
        """
        attempts = self._attempts()
        data = attempts.pop(state, None)
        self.session[SESSION_KEY] = attempts
        if data is None:
            raise FlowError("Unknown or expired authorization state")
        return FlowAttempt.deserialize(data)

    # ------------------------------------------------------------------
    # Starting a flow
    # ------------------------------------------------------------------

    def start(
        self,
        provider: ProviderConfig,
        redirect_uri: str,
        metadata: dict[str, Any],
        came_from: str = "",
        link_for: str | None = None,
    ) -> str:
        """Build the authorize URL for a provider and remember the attempt.

        :param provider: The configured provider.
        :param redirect_uri: Absolute callback URL registered with the
            provider.
        :param metadata: Provider metadata, normally from discovery; must
            carry ``authorization_endpoint``.
        :param came_from: Requested post-login redirect, validated here (S6).
        :param link_for: Userid to link to, for a linking flow.
        :returns: The URL to send the user to.
        :raises FlowError: When the metadata carries no authorize endpoint.
        """
        endpoint = metadata.get("authorization_endpoint")
        if not endpoint:
            raise FlowError(
                f"{provider.provider_id}: metadata has no authorization_endpoint"
            )

        client = self._client(provider, redirect_uri)
        code_verifier = secrets.token_urlsafe(64)
        nonce = secrets.token_urlsafe(32)

        url, state = client.create_authorization_url(
            endpoint,
            code_verifier=code_verifier,
            code_challenge_method=CODE_CHALLENGE_METHOD,
            nonce=nonce,
        )
        self._store(
            FlowAttempt(
                state=state,
                provider_id=provider.provider_id,
                code_verifier=code_verifier,
                nonce=nonce,
                came_from=validate_came_from(came_from, self.portal_url),
                link_for=link_for,
            )
        )
        return url

    # ------------------------------------------------------------------
    # Finishing a flow
    # ------------------------------------------------------------------

    def finish(
        self,
        provider: ProviderConfig,
        redirect_uri: str,
        metadata: dict[str, Any],
        state: str,
        code: str,
    ) -> tuple[FlowAttempt, dict[str, Any]]:
        """Exchange an authorization code for the provider's claims.

        :param provider: The configured provider.
        :param redirect_uri: The same callback URL used to start the flow.
        :param metadata: Provider metadata; must carry ``token_endpoint``.
        :param state: The ``state`` echoed back by the provider.
        :param code: The authorization code.
        :returns: The consumed attempt and the raw claims payload.
        :raises FlowError: When the attempt is unknown, the provider does not
            match, or the exchange yields nothing usable.
        """
        attempt = self.pop(state)
        if attempt.provider_id != provider.provider_id:
            # A code issued for provider A must never be redeemed at B.
            raise FlowError("Authorization state does not match this provider")

        endpoint = metadata.get("token_endpoint")
        if not endpoint:
            raise FlowError(f"{provider.provider_id}: metadata has no token_endpoint")

        client = self._client(provider, redirect_uri)
        token = client.fetch_token(
            endpoint,
            code=code,
            code_verifier=attempt.code_verifier,
            redirect_uri=redirect_uri,
        )
        payload = self._claims(client, token, provider, metadata, attempt)
        return attempt, payload

    def _claims(
        self,
        client: OAuth2Session,
        token: dict[str, Any],
        provider: ProviderConfig,
        metadata: dict[str, Any],
        attempt: FlowAttempt,
    ) -> dict[str, Any]:
        """Read the user's claims out of a token response.

        Prefers the ``id_token`` when the provider issued one -- it is signed
        and carries the nonce -- and falls back to the userinfo endpoint for
        plain OAuth2 providers such as GitHub.

        :param client: The authlib client holding the token.
        :param token: The token response.
        :param provider: The configured provider.
        :param metadata: Provider metadata.
        :param attempt: The consumed attempt, for nonce checking.
        :returns: The raw claims payload.
        :raises FlowError: When no claims can be obtained.
        """
        if "id_token" in token:
            return self._id_token_claims(token, provider, metadata, attempt)
        userinfo_endpoint = metadata.get("userinfo_endpoint")
        if not userinfo_endpoint:
            raise FlowError("Provider returned no id_token and exposes no userinfo")
        response = client.get(userinfo_endpoint)
        response.raise_for_status()
        return response.json()

    def _id_token_claims(
        self,
        token: dict[str, Any],
        provider: ProviderConfig,
        metadata: dict[str, Any],
        attempt: FlowAttempt,
    ) -> dict[str, Any]:
        """Validate an ``id_token`` and return its claims.

        Signature, issuer, audience and expiry are checked by authlib; the
        nonce is checked against the attempt, which is what ties the token to
        the session that started the flow (S1).

        :param token: The token response.
        :param provider: The configured provider, naming the audience.
        :param metadata: Provider metadata, carrying ``jwks`` and ``issuer``.
        :param attempt: The consumed attempt.
        :returns: The validated claims.
        :raises FlowError: When validation fails.
        """
        from authlib.jose import JsonWebToken
        from authlib.jose.errors import JoseError

        jwks = metadata.get("jwks")
        if not jwks:
            raise FlowError("Provider issued an id_token but exposes no JWKS")
        audience = self._client_id(provider)
        try:
            claims = JsonWebToken(["RS256", "ES256", "RS512"]).decode(
                token["id_token"],
                key=jwks,
                claims_options={
                    "iss": {"essential": True, "value": metadata.get("issuer")},
                    "aud": {"essential": True, "value": audience},
                    "nonce": {"essential": True, "value": attempt.nonce},
                },
            )
            claims.validate()
        except JoseError as exc:
            raise FlowError(f"id_token rejected: {exc}") from exc
        return dict(claims)

    @staticmethod
    def _client_id(provider: ProviderConfig) -> str:
        """Return the client id the id_token audience must match.

        Read from the provider's own configuration, not from the discovery
        document: the audience of an ``id_token`` is the client *we*
        authenticated as, and the provider does not get to name it.

        An empty client id is refused rather than passed on, because authlib
        reads ``{"value": ""}`` as "no constraint" -- so a misconfigured
        provider would silently disable the audience check and accept a token
        minted for any other client (S1).

        :param provider: The configured provider.
        :returns: The client id.
        :raises FlowError: When the provider has no client id configured.
        """
        client_id = provider.config.get("client_id", "")
        if not client_id:
            raise FlowError(f"{provider.provider_id}: no client_id configured")
        return client_id

    @staticmethod
    def _client(provider: ProviderConfig, redirect_uri: str) -> OAuth2Session:
        """Build an authlib client for a provider.

        :param provider: The configured provider.
        :param redirect_uri: Absolute callback URL.
        :returns: The authlib session.
        """
        config = provider.config
        return OAuth2Session(
            client_id=config.get("client_id", ""),
            client_secret=config.get("client_secret", ""),
            scope=config.get("scope", ""),
            redirect_uri=redirect_uri,
            code_challenge_method=CODE_CHALLENGE_METHOD,
        )
