"""Recorded consent.

What the user agreed to, so they are not asked again. The alternative --
prompting on every authorization request -- makes an existing session
worthless: the whole reason a relying party sends a browser here rather than
asking for a password is that the answer should already be known.

Consent is recorded per ``(userid, client)`` and remembers the scopes. A
client that later asks for more is asked again, for the whole set rather than
the difference, because "also allow X" is a sentence people agree to without
reading what they already allowed.

Unlike the authorization codes this store lives next to, consent is durable:
it is the only thing in the ``[server]`` layer that is meant to outlive the
request that created it, and the only reason the layer needs real storage
rather than a sixty-second scratch pad.

Consent can be withdrawn, and the withdrawal is what makes the record worth
keeping: :meth:`ConsentStore.for_user` is the account screen's read and
:meth:`ConsentStore.forget` is its delete. Forgetting an agreement only
decides what happens the *next* time that client asks, though -- it ends
nothing already issued -- so the endpoint that calls it revokes the client's
refresh tokens for that user in the same breath. Access tokens are
self-encoded with no denylist and live out their lifetime whatever anybody
withdraws; that is the cost of the design, and the screen says so rather than
implying a cutoff it cannot deliver.
"""

from BTrees.OOBTree import OOBTree
from datetime import datetime
from datetime import UTC
from persistent import Persistent


class ConsentRecord(Persistent):
    """One user's standing agreement with one client.

    :ivar scopes: The scopes agreed to.
    :ivar granted_at: When the agreement was last given.
    """

    def __init__(self, scopes: set[str], granted_at: datetime | None = None) -> None:
        """Record an agreement.

        :param scopes: The scopes agreed to.
        :param granted_at: When; the present by default.
        """
        self.scopes = frozenset(scopes)
        self.granted_at = granted_at or datetime.now(UTC)

    def covers(self, scopes: set[str]) -> bool:
        """Whether this agreement already covers a request.

        :param scopes: The scopes being asked for.
        :returns: Whether every one of them was agreed to.
        """
        return scopes <= self.scopes


class ConsentStore(Persistent):
    """Standing consent, keyed by user and client."""

    def __init__(self) -> None:
        """Create an empty store."""
        self._grants: OOBTree = OOBTree()

    def granted(self, userid: str, client_id: str, scope: str = "") -> bool:
        """Whether this user has already agreed to this client and scope.

        A client asking for nothing at all still needs a record: an empty
        scope does not mean an empty request, it means the client wants a
        token that speaks for this user. Being asked once is the point.

        :param userid: The Plone userid.
        :param client_id: The client.
        :param scope: Space-separated scopes being asked for.
        :returns: Whether the authorization can proceed without prompting.
        """
        record = self._grants.get((userid, client_id))
        if record is None:
            return False
        return record.covers(set(scope.split()))

    def record(self, userid: str, client_id: str, scope: str = "") -> ConsentRecord:
        """Record an agreement, replacing any earlier one.

        Replacing rather than merging: the user was shown the whole scope
        list and agreed to that, so that list is the agreement. Adding to a
        set they were never shown in full is how consent screens end up
        recording more than anybody said yes to.

        :param userid: The Plone userid.
        :param client_id: The client.
        :param scope: Space-separated scopes agreed to.
        :returns: The stored record.
        """
        entry = ConsentRecord(set(scope.split()))
        self._grants[(userid, client_id)] = entry
        return entry

    def for_user(self, userid: str) -> list[tuple[str, ConsentRecord]]:
        """Return every agreement this user has standing.

        What the account screen lists: the applications that can ask this
        server for a token speaking for this person, without asking them
        again.

        The whole store is walked rather than a per-user index consulted.
        The keys are ``(userid, client_id)`` tuples in an OOBTree, so a range
        query would work and is deliberately not used: this runs when one
        person opens one page, the store holds one record per user *per
        client they have ever authorized*, and an index would be a second
        structure to keep true for no measurable gain.

        :param userid: The Plone userid.
        :returns: ``(client_id, record)`` pairs, newest agreement first, then
            by client id so the order is stable when two were granted in the
            same moment -- which the demo stack manages routinely.
        """
        mine = [
            (client_id, record)
            for (owner, client_id), record in self._grants.items()
            if owner == userid
        ]
        mine.sort(key=lambda pair: (-pair[1].granted_at.timestamp(), pair[0]))
        return mine

    def forget(self, userid: str, client_id: str) -> bool:
        """Withdraw one agreement.

        The client is not blocked: it may ask again, and the user will be
        prompted as they were the first time. Blocking is a different
        feature, and one an operator does with the client registry rather
        than one a user does to an application.

        :param userid: The Plone userid.
        :param client_id: The client to forget.
        :returns: Whether there was an agreement to forget. False is not an
            error -- it is what a second withdrawal of the same grant looks
            like, and a caller that treats it as one turns a double-click
            into a failure.
        """
        if (userid, client_id) not in self._grants:
            return False
        del self._grants[(userid, client_id)]
        return True
