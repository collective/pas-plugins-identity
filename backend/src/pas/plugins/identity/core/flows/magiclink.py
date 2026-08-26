"""Magic-link tokens.

A magic link is a signed, single-use, short-lived assertion that whoever holds
it controls a mailbox. The signature is authlib's -- no hand-rolled JWT --
the key comes from the same derivation as the flow cookie, and the ``jti`` is
burned server-side on first use so the second click fails.

Three properties, each of which is the whole point of one part of this module:

* **Signed** -- the address cannot be edited by the recipient.
* **Single-use** -- a link forwarded, logged by a mail gateway, or sitting in
  a shared inbox is worth one login, not a permanent key.
* **Short-lived** -- the default TTL is 15 minutes, and the burn store
  only has to remember tokens for that long.

Rate limiting lives here too, because the send endpoint is the one an attacker
can make Plone send mail from: without it, this package is an open relay
aimed at anybody's inbox.
"""

from BTrees.OOBTree import OOBTree
from datetime import datetime
from datetime import timedelta
from datetime import UTC
from pas.plugins.identity import logger
from pas.plugins.identity.core.flows.session import signing_keys
from pas.plugins.identity.core.interfaces import FlowError
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.interfaces import RateLimited
from persistent import Persistent

import secrets


#: Signing algorithm. Symmetric is right here: the issuer and the verifier are
#: the same Plone site, and there is nothing for a third party to check.
ALGORITHM = "HS256"

#: A token minted to sign somebody in.
PURPOSE_LOGIN = "magic-link"

#: A token minted to prove a mailbox belongs to somebody already signed in.
#:
#: Kept apart from :data:`PURPOSE_LOGIN` deliberately. The two are minted from
#: the same key and look identical on the wire, so without the distinction a
#: link mailed to confirm an address would sign its holder in as whoever owns
#: that address -- which is precisely the account takeover the linking flow's
#: same-session check exists to prevent.
PURPOSE_LINK = "identity-link"

#: Default lifetime, in seconds. Capped at fifteen minutes; see
#: :data:`MAX_TTL`.
DEFAULT_TTL = 900

#: Hard ceiling, whatever an operator configures. A magic link that lives
#: longer than this stops being a login and becomes a bearer credential.
MAX_TTL = 900

#: Default number of links one address may request per hour.
DEFAULT_RATE_LIMIT = 5

#: How many requests one IP may make per hour, whatever address it names.
#: Separate from the per-address limit: an attacker enumerating mailboxes uses
#: a different address every time and would never trip a per-address counter.
DEFAULT_IP_RATE_LIMIT = 20

#: Window both limits are measured over.
RATE_WINDOW = timedelta(hours=1)


def _key() -> bytes:
    """Return the current signing key.

    :returns: The derived key, shared with the flow cookie's derivation.
    """
    return signing_keys()[0]


def _all_keys() -> list[bytes]:
    """Return every key a token may have been signed with.

    :returns: Derived keys, current first, so a rotation does not invalidate
        links already in flight.
    """
    return signing_keys()


def ttl_for(seconds: int | None) -> int:
    """Clamp a configured lifetime to something defensible.

    :param seconds: Configured lifetime, or ``None``.
    :returns: The lifetime to use, never above :data:`MAX_TTL`.
    """
    if not seconds or seconds <= 0:
        return DEFAULT_TTL
    return min(int(seconds), MAX_TTL)


def issue(
    address: str,
    ttl: int | None = None,
    *,
    purpose: str = PURPOSE_LOGIN,
    link_for: str | None = None,
) -> tuple[str, str]:
    """Mint a magic-link token for an address.

    :param address: The address being proven; stored lowercased.
    :param ttl: Lifetime in seconds; clamped by :func:`ttl_for`.
    :param purpose: What the token may be redeemed for; one of
        :data:`PURPOSE_LOGIN` or :data:`PURPOSE_LINK`.
    :param link_for: Userid the link was minted for, when the purpose is
        :data:`PURPOSE_LINK`. Carried in the token rather than in the flow
        cookie because the mail may well be opened in another browser, where
        no cookie of ours exists.
    :returns: The encoded token and its ``jti``.
    """
    from authlib.jose import JsonWebToken

    now = datetime.now(UTC)
    lifetime = ttl_for(ttl)
    jti = secrets.token_urlsafe(24)
    payload = {
        "sub": address.lower(),
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=lifetime)).timestamp()),
        "purpose": purpose,
    }
    if link_for is not None:
        payload["link_for"] = link_for
    token = JsonWebToken([ALGORITHM]).encode({"alg": ALGORITHM}, payload, _key())
    return token.decode("utf-8"), jti


