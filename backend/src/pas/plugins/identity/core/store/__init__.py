"""The identity store.

Two BTrees kept inside the PAS plugin object:

``_identities``
    ``"<provider>\\x00<subject>"`` -> userid. The forward map; the uniqueness
    of its keys is what keeps one identity pointing at one userid.
``_by_userid``
    userid -> ``PersistentList`` of :class:`IdentityRecord`. The reverse map,
    so listing a user's identities never scans the forward map.

Subjects are stored verbatim, except for ``provider="email"`` where they are
lowercased -- addresses are case-insensitive in their domain part and, in
practice, in their local part too, and a case-sensitive store would let the
same mailbox be linked twice.
"""

from BTrees.OOBTree import OOBTree
from datetime import datetime
from datetime import UTC
from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.interfaces import IdentityCollision
from pas.plugins.identity.core.interfaces import IIdentityStore
from pas.plugins.identity.core.interfaces import JSONDict
from persistent import Persistent
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from zope.interface import implementer


#: Provider id whose subjects are email addresses.
EMAIL_PROVIDER = "email"

#: Separator for the composite forward-map key. NUL cannot occur in a provider
#: id (they are identifiers) nor in a subject (providers emit printable text),
#: so the composite key is unambiguous.
_SEP = "\x00"


def normalize_subject(provider: str, subject: str) -> str:
    """Apply the store's case policy to a subject.

    :param provider: Provider id.
    :param subject: Raw provider-side subject identifier.
    :returns: The subject as it is stored and looked up.
    """
    return subject.lower() if provider == EMAIL_PROVIDER else subject


def _key(provider: str, subject: str) -> str:
    """Build the forward-map key for an identity.

    :param provider: Provider id.
    :param subject: Provider-side subject identifier.
    :returns: Composite key.
    """
    return f"{provider}{_SEP}{normalize_subject(provider, subject)}"


class IdentityRecord(Persistent):
    """One external identity owned by a userid.

    :ivar provider: Provider id.
    :ivar subject: Provider-side subject, normalized per the store's policy.
    :ivar created: When the identity was first linked.
    :ivar last_login: When it was last used to authenticate, or ``None``.
    :ivar claims: Snapshot of the normalized claims from the last refresh.
    :ivar groups: Local group ids this provider granted at the last login.
        The fence: a login only ever takes back what the same provider gave,
        so a group an administrator granted by hand is never touched, and a
        group revoked at the provider goes away without anyone editing
        anything. A class attribute so a record written before this existed
        reads as "granted nothing" rather than needing an upgrade step.
    """

    #: See :attr:`groups` in the class docstring.
    groups: tuple[str, ...] = ()

    def __init__(self, provider: str, subject: str, claims: Claims) -> None:
        """Create a record.

        :param provider: Provider id.
        :param subject: Provider-side subject identifier.
        :param claims: Normalized claims snapshot.
        """
        self.provider = provider
        self.subject = normalize_subject(provider, subject)
        self.created = datetime.now(UTC)
        self.last_login: datetime | None = None
        self.claims = PersistentMapping(claims)

    def serialize(self) -> JSONDict:
        """Render the record for an API response.

        Claims are included, credentials never are.

        :returns: JSON-ready mapping.
        """
        return {
            "provider": self.provider,
            "subject": self.subject,
            "created": self.created.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "claims": dict(self.claims),
            "groups": list(self.groups),
        }

    def __repr__(self) -> str:
        """Return a debugging representation.

        :returns: Provider and subject.
        """
        return f"<IdentityRecord {self.provider}:{self.subject}>"


