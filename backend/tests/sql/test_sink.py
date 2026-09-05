"""The audit sink that writes to a relational database.

Run against SQLite, which needs no driver and no service. PostgreSQL is what
the sink is written for and what the demo stack runs; nothing here is
SQLite-specific beyond the URL, and the schema uses no dialect's extensions.
"""

from pas.plugins.identity.core.audit import AUTHENTICATED
from pas.plugins.identity.core.audit import DEFAULT_SINK
from pas.plugins.identity.core.audit import entries as audit_entries
from pas.plugins.identity.core.audit import FLOW_REFUSED
from pas.plugins.identity.core.audit import record
from pas.plugins.identity.core.audit import SINKS_RECORD
from pas.plugins.identity.core.audit import source
from pas.plugins.identity.core.interfaces import IAuditSink
from pas.plugins.identity.core.interfaces import IAuditSource
from pas.plugins.identity.sql import engine as engine_module
from pas.plugins.identity.sql import SINK_NAME
from pas.plugins.identity.sql import SQLAuditSink
from plone import api
from zope.component import getUtility
from zope.interface.verify import verifyObject

import pytest


@pytest.fixture(scope="class")
def portal(portal_class):
    """Return the portal."""
    yield portal_class


class SQLCase:
    """A fresh SQLite database per test, and the sink pointed at it.

    Not a test class. The engine is process-wide and built once, so every
    test has to reset it or the second one writes to the first one's
    database.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, tmp_path, monkeypatch) -> None:
        self.portal = portal
        self.database = tmp_path / "audit.db"
        monkeypatch.setenv(engine_module.DSN_VARIABLE, f"sqlite:///{self.database}")
        engine_module.reset()
        self.sink = getUtility(IAuditSink, name=SINK_NAME)
        self.sink._ready = False
        yield
        engine_module.reset()
        api.portal.set_registry_record(SINKS_RECORD, (DEFAULT_SINK,))

    def use_sql(self, *names: str) -> None:
        """Point the site at the SQL sink, and whatever else is named.

        :param names: Extra sink names, recorded to after the SQL one.
        """
        api.portal.set_registry_record(SINKS_RECORD, (SINK_NAME, *names))


class TestTheSinkIsRegistered(SQLCase):
    """Registered by the layer's ZCML whenever SQLAlchemy is importable."""

    def test_it_is_there(self):
        """The extra being installed is what registers it."""
        assert isinstance(self.sink, SQLAuditSink)

    def test_it_writes(self):
        """It provides the sink interface."""
        assert verifyObject(IAuditSink, self.sink)

    def test_it_reads_back(self):
        """And unlike the log sink, the source interface too: a database is
        somewhere a site can query."""
        assert verifyObject(IAuditSource, self.sink)


class TestWritingAndReading(SQLCase):
    """A row per event, read back newest first."""

    def test_an_event_becomes_a_row(self):
        """The simplest thing the sink does."""
        self.use_sql()

        record("userid-1", AUTHENTICATED, "dex", True)

        assert len(self.sink.entries("userid-1")) == 1

    def test_the_row_carries_the_facts(self):
        """Event, provider and outcome are the point of a row."""
        self.use_sql()

        record("userid-1", AUTHENTICATED, "dex", True, {"reason": "why"})

        row = self.sink.entries("userid-1")[0]
        assert (row.event, row.provider, row.success) == (
            AUTHENTICATED,
            "dex",
            True,
        )
        assert row.detail == {"reason": "why"}

    def test_a_failure_is_recorded_too(self):
        """A log of successes is not an audit log."""
        self.use_sql()

        record("userid-1", FLOW_REFUSED, "dex", False)

        assert self.sink.entries("userid-1")[0].success is False

    def test_rows_come_back_newest_first(self):
        """Which is the order every caller reads in."""
        self.use_sql()
        record("userid-1", AUTHENTICATED, "dex", True)
        record("userid-1", FLOW_REFUSED, "dex", False)

        events = [row.event for row in self.sink.entries("userid-1")]

        assert events == [FLOW_REFUSED, AUTHENTICATED]

    def test_per_user_isolation(self):
        """Asking about one account answers about that account."""
        self.use_sql()
        record("userid-1", AUTHENTICATED, "dex", True)
        record("userid-2", AUTHENTICATED, "dex", True)

        assert len(self.sink.entries("userid-1")) == 1

    def test_site_wide_returns_everything(self):
        """No userid means the whole site."""
        self.use_sql()
        record("userid-1", AUTHENTICATED, "dex", True)
        record("userid-2", AUTHENTICATED, "dex", True)

        assert len(self.sink.entries()) == 2

    def test_an_unattributed_event_is_a_null_userid(self):
        """SQL has a spelling for "no value", so the ZODB log's sentinel
        bucket does not need carrying across."""
        self.use_sql()

        record(None, FLOW_REFUSED, "dex", False)

        assert self.sink.entries()[0].userid is None

    def test_an_unattributed_event_is_not_returned_for_a_user(self):
        """And a NULL userid belongs to nobody rather than to everybody."""
        self.use_sql()
        record(None, FLOW_REFUSED, "dex", False)

        assert self.sink.entries("userid-1") == []

    def test_the_timestamp_is_timezone_aware(self):
        """A log read across two deployments in two zones is unreadable
        otherwise."""
        self.use_sql()

        record("userid-1", AUTHENTICATED, "dex", True)

        assert self.sink.entries("userid-1")[0].timestamp.tzinfo is not None


