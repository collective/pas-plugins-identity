"""OpenID Connect back-channel logout, received.

The provider tells this site that somebody's session there has ended, and this
site ends theirs here. No browser is involved: the provider POSTs a signed
*logout token* server to server, which is exactly why it works when the user
has already closed the tab.

Three things make this harder than it looks, and each is a decision recorded
below rather than a detail.

**Whose session.** The ``sub`` in a logout token is the *provider's* subject,
not a Plone userid -- this package mints uuid4 userids that no provider
has ever seen. The identity store is what turns one into the other, and a
logout for an identity this site has never seen is a success rather than an
error: there is nothing to end, and saying so would tell an unauthenticated
caller which subjects have accounts here.

**How a session ends.** A ``plone.session`` ticket is stateless and signed
from a keyring, so there is normally no way to end one person's session
without ending everyone's. ``plone.session`` has a switch for this --
``per_user_keyring`` -- which gives each user their own ring; clearing and
rotating that ring invalidates exactly their tickets. It is off by default,
so a site that wants back-channel logout has to turn it on, and this module
says so loudly rather than silently doing nothing.

**What cannot be undone.** Access tokens this site issued as an authorization
server are self-encoded and there is no denylist, so they live out their
lifetime. Refresh tokens *are* revocable, and the ``[server]`` layer revokes
them by subscribing to the event this module fires -- which is how the two
layers cooperate without core importing server.
"""

from BTrees.OOBTree import OOBTree
from datetime import datetime
from datetime import timedelta
from datetime import UTC
from pas.plugins.identity import logger
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.flows import metadata as flow_metadata
from pas.plugins.identity.core.interfaces import FlowError
from pas.plugins.identity.core.interfaces import JSONDict
from persistent import Persistent
from plone import api
from plone.keyring.interfaces import IKeyManager
from zope.component import getUtility


#: The event a logout token must declare, per OpenID Connect Back-Channel
#: Logout 1.0 §2.4. A token without it is some other kind of logout token and
#: acting on it would be acting on a message meant for something else.
LOGOUT_EVENT = "http://schemas.openid.net/event/backchannel-logout"

#: How long a spent ``jti`` is remembered. The specification says a replay
#: must be refused if the same ``jti`` was received "recently"; this is what
#: this package means by recently, and it comfortably exceeds any sane clock
#: skew between a provider and this site.
JTI_TTL = 600

#: Algorithms accepted on a logout token, matching what the flow accepts on
#: an ``id_token``. Listed rather than left open: an empty list lets a token
#: choose its own algorithm, which is how ``alg: none`` forgeries happen.
ALGORITHMS = ("RS256", "ES256", "RS512")


class LogoutError(Exception):
    """A logout token cannot be acted on."""


class LogoutJTIStore(Persistent):
    """Identifiers of logout tokens already acted on.

    Small and short-lived: a ``jti`` is remembered only long enough that
    replaying the token it belonged to is refused.
    """

    def __init__(self) -> None:
        """Create an empty store."""
        self._seen: OOBTree = OOBTree()

    def _sweep(self, now: datetime | None = None) -> None:
        """Forget identifiers that can no longer be replayed usefully.

        :param now: The moment to judge against.
        """
        moment = now or datetime.now(UTC)
        for jti in [j for j, expiry in self._seen.items() if moment >= expiry]:
            del self._seen[jti]

    def seen(self, jti: str) -> bool:
        """Whether this identifier has already been acted on.

        :param jti: The token identifier.
        :returns: Whether it is a replay.
        """
        expiry = self._seen.get(jti)
        return expiry is not None and datetime.now(UTC) < expiry

    def record(self, jti: str) -> None:
        """Remember an identifier as spent.

        :param jti: The token identifier.
        """
        self._sweep()
        self._seen[jti] = datetime.now(UTC) + timedelta(seconds=JTI_TTL)

    def count(self) -> int:
        """Return how many identifiers are remembered.

        :returns: Number of live entries.
        """
        return len(self._seen)


def _unverified_issuer(token: str) -> str:
    """Return the ``iss`` of a token without checking its signature.

    Reading a claim before verification looks alarming and is not: the issuer
    is *how the key to verify with is chosen*, exactly as ``kid`` is. Nothing
    is trusted on the strength of it -- a token naming a provider it was not
    signed by fails the signature check a moment later.

    :param token: The encoded logout token.
    :returns: The issuer, or the empty string when the token is unreadable.
    """
    import base64
    import json

    try:
        payload = token.split(".")[1]
        decoded = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        return json.loads(decoded).get("iss", "")
    except (IndexError, ValueError, TypeError):
        return ""


