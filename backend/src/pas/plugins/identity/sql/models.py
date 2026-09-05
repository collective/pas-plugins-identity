"""The table authentication events are written to.

One table, and the shape is the audit entry's rather than anything clever: a
row per event, with the fields every consumer filters on as columns and the
free-form context as JSON beside them.

``detail`` stays JSON rather than being flattened into columns because it is
free-form by contract. A new event name may carry a key nothing has seen
before, and a schema that had to grow a column for it would make adding an
event a migration.
"""

from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy import Index
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column


class Base(DeclarativeBase):
    """Declarative base for this package's tables."""


class AuditRow(Base):
    """One authentication event.

    Nullable ``userid`` rather than a sentinel: a callback with an unknown
    state has, by construction, no user to attribute it to, and those are
    exactly the rows an operator investigating an attack wants. SQL already
    has a spelling for "no value", so the ZODB log's ``UNATTRIBUTED`` bucket
    does not need carrying across.
    """

    __tablename__ = "identity_audit"

    id: Mapped[int] = mapped_column(primary_key=True)

    #: When the event happened, in UTC. Timezone-aware: a log read across
    #: two deployments in two zones is unreadable otherwise.
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    #: Which site wrote the row. A database is a place several Plone sites
    #: can point at, and a log that cannot say which of them a login was for
    #: is not much use once they share one.
    site: Mapped[str | None] = mapped_column(String(255), nullable=True)

    #: Userid the event concerns, ``NULL`` when it could not be resolved.
    userid: Mapped[str | None] = mapped_column(String(255), nullable=True)

    #: Event name, from the vocabulary the package publishes.
    event: Mapped[str] = mapped_column(String(64))

    #: Provider id involved.
    provider: Mapped[str] = mapped_column(String(255))

    #: Whether the attempt succeeded.
    success: Mapped[bool] = mapped_column()

    #: Extra, non-credential context. Never tokens.
    detail: Mapped[dict] = mapped_column(JSON, default=dict)

    __table_args__ = (
        # The two questions this log is asked: what happened to this account,
        # and what happened lately. Both want the newest rows first, which is
        # the order every caller reads in.
        Index("ix_identity_audit_userid_timestamp", "userid", "timestamp"),
        Index("ix_identity_audit_timestamp", "timestamp"),
    )

    def serialize(self) -> dict:
        """Render the row for an API response.

        The same mapping ``AuditEntry.serialize`` returns, because callers
        read whatever the configured source hands them and must not be able
        to tell which store answered. That duck type -- ``event``,
        ``success``, ``timestamp`` and this method -- is the contract between
        a source and the rest of the package.

        :returns: JSON-ready mapping.
        """
        return {
            "event": self.event,
            "provider": self.provider,
            "success": self.success,
            "timestamp": self.timestamp.isoformat(),
            "detail": dict(self.detail or {}),
        }

    def __repr__(self) -> str:
        """Return a debugging representation.

        :returns: The event, provider and outcome.
        """
        return f"<AuditRow {self.event} {self.provider} success={self.success}>"