class TestARowLooksLikeAnEntry(SQLCase):
    """Callers read whatever the configured source hands them, so a row has
    to be indistinguishable from a ZODB entry."""

    def test_it_serializes_the_same_keys(self):
        """The mapping ``@audit-log`` renders."""
        self.use_sql()
        record("userid-1", AUTHENTICATED, "dex", True, {"reason": "why"})

        rendered = self.sink.entries("userid-1")[0].serialize()

        assert set(rendered) == {
            "event",
            "provider",
            "success",
            "timestamp",
            "detail",
        }

    def test_the_timestamp_serializes_as_a_string(self):
        """As the ZODB entry's does."""
        self.use_sql()
        record("userid-1", AUTHENTICATED, "dex", True)

        rendered = self.sink.entries("userid-1")[0].serialize()

        assert isinstance(rendered["timestamp"], str)

    def test_rows_are_readable_once_the_session_is_gone(self):
        """The caller reads them after ``entries`` returns, so every column
        has to be loaded by then rather than lazily."""
        self.use_sql()
        record("userid-1", AUTHENTICATED, "dex", True)

        rows = self.sink.entries("userid-1")

        assert rows[0].serialize()["event"] == AUTHENTICATED

    def test_a_read_does_not_poison_the_next_write(self):
        """Reading joins the transaction. Leaving it open would keep the
        closed session attached as a data manager, and the next write's
        commit would try to commit that one too."""
        self.use_sql()
        record("userid-1", AUTHENTICATED, "dex", True)

        self.sink.entries("userid-1")
        record("userid-2", AUTHENTICATED, "dex", True)

        assert len(self.sink.entries("userid-2")) == 1

    def test_reading_returns_its_connection_to_the_pool(self):
        """A read joins the transaction as much as a write does. Without
        ending it the connection stays checked out until something else in
        this thread commits, which on a Zope worker is a connection leaked
        per audit-log view."""
        self.use_sql()
        record("userid-1", AUTHENTICATED, "dex", True)

        self.sink.entries("userid-1")

        assert engine_module.engine().pool.checkedout() == 0


class TestItIsAConfiguredSource(SQLCase):
    """Naming it in the setting is what makes it the store reads answer
    from."""

    def test_it_is_chosen_as_the_source(self):
        """Listed first, so it answers rather than the ZODB log."""
        self.use_sql()

        assert isinstance(source(), SQLAuditSink)

    def test_reads_go_through_it(self):
        """And the module-level helper returns its rows."""
        self.use_sql()

        record("userid-1", AUTHENTICATED, "dex", True)

        assert len(audit_entries("userid-1")) == 1

    def test_recording_to_both_writes_to_both(self):
        """The combination an operator wants: keep the ZODB log, and keep a
        copy somewhere unbounded."""
        self.use_sql(DEFAULT_SINK)

        record("userid-both", AUTHENTICATED, "dex", True)

        assert len(self.sink.entries("userid-both")) == 1
        plugin = getUtility(IAuditSink, name=DEFAULT_SINK)
        assert len(plugin.entries("userid-both")) == 1


class TestWithoutADatabase(SQLCase):
    """A sink with nothing to write to must not take a login down."""

    # Takes ``_setup`` as an argument rather than relying on base-class
    # ordering: pytest does not promise to run an inherited autouse fixture
    # before one declared on the subclass, and without this the base fixture
    # sets the variable back after this one deleted it.
    @pytest.fixture(autouse=True)
    def _no_dsn(self, _setup, monkeypatch) -> None:
        monkeypatch.delenv(engine_module.DSN_VARIABLE, raising=False)
        engine_module.reset()

    def test_recording_is_a_no_op(self):
        """Rather than a traceback out of a login."""
        self.use_sql()

        record("userid-1", AUTHENTICATED, "dex", True)

    def test_recording_says_so(self, caplog):
        """An operator has to find out somehow, and a silent drop is how a
        site ends up believing it has records it never wrote."""
        self.use_sql()

        record("userid-1", AUTHENTICATED, "dex", True)

        assert engine_module.DSN_VARIABLE in caplog.text

    def test_reading_is_empty_rather_than_an_error(self):
        """A sink that cannot reach its store has nothing to say about what
        is in it, and raising would take the control panel with it."""
        assert self.sink.entries("userid-1") == []

    def test_there_is_no_engine(self):
        """Built lazily, so an unconfigured sink opens no connection and a
        site with the extra installed still starts."""
        assert engine_module.engine() is None


class TestTheSchema(SQLCase):
    """Created on first use, and not otherwise touched."""

    def test_the_table_is_created_on_first_write(self):
        """A fresh database needs no migration step to start recording."""
        self.use_sql()

        record("userid-1", AUTHENTICATED, "dex", True)

        assert self.database.exists()

    def test_creating_twice_is_harmless(self):
        """``checkfirst`` means a second instance against the same database
        finds the table rather than colliding with it."""
        self.use_sql()
        record("userid-1", AUTHENTICATED, "dex", True)

        other = SQLAuditSink()
        other.record("userid-2", AUTHENTICATED, "dex", True)

        assert len(self.sink.entries()) == 2

    def test_reading_a_fresh_database_creates_it_too(self):
        """Reading before anything was written must answer empty rather than
        raise about a missing table."""
        assert self.sink.entries("userid-1") == []
