"""Refresh tokens, rotated on every use.

The second thing this layer persists, and for the same reason as the first:
an access token is self-encoded and proves itself (C7), but a refresh token
has to be *revocable and single-use*, and both of those are claims about
something remembered.

Rotation means the token you present is destroyed and a different one comes
back. On its own that buys very little -- an attacker holding a stolen copy
simply uses it first, and the legitimate client is the one that finds its
token rejected. What makes rotation worth doing is **reuse detection**: a
token that has already been spent turning up again means two parties hold the
same token, and exactly one of them is entitled to it. Since there is no way
to tell which, the whole family is revoked and both are sent back to the
authorization endpoint, where a human is involved again.

That is why spent tokens are remembered rather than simply deleted. A store
that forgot them could not tell a replay from a token that never existed, and
would answer both with the same shrug.
"""

from BTrees.OOBTree import OOBTree
from datetime import datetime
from datetime import timedelta
from datetime import UTC
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.server.interfaces import ServerError
from persistent import Persistent
from plone import api
from uuid import uuid4

import secrets


#: Registry key holding the refresh-token lifetime, in seconds.
TTL_RECORD = "pas.plugins.identity.server_refresh_token_ttl"

#: Default lifetime: fourteen days. Long enough that a client checking in
#: daily never sends a human back to the login page, short enough that an
#: abandoned integration stops working inside a sprint rather than a year.
DEFAULT_TTL = 60 * 60 * 24 * 14

#: Bytes of entropy in a refresh token.
TOKEN_BYTES = 32


class RefreshError(ServerError):
    """A refresh token cannot be issued or redeemed."""


def get_ttl() -> int:
    """Return the refresh-token lifetime in seconds.

    :returns: The configured lifetime, or :data:`DEFAULT_TTL`.
    """
    return (
        api.portal.get_registry_record(TTL_RECORD, default=DEFAULT_TTL) or DEFAULT_TTL
    )


class RefreshToken(Persistent):
    """One issued refresh token.

    :ivar client_id: The client it was issued to.
    :ivar subject: The Plone userid it acts for.
    :ivar scope: The granted scopes.
    :ivar family: Identifier shared by every token descended from one
        authorization. Rotation keeps it; revocation works on it.
    :ivar expires_at: When it stops being redeemable.
    """

    def __init__(
        self,
        client_id: str,
        subject: str,
        scope: str = "",
        family: str = "",
        expires_at: datetime | None = None,
    ) -> None:
        """Record an issued refresh token.

        :param client_id: The client it is for.
        :param subject: The userid it acts for.
        :param scope: Granted scopes.
        :param family: The rotation family; a fresh one by default.
        :param expires_at: Expiry; computed from the configured TTL by
            default.
        """
        self.client_id = client_id
        self.subject = subject
        self.scope = scope
        self.family = family or uuid4().hex
        self.expires_at = expires_at or (
            datetime.now(UTC) + timedelta(seconds=get_ttl())
        )

    def is_expired(self, now: datetime | None = None) -> bool:
        """Whether the token has expired.

        :param now: The moment to judge against; the present by default.
        :returns: Whether it is too late to redeem this token.
        """
        return (now or datetime.now(UTC)) >= self.expires_at

    def serialize(self) -> JSONDict:
        """Render the token for a debugging view.

        Not including the token itself: this object is what the token maps
        *to*, and the mapping key is the secret.

        :returns: JSON-ready mapping.
        """
        return {
            "client_id": self.client_id,
            "subject": self.subject,
            "scope": self.scope,
            "family": self.family,
            "expires_at": self.expires_at.isoformat(),
        }


class RefreshTokenStore(Persistent):
    """Refresh tokens, rotated on use and revoked on replay."""

    def __init__(self) -> None:
        """Create an empty store."""
        self._tokens: OOBTree = OOBTree()
        #: Tokens already spent, mapped to their family and expiry. Kept so a
        #: replay is distinguishable from a token that never existed.
        self._spent: OOBTree = OOBTree()

    def _sweep(self, now: datetime | None = None) -> None:
        """Drop everything that can no longer matter.

        A spent token is kept only as long as the live one it was exchanged
        for could have been: past that, a replay of it is refused by expiry
        anyway and remembering it buys nothing.

        :param now: The moment to judge against.
        """
        moment = now or datetime.now(UTC)
        for token in [t for t, v in self._tokens.items() if v.is_expired(moment)]:
            del self._tokens[token]
        for token in [t for t, (_f, exp) in self._spent.items() if moment >= exp]:
            del self._spent[token]

    def issue(
        self,
        client_id: str,
        subject: str,
        scope: str = "",
        family: str = "",
    ) -> str:
        """Issue a refresh token.

        :param client_id: The client it is for.
        :param subject: The userid it acts for.
        :param scope: Granted scopes.
        :param family: Rotation family to continue; a new one by default.
        :returns: The token, which is the only copy.
        """
        self._sweep()
        token = secrets.token_urlsafe(TOKEN_BYTES)
        self._tokens[token] = RefreshToken(
            client_id=client_id,
            subject=subject,
            scope=scope,
            family=family,
        )
        return token

    def revoke_family(self, family: str) -> int:
        """Revoke every live token descended from one authorization.

        :param family: The family identifier.
        :returns: How many live tokens were revoked.
        """
        doomed = [t for t, v in self._tokens.items() if v.family == family]
        for token in doomed:
            del self._tokens[token]
        return len(doomed)

    def rotate(self, token: str, client_id: str) -> tuple[str, RefreshToken]:
        """Redeem a refresh token and issue its replacement.

        :param token: The token as presented.
        :param client_id: The client presenting it, which must be the one it
            was issued to. A refresh token is a bearer credential, so without
            this check a client that obtained somebody else's could refresh
            it into a token of its own.
        :returns: The replacement token and the grant it carries.
        :raises RefreshError: When the token is unknown, expired, issued to
            another client, or already spent. One message for all of them: a
            client that can tell "already used" from "never existed" learns
            whether a token it stole has been rotated since.
        """
        # Deliberately no sweep first. Sweeping would delete an expired token
        # before this could look at it, so the expiry check below would never
        # run and expiry would be enforced by a housekeeping routine instead
        # of by the redemption path. ``issue`` sweeps, and this method ends by
        # calling it, so the store is still kept bounded.
        spent = self._spent.get(token)
        if spent is not None:
            # Two parties hold this token and exactly one is entitled to it.
            # There is no way to tell which, so neither keeps access: the
            # family dies and both are sent back to the authorization
            # endpoint, where a human is involved again.
            self.revoke_family(spent[0])
            raise RefreshError("The refresh token was refused")

        grant = self._tokens.get(token)
        if grant is None:
            raise RefreshError("The refresh token was refused")
        if grant.client_id != client_id:
            raise RefreshError("The refresh token was refused")

        del self._tokens[token]
        self._spent[token] = (grant.family, grant.expires_at)
        if grant.is_expired():
            raise RefreshError("The refresh token was refused")

        replacement = self.issue(
            client_id=grant.client_id,
            subject=grant.subject,
            scope=grant.scope,
            family=grant.family,
        )
        return replacement, grant

    def count(self) -> int:
        """Return how many refresh tokens are live.

        :returns: Number of redeemable tokens.
        """
        return len(self._tokens)
