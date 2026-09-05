"""The database connection the SQL audit sink writes through.

One engine per process, built the first time something asks for it, from a
DSN read out of the environment.

Why the environment and not the registry
========================================

A DSN carries a password, and the registry is the wrong place for one here.
It is exported by GenericSetup, readable by anyone who can reach the control
panel, and kept in the ``Data.fs`` that gets copied to a staging site. The
package already refuses to put provider secrets into an export for exactly
that reason, and says so: *"the secrets have to travel separately, by whatever
means your deployment already uses for secrets."* An environment variable is
what a deployment already uses.

The consequence is that this sink is configured where the process is
configured rather than through the web, which is the same place a database
connection is configured for every other application in the stack.

Why a transaction manager of its own
====================================

``zope.sqlalchemy`` exists to join a SQLAlchemy session to Zope's transaction,
so that a database write and a ZODB write commit together. That is the right
default for application data and the wrong one here.

Auditing must never be the reason a request fails. That is a guarantee this
package already makes and tests: :func:`pas.plugins.identity.core.audit.record`
swallows and logs whatever a sink raises, precisely so a bookkeeping problem
cannot become an outage. Joining the request's transaction would route around
it -- the failure would surface at commit, long after ``record`` returned, and
would abort the login it was auditing. A database on the far side of a network
makes that likely rather than theoretical.

So the session is registered against a transaction manager of this module's
own, and committed inside the write. Two consequences worth stating plainly:

* An audit row is committed even if the request that produced it later fails.
  For an *attempt* log this is right: the attempt happened, and a log that
  quietly forgets attempts whose requests died is not much of an audit log.
* A row is written before the ZODB changes it describes are durable. The log
  records attempts and outcomes, not the state of the site, so nothing here
  reads back its own writes.
"""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

import os
import threading
import transaction
import zope.sqlalchemy


#: Environment variable holding the SQLAlchemy URL to write to. Unset means
#: this sink has nothing to write to, which it reports rather than guesses at.
DSN_VARIABLE = "IDENTITY_AUDIT_DSN"

#: Guards building the engine. Two threads answering two logins at once must
#: not build two engines, each with its own pool.
_lock = threading.Lock()

#: The process-wide engine, and the session factory bound to it.
_engine: Engine | None = None
_factory: sessionmaker | None = None

#: The transaction manager audit writes commit through. Deliberately not the
#: one Zope uses for the request; see the module docstring.
#:
#: Thread-local, because a Zope server answers several requests at once and a
#: single shared transaction would have two logins committing each other's
#: work. Implicit rather than explicit: SQLAlchemy acquires its connection
#: when it feels like it, and an explicit manager raises ``NoTransaction`` the
#: moment that happens outside a block this module opened.
manager = transaction.ThreadTransactionManager()


def dsn() -> str | None:
    """Return the configured database URL.

    :returns: The URL, or ``None`` when the variable is unset or empty.
    """
    return os.environ.get(DSN_VARIABLE) or None


def engine() -> Engine | None:
    """Return the process-wide engine, building it on first use.

    Built lazily rather than at import: importing this module must not open a
    connection, or a site with the extra installed and the sink unconfigured
    would fail to start.

    :returns: The engine, or ``None`` when no DSN is configured.
    """
    global _engine, _factory

    if _engine is not None:
        return _engine

    url = dsn()
    if url is None:
        return None

    with _lock:
        if _engine is None:
            # ``pool_pre_ping`` because the connections in this pool are idle
            # between logins, which is exactly how long a database restart or
            # a firewall's idle timeout takes to make one stale. Without it
            # the first login after a quiet night raises instead of
            # reconnecting.
            built = create_engine(url, pool_pre_ping=True, future=True)
            factory = sessionmaker(bind=built, future=True)
            zope.sqlalchemy.register(factory, transaction_manager=manager)
            _engine, _factory = built, factory
    return _engine


def session() -> Session | None:
    """Return a session for one audit write.

    :returns: A new session, or ``None`` when no DSN is configured.
    """
    if engine() is None:
        return None
    assert _factory is not None  # noqa: S101 - engine() sets both together
    return _factory()


def reset() -> None:
    """Forget the engine, so the next write builds a new one.

    Exists for the test suite, which points the sink at a fresh SQLite
    database per test and would otherwise get the first one for the whole
    run.
    """
    global _engine, _factory

    with _lock:
        if _engine is not None:
            _engine.dispose()
        _engine = None
        _factory = None
