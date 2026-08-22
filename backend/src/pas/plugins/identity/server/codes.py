"""Authorization codes.

The one thing this layer genuinely has to persist. Access tokens are
self-encoded and write nothing (C7), but an authorization code must be
single-use, and "single-use" is a claim about something remembered: the only
way to refuse the second redemption is to have recorded the first.

Codes are short-lived by design. RFC 6749 permits ten minutes and recommends
much less; OAuth 2.1 says the same more firmly. The window only has to cover a
browser redirect and the back-channel exchange that follows it, so it is set
in seconds rather than minutes.

PKCE lives here rather than at the endpoint because the challenge is recorded
at issuance and the verifier arrives at redemption; keeping both halves in one
place is what makes it impossible to check one without the other.
"""

from BTrees.OOBTree import OOBTree
from datetime import datetime
from datetime import timedelta
from datetime import UTC
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.server.interfaces import ServerError
from persistent import Persistent

import base64
import hashlib
import secrets


#: How long a code is good for, in seconds. Long enough for a redirect and
#: the exchange behind it, short enough that a code left in a proxy log or a
#: Referer header is worthless by the time anybody reads it.
CODE_TTL = 60

#: Bytes of entropy in a code.
CODE_BYTES = 32

#: The only PKCE method this server accepts. ``plain`` is in the RFC and is
#: worth nothing: it puts the verifier in the authorization request, which is
#: the exact place PKCE exists to protect.
CHALLENGE_METHOD = "S256"


class CodeError(ServerError):
    """An authorization code cannot be issued or redeemed."""


def _s256(verifier: str) -> str:
    """Return the S256 challenge for a verifier.

    :param verifier: The PKCE code verifier.
    :returns: Base64url-encoded SHA-256 of the verifier, unpadded, which is
        what RFC 7636 specifies.
    """
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class AuthorizationCode(Persistent):
    """One issued authorization code.

    :ivar client_id: The client the code was issued to.
    :ivar subject: The Plone userid that authorized it.
    :ivar redirect_uri: The URI the code was issued for. Recorded because RFC
        6749 requires the token request to present the same one, which is what
        stops a code obtained through one registered URI being redeemed as
        though it had come through another.
    :ivar scope: The granted scopes.
    :ivar challenge: The PKCE code challenge, empty when none was sent.
    :ivar expires_at: When the code stops being redeemable.
    """

    def __init__(
        self,
        client_id: str,
        subject: str,
        redirect_uri: str,
        scope: str = "",
        challenge: str = "",
        expires_at: datetime | None = None,
    ) -> None:
        """Record an issued code.

        :param client_id: The client the code is for.
        :param subject: The userid that authorized it.
        :param redirect_uri: The redirect URI used.
        :param scope: Granted scopes.
        :param challenge: PKCE code challenge.
        :param expires_at: Expiry; computed from :data:`CODE_TTL` by default.
        """
        self.client_id = client_id
        self.subject = subject
        self.redirect_uri = redirect_uri
        self.scope = scope
        self.challenge = challenge
        self.expires_at = expires_at or (
            datetime.now(UTC) + timedelta(seconds=CODE_TTL)
        )

    def is_expired(self, now: datetime | None = None) -> bool:
        """Whether the code has expired.

        :param now: The moment to judge against; the present by default.
        :returns: Whether it is too late to redeem this code.
        """
        return (now or datetime.now(UTC)) >= self.expires_at

    def serialize(self) -> JSONDict:
        """Render the code for a debugging view.

        Deliberately does not include the code itself -- this object is what
        the code maps *to*, and the mapping key is the secret.

        :returns: JSON-ready mapping.
        """
        return {
            "client_id": self.client_id,
            "subject": self.subject,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "pkce": bool(self.challenge),
            "expires_at": self.expires_at.isoformat(),
        }