@implementer(IIdentityStore)
class IdentityStore(Persistent):
    """Persistent implementation of :class:`IIdentityStore`."""

    def __init__(self) -> None:
        """Create empty forward and reverse maps."""
        self._identities: OOBTree = OOBTree()
        self._by_userid: OOBTree = OOBTree()

    def userid_for(self, provider: str, subject: str) -> str | None:
        """Resolve an external identity to a canonical userid.

        :param provider: Provider id.
        :param subject: Provider-side subject identifier.
        :returns: The userid, or ``None`` when unknown.
        """
        return self._identities.get(_key(provider, subject))

    def identities_for(self, userid: str) -> tuple[IdentityRecord, ...]:
        """Return every identity record owned by a userid.

        :param userid: Canonical Plone userid.
        :returns: Tuple of records, in link order.
        """
        return tuple(self._by_userid.get(userid, ()))

    def get(self, provider: str, subject: str) -> IdentityRecord | None:
        """Return the record for an identity.

        :param provider: Provider id.
        :param subject: Provider-side subject identifier.
        :returns: The record, or ``None`` when the identity is unknown.
        """
        userid = self.userid_for(provider, subject)
        if userid is None:
            return None
        normalized = normalize_subject(provider, subject)
        for record in self._by_userid[userid]:
            if record.provider == provider and record.subject == normalized:
                return record
        # Forward and reverse maps are written together; a hit in one without
        # the other means the ZODB state is corrupt.
        raise RuntimeError(  # pragma: no cover - can't-happen consistency guard
            f"Identity store inconsistent for {provider}:{normalized}"
        )

    def add(
        self, provider: str, subject: str, userid: str, claims: Claims
    ) -> IdentityRecord:
        """Link an external identity to a userid.

        :param provider: Provider id.
        :param subject: Provider-side subject identifier.
        :param userid: Canonical Plone userid.
        :param claims: Normalized claims snapshot.
        :returns: The stored record.
        :raises IdentityCollision: When the identity is already owned by a
            different userid. Re-adding an identity to the userid that
            already owns it is also a collision: the caller should have used
            :meth:`touch`.
        """
        key = _key(provider, subject)
        owner = self._identities.get(key)
        if owner is not None:
            raise IdentityCollision(
                f"{provider}:{normalize_subject(provider, subject)} is already "
                f"linked to {owner}"
            )
        record = IdentityRecord(provider, subject, claims)
        self._identities[key] = userid
        self._by_userid.setdefault(userid, PersistentList()).append(record)
        return record

    def remove(self, provider: str, subject: str) -> None:
        """Unlink an external identity.

        :param provider: Provider id.
        :param subject: Provider-side subject identifier.
        :raises KeyError: When the identity is unknown.
        """
        key = _key(provider, subject)
        userid = self._identities.get(key)
        if userid is None:
            raise KeyError(f"{provider}:{normalize_subject(provider, subject)}")
        normalized = normalize_subject(provider, subject)
        records = self._by_userid[userid]
        remaining = PersistentList(
            r
            for r in records
            if not (r.provider == provider and r.subject == normalized)
        )
        del self._identities[key]
        if remaining:
            self._by_userid[userid] = remaining
        else:
            del self._by_userid[userid]

    def touch(self, provider: str, subject: str, claims: Claims) -> IdentityRecord:
        """Record a successful login against an existing identity.

        Claims are refreshed on every login; profile-owned fields are
        protected downstream by the claims-sync subscriber, not here.

        :param provider: Provider id.
        :param subject: Provider-side subject identifier.
        :param claims: Fresh normalized claims.
        :returns: The updated record.
        :raises KeyError: When the identity is unknown.
        """
        record = self.get(provider, subject)
        if record is None:
            raise KeyError(f"{provider}:{normalize_subject(provider, subject)}")
        record.last_login = datetime.now(UTC)
        record.claims = PersistentMapping(claims)
        return record

    def userids(self) -> tuple[str, ...]:
        """Return every userid that owns at least one identity.

        :returns: Tuple of userids.
        """
        return tuple(self._by_userid.keys())

    def __len__(self) -> int:
        """Return the number of linked identities.

        :returns: Count of entries in the forward map.
        """
        return len(self._identities)