def provider_for_issuer(issuer: str):
    """Return the configured provider that issues under a given issuer.

    :param issuer: The issuer named by a token.
    :returns: The matching provider, or ``None``.
    """
    if not issuer:
        return None
    wanted = issuer.rstrip("/")
    for provider in get_providers():
        try:
            if flow_metadata.issuer_for(provider) == wanted:
                return provider
        except FlowError:
            # A provider whose issuer cannot be resolved is misconfigured,
            # and that is not this request's problem: it simply cannot be the
            # one that signed this token, and the next one may well be.
            continue
    return None


def validate_logout_token(token: str) -> tuple[str, JSONDict]:
    """Validate a logout token and return the provider it came from.

    :param token: The encoded logout token.
    :returns: The provider id and the validated claims.
    :raises LogoutError: When the token is not one this site should act on.
    """
    from authlib.jose import JsonWebToken
    from authlib.jose.errors import JoseError

    provider = provider_for_issuer(_unverified_issuer(token))
    if provider is None:
        raise LogoutError("No configured provider issues tokens under that issuer")

    metadata = flow_metadata.metadata_for(provider)
    jwks = metadata.get("jwks")
    if not jwks:
        raise LogoutError(f"{provider.provider_id}: provider exposes no JWKS")

    audience = (provider.config.get("client_id") or "").strip()
    if not audience:
        raise LogoutError(f"{provider.provider_id}: no client id configured")

    try:
        claims = JsonWebToken(list(ALGORITHMS)).decode(
            token,
            key=jwks,
            claims_options={
                "iss": {"essential": True, "value": metadata.get("issuer")},
                "aud": {"essential": True, "value": audience},
                "iat": {"essential": True},
                "jti": {"essential": True},
            },
        )
        claims.validate()
    except JoseError as exc:
        raise LogoutError(f"logout_token rejected: {exc}") from exc
    except (AttributeError, ValueError) as exc:
        raise LogoutError("logout_token rejected: unreadable") from exc

    claims = dict(claims)
    # Back-Channel Logout 1.0 §2.4: a logout token must say it is one, must identify a
    # session or a
    # subject, and must not carry a nonce -- the last because a nonce would
    # mean somebody is trying to pass an id_token off as a logout token.
    events = claims.get("events") or {}
    if LOGOUT_EVENT not in events:
        raise LogoutError("logout_token rejected: not a back-channel logout event")
    if "nonce" in claims:
        raise LogoutError("logout_token rejected: a logout token carries no nonce")
    if not claims.get("sub") and not claims.get("sid"):
        raise LogoutError("logout_token rejected: neither sub nor sid")
    return provider.provider_id, claims


def revoke_sessions(userid: str) -> bool:
    """End every ``plone.session`` ticket belonging to one user.

    Only possible when ``plone.session`` is configured with
    ``per_user_keyring``: without it every ticket in the site is signed from
    one ring, and the only way to invalidate this user's would be to
    invalidate everybody's. Refusing to do that quietly is the point of the
    return value.

    :param userid: The Plone userid whose sessions should end.
    :returns: Whether the sessions were actually ended.
    """
    session = getattr(api.portal.get_tool("acl_users"), "session", None)
    if session is None:  # pragma: no cover - can't-happen: Plone always has one
        logger.warning("No session plugin; cannot end sessions for %s", userid)
        return False
    if not getattr(session, "per_user_keyring", False):
        logger.error(
            "Back-channel logout cannot end %s's Plone session: the "
            "session plugin is not configured with 'per user keyring', so "
            "every ticket in this site is signed from one ring. Enable it "
            "on acl_users/session under 'Manage secrets'.",
            userid,
        )
        return False

    ring = session._getSecretKey(userid)
    manager = getUtility(IKeyManager)
    if ring not in manager:
        # The user has no ring yet, which means no ticket was ever signed for
        # them. Nothing to end, and nothing wrong.
        return True
    manager.clear(ring=ring)
    manager.rotate(ring=ring)
    logger.info("Back-channel logout ended Plone sessions for %s", userid)
    return True