def verify(token: str, purposes: tuple[str, ...] = (PURPOSE_LOGIN,)) -> JSONDict:
    """Validate a magic-link token and return its claims.

    Signature, expiry and purpose are all checked here; the ``jti`` burn is
    the caller's job, because only the caller knows whether the login it
    guards actually went through.

    :param token: The encoded token.
    :param purposes: Purposes the caller is willing to accept. A caller that
        handles only one names only one: accepting both and branching
        afterwards is how a link token ends up signing somebody in.
    :returns: The validated claims.
    :raises FlowError: When the token is malformed, unsigned by us, expired,
        or was minted for something the caller does not accept.
    """
    from authlib.jose import JsonWebToken
    from authlib.jose.errors import JoseError

    decoder = JsonWebToken([ALGORITHM])
    for key in _all_keys():
        try:
            claims = decoder.decode(token, key=key)
            claims.validate()
        except JoseError:
            continue
        if claims.get("purpose") not in purposes:
            # A token minted for something else must not be usable here,
            # however impeccably it is signed.
            raise FlowError("Token was not issued for this purpose")
        return dict(claims)
    raise FlowError("Magic link is invalid or has expired")


class MagicLinkStore(Persistent):
    """Server-side state for magic links: burned tokens and rate counters.

    Both are bounded by time rather than by count, and both are swept on
    write, so nothing has to run on a schedule. The burn store only needs to
    remember a token until it would have expired anyway.
    """

    def __init__(self) -> None:
        """Create empty stores."""
        self._burned: OOBTree = OOBTree()
        self._requests: OOBTree = OOBTree()

    # ------------------------------------------------------------------
    # Single use
    # ------------------------------------------------------------------

    def burn(self, jti: str, expires_at: datetime) -> None:
        """Mark a token as spent.

        :param jti: The token id.
        :param expires_at: When the token would expire anyway, after which
            remembering it is pointless.
        """
        self._sweep_burned()
        self._burned[jti] = expires_at

    def is_burned(self, jti: str) -> bool:
        """Report whether a token has already been used.

        :param jti: The token id.
        :returns: Whether it was burned.
        """
        self._sweep_burned()
        return jti in self._burned

    def _sweep_burned(self) -> None:
        """Drop burn records for tokens that have expired anyway."""
        now = datetime.now(UTC)
        for jti in [j for j, expiry in self._burned.items() if expiry < now]:
            del self._burned[jti]

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def check_and_record(self, bucket: str, limit: int) -> None:
        """Count one request against a bucket, refusing over the limit.

        Counting happens *before* the mail is sent and is not rolled back if
        sending fails: a bounced send still cost the recipient an email, and
        an attacker must not get free retries by making delivery fail.

        :param bucket: What is being limited -- an address, or an IP.
        :param limit: How many requests are allowed in the window.
        :raises RateLimited: When the bucket is over its limit.
        """
        now = datetime.now(UTC)
        cutoff = now - RATE_WINDOW
        stamps = [s for s in self._requests.get(bucket, ()) if s > cutoff]
        if limit > 0 and len(stamps) >= limit:
            logger.info("Rate-limiting magic-link requests for %r", bucket)
            self._requests[bucket] = stamps
            raise RateLimited(f"Too many requests for {bucket}")
        stamps.append(now)
        self._requests[bucket] = stamps

    def requests_in_window(self, bucket: str) -> int:
        """Return how many requests a bucket has made in the window.

        :param bucket: The bucket to count.
        :returns: Number of requests still inside the window.
        """
        cutoff = datetime.now(UTC) - RATE_WINDOW
        return len([s for s in self._requests.get(bucket, ()) if s > cutoff])
