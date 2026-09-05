"""Authentication records in a relational database.

The optional ``[sql]`` layer. Nothing in core imports it, and CI fails the
build if that stops being true, so a site installing no extra carries no
SQLAlchemy.

What it is for
==============

The built-in log is bounded and purged on every write, which is the right
default and the wrong thing for a site that has to keep authentication records
longer than the bounds allow, query them with something other than Python, or
put them where the rest of its estate already looks. This sink is the answer
to all three, and it provides
:class:`~pas.plugins.identity.core.interfaces.IAuditSource` as well as the
sink interface, so a site can read its own records back through the control
panel and ``@audit-log`` exactly as before.

Turning it on
=============

Install the extra, point ``IDENTITY_AUDIT_DSN`` at a database, and add ``sql``
to ``pas.plugins.identity.audit_sinks``. Recording to ``plugin`` and ``sql``
together is a reasonable thing to want; listing ``sql`` first is what makes it
the store the control panel reads.

PostgreSQL is what this is written against and what the demo stack runs.
SQLite is what the test suite uses, because it needs no driver and no service.

The schema
==========

Created on first use if it is not there, which is deliberate and limited: it
is ``CREATE TABLE IF NOT EXISTS`` for one table, not a migration framework.
A deployment that would rather own its schema creates the table itself and
nothing here will disagree with it. What this package will not do is silently
alter a table it finds.
"""

from datetime import datetime
from datetime import UTC
from pas.plugins.identity import logger
from pas.plugins.identity.core.interfaces import IAuditSink
from pas.plugins.identity.core.interfaces import IAuditSource
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.sql import engine as engine_module
from pas.plugins.identity.sql.models import AuditRow
from pas.plugins.identity.sql.models import Base
from plone import api
from sqlalchemy import select
from zope.interface import implementer


#: Name this sink is registered under.
SINK_NAME = "sql"

#: How many rows a site-wide read pulls back before the service trims it.
#: The table is unbounded, unlike the ZODB log, so a read has to bound itself
#: or the first query on a year-old database returns the year.
READ_LIMIT = 1000


def _site_id() -> str | None:
    """Return the id of the Plone site being served.

    :returns: The site id, or ``None`` outside a site. Stored on every row so
        a database shared by several sites can still say which one a login
        was for.
    """
    try:
        return api.portal.get().getId()
    except api.exc.CannotGetPortalError:
        return None


@implementer(IAuditSink, IAuditSource)
class SQLAuditSink:
    """Write authentication events to a relational database, and read them
    back."""

    def __init__(self) -> None:
        """Start with no schema created."""
        self._ready = False

    def _prepare(self, session) -> None:
        """Create the table if this process has not yet seen it.

        :param session: The session whose bind to create against.
        """
        if self._ready:
            return
        Base.metadata.create_all(session.get_bind(), checkfirst=True)
        self._ready = True

    def record(
        self,
        userid: str | None,
        event: str,
        provider: str,
        success: bool,
        detail: JSONDict | None = None,
    ) -> None:
        """Write one authentication event as a row.

        Committed through this layer's own transaction manager rather than
        the request's, so a database that is slow or unreachable cannot fail
        the login it is auditing. See :mod:`pas.plugins.identity.sql.engine`
        for why that is worth the row being durable slightly early.

        :param userid: Userid the event concerns, ``None`` when unresolved.
        :param event: Event name.
        :param provider: Provider id involved.
        :param success: Whether the attempt succeeded.
        :param detail: Extra, non-credential context. Never tokens.
        :raises Exception: Whatever the database raised. The caller in
            :func:`pas.plugins.identity.core.audit.record` logs and swallows
            it; raising here rather than swallowing is what lets it say which
            sink failed.
        """
        session = engine_module.session()
        if session is None:
            logger.warning(
                "The sql audit sink has no %s configured; dropping a %r entry",
                engine_module.DSN_VARIABLE,
                event,
            )
            return

        with session:
            self._prepare(session)
            session.add(
                AuditRow(
                    timestamp=datetime.now(UTC),
                    site=_site_id(),
                    userid=userid,
                    event=event,
                    provider=provider,
                    success=success,
                    detail=dict(detail or {}),
                )
            )
            engine_module.manager.commit()

    def entries(self, userid: str | None = None) -> list:
        """Return recorded rows, newest first.

        :param userid: Restrict to one user; ``None`` returns everything this
            site recorded.
        :returns: The rows, capped at :data:`READ_LIMIT`. Empty when no
            database is configured -- a sink that cannot reach its store has
            nothing to say about what is in it, and saying so by raising
            would take the control panel down with it.
        """
        session = engine_module.session()
        if session is None:
            return []

        with session:
            self._prepare(session)
            query = (
                select(AuditRow)
                .where(AuditRow.site == _site_id())
                .order_by(AuditRow.timestamp.desc())
                .limit(READ_LIMIT)
            )
            if userid is not None:
                query = query.where(AuditRow.userid == userid)
            rows = list(session.scalars(query))
            for row in rows:
                # SQLite has no timezone-aware column type, so a value
                # written as UTC comes back naive. PostgreSQL returns it
                # aware. Everything here writes UTC, so stamping it back on
                # is a restatement rather than a guess, and it keeps
                # ``serialize`` producing the same offset-carrying string
                # whichever database answered.
                if row.timestamp.tzinfo is None:
                    row.timestamp = row.timestamp.replace(tzinfo=UTC)
            # Nothing is done to the transaction here, and nothing needs to
            # be. Closing the session -- which the ``with`` above does on the
            # way out -- returns its connection to the pool and detaches it
            # from the transaction, so a read neither leaks a connection nor
            # leaves a closed session for the next write's commit to trip
            # over. Both of those are asserted rather than assumed, because
            # an explicit abort here looks obviously correct and is dead
            # code: removing it changes no test.
            #
            # Every column the caller reads is loaded by the query above and
            # none is lazy, so the rows stay readable once the session is
            # gone without being expunged first.
            return rows