class AuthorizationCodeStore(Persistent):
    """Issued authorization codes, burned on redemption."""

    def __init__(self) -> None:
        """Create an empty store."""
        self._codes: OOBTree = OOBTree()

    def _sweep(self, now: datetime | None = None) -> None:
        """Drop codes that can no longer be redeemed.

        Called on every write so the store cannot grow without bound in a
        site where most authorization requests are abandoned rather than
        completed -- which is the normal case, not the exception.

        :param now: The moment to judge against.
        """
        moment = now or datetime.now(UTC)
        for key in [k for k, v in self._codes.items() if v.is_expired(moment)]:
            del self._codes[key]

    def issue(
        self,
        client_id: str,
        subject: str,
        redirect_uri: str,
        scope: str = "",
        challenge: str = "",
    ) -> str:
        """Issue a code.

        :param client_id: The client the code is for.
        :param subject: The userid authorizing it.
        :param redirect_uri: The redirect URI in use.
        :param scope: Granted scopes.
        :param challenge: PKCE code challenge, empty when none was sent.
        :returns: The code, which is the only copy: the store maps it to the
            grant and nothing recovers it afterwards.
        """
        self._sweep()
        code = secrets.token_urlsafe(CODE_BYTES)
        self._codes[code] = AuthorizationCode(
            client_id=client_id,
            subject=subject,
            redirect_uri=redirect_uri,
            scope=scope,
            challenge=challenge,
        )
        return code

    def redeem(
        self,
        code: str,
        client_id: str,
        redirect_uri: str,
        verifier: str = "",
    ) -> AuthorizationCode:
        """Redeem a code, burning it.

        The code is deleted before any of the checks that can fail. A code
        that was presented is spent whether or not the presentation was
        correct: leaving a failed attempt redeemable is what turns one leaked
        code into an unlimited number of guesses at the verifier.

        :param code: The code as presented.
        :param client_id: The client presenting it.
        :param redirect_uri: The redirect URI presented with it.
        :param verifier: The PKCE code verifier.
        :returns: The redeemed grant.
        :raises CodeError: When the code is unknown, spent, expired, issued to
            another client, issued for another redirect URI, or the verifier
            does not match the recorded challenge. One exception for all of
            them: a client that can tell "wrong verifier" from "unknown code"
            can enumerate.
        """
        grant = self._codes.get(code)
        if grant is None:
            raise CodeError("The authorization code was refused")
        del self._codes[code]

        if grant.is_expired():
            raise CodeError("The authorization code was refused")
        if grant.client_id != client_id:
            raise CodeError("The authorization code was refused")
        if grant.redirect_uri != redirect_uri:
            raise CodeError("The authorization code was refused")
        if grant.challenge:
            if not verifier or _s256(verifier) != grant.challenge:
                raise CodeError("The authorization code was refused")
        elif verifier:
            # A verifier for a grant that recorded no challenge means the
            # authorization request and the token request disagree about
            # whether PKCE was in play. Refusing is the only safe reading:
            # accepting it lets an attacker who intercepted a non-PKCE code
            # dress the exchange up as a PKCE one.
            raise CodeError("The authorization code was refused")
        return grant

    def count(self) -> int:
        """Return how many codes are outstanding.

        :returns: Number of live codes, expired ones included until the next
            sweep.
        """
        return len(self._codes)


class ChallengeError(CodeError):
    """A PKCE challenge is missing or unusable."""


def check_challenge(challenge: str, method: str, required: bool) -> str:
    """Validate the PKCE parameters of an authorization request.

    :param challenge: The ``code_challenge`` parameter, possibly empty.
    :param method: The ``code_challenge_method`` parameter, possibly empty.
    :param required: Whether this client must use PKCE (S8: public ones do).
    :returns: The challenge to record with the code, empty when none was sent
        and none was required.
    :raises ChallengeError: When PKCE is required and absent, or when a
        method other than S256 is asked for.
    """
    if not challenge:
        if required:
            raise ChallengeError("This client must use PKCE")
        return ""
    if method and method != CHALLENGE_METHOD:
        raise ChallengeError(f"Unsupported code_challenge_method: {method}")
    if not method:
        # RFC 7636 defaults the method to `plain` when it is omitted, which
        # this server does not accept at all. Saying so is better than
        # silently treating the challenge as S256 and failing at redemption
        # with something that reads like a client bug.
        raise ChallengeError("code_challenge_method must be S256")
    return challenge


def make_verifier() -> tuple[str, str]:
    """Return a PKCE verifier and its S256 challenge.

    Test and documentation helper: the server never generates these, clients
    do. It lives here so the one implementation of S256 is the one exercised.

    :returns: ``(verifier, challenge)``.
    """
    verifier = secrets.token_urlsafe(64)
    return verifier, _s256(verifier)
