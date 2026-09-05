"""Integration tests for the audit log."""

from . import CLAIMS
from datetime import timedelta
from pas.plugins.identity.core import audit as audit_module
from pas.plugins.identity.core.audit import AuditLog
from pas.plugins.identity.core.audit import AUTHENTICATED
from pas.plugins.identity.core.audit import DEFAULT_SINK
from pas.plugins.identity.core.audit import EMAIL_VERIFIED
from pas.plugins.identity.core.audit import FLOW_REFUSED
from pas.plugins.identity.core.audit import IDENTITY_LINKED
from pas.plugins.identity.core.audit import IDENTITY_UNLINKED
from pas.plugins.identity.core.audit.logsink import LoggingAuditSink
from pas.plugins.identity.core.audit.logsink import logger as log_sink_logger
from pas.plugins.identity.core.audit.logsink import SINK_NAME as LOG_SINK_NAME
from pas.plugins.identity.core.audit import MAX_DAYS_RECORD
from pas.plugins.identity.core.audit import MAX_ENTRIES_RECORD
from pas.plugins.identity.core.audit import PluginAuditSink
from pas.plugins.identity.core.audit import entries as audit_entries
from pas.plugins.identity.core.audit import record
from pas.plugins.identity.core.audit import RECORD_PII_RECORD
from pas.plugins.identity.core.audit import sink_names
from pas.plugins.identity.core.audit import SINKS_RECORD
from pas.plugins.identity.core.audit import source
from pas.plugins.identity.core.audit import request_detail
from pas.plugins.identity.core.audit import UNATTRIBUTED
from pas.plugins.identity.core.events import EmailVerified
from pas.plugins.identity.core.events import ExternalIdentityAuthenticated
from pas.plugins.identity.core.events import IdentityLinked
from pas.plugins.identity.core.events import IdentityUnlinked
from pas.plugins.identity.core.events import UserClaimsRefreshed
from pas.plugins.identity.core.interfaces import IAuditSink
from pas.plugins.identity.core.interfaces import IAuditSource
from pas.plugins.identity.core.pas import PLUGIN_ID
from plone import api
from zope.component import getGlobalSiteManager
from zope.component import getUtility
from zope.event import notify
from zope.interface import alsoProvides
from zope.interface.verify import verifyObject

import logging
import pytest


#: The logger the log-only sink writes to.
LOGGER_NAME = log_sink_logger.name


@pytest.fixture(scope="class")
def portal(portal_class):
    """Return the portal."""
    yield portal_class


@pytest.fixture
def utility() -> IAuditSink:
    """Return the installed plugin's audit sink."""
    return getUtility(IAuditSink, name=DEFAULT_SINK)


class TestSinkRegistration:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, log, utility) -> None:
        self.portal = portal
        self.log = log
        self.utility = utility

    def test_sink_is_registered(self):
        """The default sink is what ``record`` finds."""
        assert isinstance(self.utility, PluginAuditSink)

    def test_sink_satisfies_its_interface(self):
        """A replacement sink knows exactly what it has to provide."""
        assert verifyObject(IAuditSink, self.utility)

    def test_sink_is_also_a_source(self):
        """The built-in sink is the one destination that can be read back,
        which is what lets the control panel show anything at all."""
        assert verifyObject(IAuditSource, self.utility)

    def test_nothing_is_registered_unnamed(self):
        """Registering by name is what makes a second sink an addition
        rather than a replacement, so there must be no anonymous one left
        for a lookup to find by accident."""
        from zope.component import queryUtility

        assert queryUtility(IAuditSink, default=None) is None

    def test_sink_writes_to_the_plugin_log(self):
        """The default sink is backed by the plugin's own store."""
        self.utility.record("userid-1", AUTHENTICATED, "dex", True)

        assert len(self.log.entries("userid-1")) == 1

    def test_sink_reads_back(self):
        """And reads through the same store."""
        self.log.record("userid-1", AUTHENTICATED, "dex", True)

        assert len(self.utility.entries("userid-1")) == 1


class TestRecording:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, log) -> None:
        self.portal = portal
        self.log = log

    def test_entry_carries_the_facts(self):
        """Event, provider and outcome are the point of an entry."""
        entry = self.log.record(
            "userid-1", AUTHENTICATED, "dex", True, {"subject": "s"}
        )

        assert entry.event == AUTHENTICATED
        assert entry.provider == "dex"
        assert entry.success is True
        assert entry.detail["subject"] == "s"
        assert entry.timestamp is not None

    def test_failures_are_recorded_too(self):
        """A refused attempt is the interesting kind."""
        self.log.record(None, "flow-refused", "dex", False, {"reason": "bad state"})

        entry = self.log.entries()[0]
        assert entry.success is False
        assert entry.detail["reason"] == "bad state"

    def test_unattributed_entries_are_kept(self):
        """A refusal has no userid, and must not be dropped for it."""
        self.log.record(None, "flow-refused", "dex", False)

        assert len(self.log.entries(UNATTRIBUTED)) == 1
        assert len(self.log.entries()) == 1

    def test_per_user_isolation(self):
        """One user's log is not another's."""
        self.log.record("userid-1", AUTHENTICATED, "dex", True)
        self.log.record("userid-2", AUTHENTICATED, "dex", True)

        assert len(self.log.entries("userid-1")) == 1
        assert len(self.log.entries("userid-2")) == 1
        assert len(self.log.entries()) == 2

    def test_unknown_user_has_no_entries(self):
        """Asking about a stranger is not an error."""
        assert self.log.entries("never-seen") == []

    def test_entries_are_newest_first(self):
        """An operator reads the top of the log."""
        for index in range(3):
            self.log.record("userid-1", AUTHENTICATED, "dex", True, {"n": index})

        assert [e.detail["n"] for e in self.log.entries("userid-1")] == [2, 1, 0]

    def test_entry_serializes(self):
        """The shape ``@audit-log`` will publish."""
        entry = self.log.record(
            "userid-1", AUTHENTICATED, "dex", True, {"subject": "s"}
        )

        payload = entry.serialize()

        assert payload["event"] == AUTHENTICATED
        assert payload["provider"] == "dex"
        assert payload["success"] is True
        assert payload["detail"] == {"subject": "s"}
        assert payload["timestamp"].startswith(str(entry.timestamp.year))

    def test_repr(self):
        """Debugging representation names the event."""
        entry = self.log.record("userid-1", AUTHENTICATED, "dex", True)

        assert AUTHENTICATED in repr(entry)


class TestBounds:
    """The log is bounded, and purged on write rather than on a
    schedule, so the bound holds without anything having to run."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, log) -> None:
        self.portal = portal
        self.log = log

    def test_entry_count_is_capped(self):
        """Write past the cap and the oldest are evicted."""
        api.portal.set_registry_record(MAX_ENTRIES_RECORD, 10)

        for index in range(15):
            self.log.record("userid-1", AUTHENTICATED, "dex", True, {"n": index})

        entries = self.log.entries("userid-1")
        assert len(entries) == 10
        assert [e.detail["n"] for e in entries][-1] == 5

    def test_the_plan_bound_holds(self):
        """Write 600, keep 500, oldest evicted."""
        api.portal.set_registry_record(MAX_ENTRIES_RECORD, 500)

        for index in range(600):
            self.log.record("userid-1", AUTHENTICATED, "dex", True, {"n": index})

        entries = self.log.entries("userid-1")
        assert len(entries) == 500
        assert [e.detail["n"] for e in entries][-1] == 100

    def test_old_entries_expire(self):
        """Age is the other bound."""
        api.portal.set_registry_record(MAX_DAYS_RECORD, 30)
        stale = self.log.record("userid-1", AUTHENTICATED, "dex", True)
        stale.timestamp = stale.timestamp - timedelta(days=31)

        self.log.record("userid-1", AUTHENTICATED, "dex", True)

        assert len(self.log.entries("userid-1")) == 1

    def test_recent_entries_survive(self):
        """And a day-old entry is not old."""
        api.portal.set_registry_record(MAX_DAYS_RECORD, 30)
        recent = self.log.record("userid-1", AUTHENTICATED, "dex", True)
        recent.timestamp = recent.timestamp - timedelta(days=1)

        self.log.record("userid-1", AUTHENTICATED, "dex", True)

        assert len(self.log.entries("userid-1")) == 2

    def test_zero_disables_the_count_bound(self):
        """An operator who wants everything can say so."""
        api.portal.set_registry_record(MAX_ENTRIES_RECORD, 0)

        for _ in range(20):
            self.log.record("userid-1", AUTHENTICATED, "dex", True)

        assert len(self.log.entries("userid-1")) == 20

    def test_zero_disables_the_age_bound(self):
        """Likewise for retention."""
        api.portal.set_registry_record(MAX_DAYS_RECORD, 0)
        stale = self.log.record("userid-1", AUTHENTICATED, "dex", True)
        stale.timestamp = stale.timestamp - timedelta(days=9999)

        self.log.record("userid-1", AUTHENTICATED, "dex", True)

        assert len(self.log.entries("userid-1")) == 2

    def test_missing_record_falls_back_to_the_default(self, monkeypatch):
        """A site whose registry lost the record still gets a bound."""
        monkeypatch.setattr(api.portal, "get_registry_record", lambda *a, **kw: None)

        assert audit_module._setting(MAX_ENTRIES_RECORD, 500) == 500


class TestPrivacy:
    """IP and user agent are personal data and are opt-in."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, http_request_class) -> None:
        self.portal = portal
        self.request = http_request_class

    def test_pii_is_off_by_default(self):
        """The default profile must not switch on data collection."""
        assert api.portal.get_registry_record(RECORD_PII_RECORD) is False

    def test_no_request_context_by_default(self):
        """With the flag off, nothing about the machine is stored."""
        assert request_detail(self.request) == {}

    def test_request_context_when_opted_in(self):
        """With it on, the operator gets what they asked for."""
        api.portal.set_registry_record(RECORD_PII_RECORD, True)
        self.request.environ["REMOTE_ADDR"] = "203.0.113.7"
        self.request.environ["HTTP_USER_AGENT"] = "test-agent"

        detail = request_detail(self.request)

        assert detail["ip"] == "203.0.113.7"
        assert detail["user_agent"] == "test-agent"

    def test_forwarded_for_wins(self):
        """Behind a proxy the socket address is the proxy's."""
        api.portal.set_registry_record(RECORD_PII_RECORD, True)
        self.request.environ["REMOTE_ADDR"] = "10.0.0.1"
        self.request.environ["HTTP_X_FORWARDED_FOR"] = "203.0.113.7"

        assert request_detail(self.request)["ip"] == "203.0.113.7"

    def test_no_request_yields_nothing(self):
        """Not every caller has a request."""
        api.portal.set_registry_record(RECORD_PII_RECORD, True)

        assert request_detail(None) == {}


class TestSubscribers:
    """Successes are recorded from the event contract."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, log) -> None:
        self.portal = portal
        self.log = log

    def test_authentication_is_recorded(self):
        """Every successful login leaves a trace."""
        notify(
            ExternalIdentityAuthenticated(
                "userid-1", "dex", "subject-1", CLAIMS, True, True
            )
        )

        entry = self.log.entries("userid-1")[0]
        assert entry.event == AUTHENTICATED
        assert entry.detail["is_new_user"] is True
        assert entry.detail["subject"] == "subject-1"

    def test_link_is_recorded(self):
        """Linking is a security-relevant act."""
        notify(IdentityLinked("userid-1", "github", "1234567", CLAIMS))

        assert self.log.entries("userid-1")[0].event == IDENTITY_LINKED

    def test_unlink_is_recorded(self):
        """So is unlinking."""
        notify(IdentityUnlinked("userid-1", "github", "1234567"))

        assert self.log.entries("userid-1")[0].event == IDENTITY_UNLINKED

    def test_email_verification_is_recorded_with_the_address(self):
        """An entry that will not say which address was verified is useless."""
        notify(EmailVerified("userid-1", "Erico@Plone.ORG"))

        entry = self.log.entries("userid-1")[0]
        assert entry.event == EMAIL_VERIFIED
        assert entry.detail["address"] == "erico@plone.org"

    def test_claims_refresh_records_no_claims(self):
        """The useful fact is that a refresh happened; the claims themselves
        are the user's personal data and change on every login."""
        notify(UserClaimsRefreshed("userid-1", "dex", CLAIMS))

        entry = self.log.entries("userid-1")[0]
        assert "claims" not in entry.detail
        assert entry.detail == {}


class TestNeverBreaksALogin:
    """A bookkeeping problem must not become an outage."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_a_failing_sink_is_swallowed(self, monkeypatch):
        """An unwritable audit log must not refuse the login it is auditing."""

        class Exploding:
            """A sink that always fails."""

            def record(self, *args, **kwargs):
                """Fail.

                :raises RuntimeError: Always.
                """
                raise RuntimeError("audit backend is down")

        # record() imports queryUtility at call time, so patching the module
        # attribute is what reaches it.
        import zope.component

        monkeypatch.setattr(
            zope.component, "queryUtility", lambda *a, **kw: Exploding()
        )

        record("userid-1", AUTHENTICATED, "dex", True)

    def test_no_sink_is_not_an_error(self, monkeypatch):
        """A site that deliberately unregistered the sink still works."""
        import zope.component

        monkeypatch.setattr(zope.component, "queryUtility", lambda *a, **kw: None)

        record("userid-1", AUTHENTICATED, "dex", True)


class TestSinkWithoutAPlugin:
    """Auditing must never be the reason a request fails, including on a
    Zope root or a site where the add-on is not installed."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, monkeypatch) -> None:
        self.portal = portal

        def missing(name):
            """Raise as a site without the add-on would.

            :param name: Tool name.
            :raises KeyError: Always.
            """
            raise KeyError(name)

        monkeypatch.setattr(api.portal, "get_tool", missing)

    def test_record_is_a_no_op(self):
        """Nothing to write to is not an error."""
        PluginAuditSink().record("userid-1", AUTHENTICATED, "dex", True)

    def test_entries_are_empty(self):
        """And reading gives nothing rather than raising."""
        assert PluginAuditSink().entries("userid-1") == []


class TestLazyLog:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_plugin_predating_the_audit_log_gains_one(self):
        """A plugin persisted before the audit log existed must not raise on
        first use; it gets a log the same way a fresh one does."""
        plugin = api.portal.get_tool("acl_users")[PLUGIN_ID]
        del plugin._audit

        log = plugin.audit

        assert isinstance(log, AuditLog)
        assert plugin.audit is log


class Recorder:
    """A sink that keeps what it was handed, and nothing more."""

    def __init__(self) -> None:
        """Start with nothing recorded."""
        self.written: list[tuple] = []

    def record(self, userid, event, provider, success, detail=None) -> None:
        """Keep the call.

        :param userid: Userid the event concerns.
        :param event: Event name.
        :param provider: Provider id.
        :param success: Whether the attempt succeeded.
        :param detail: Extra context.
        """
        self.written.append((userid, event, provider, success, detail))


class Readable(Recorder):
    """A sink that can also answer for what it kept."""

    def entries(self, userid=None) -> list:
        """Return what was recorded.

        :param userid: Restrict to one user; ``None`` returns everything.
        :returns: The matching calls.
        """
        if userid is None:
            return list(self.written)
        return [call for call in self.written if call[0] == userid]


class Exploding:
    """A sink that always fails."""

    def record(self, *args, **kwargs) -> None:
        """Fail.

        :raises RuntimeError: Always.
        """
        raise RuntimeError("audit backend is down")


class SinkCase:
    """Registering named sinks for the duration of one test.

    Not a test class. Named sinks are global-registry state, so every one
    registered here is unregistered again in teardown: a leaked sink would
    be recorded to by every later test in the run, and the failure would
    surface somewhere else entirely.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.registered: list[tuple[object, str]] = []
        yield
        registry = getGlobalSiteManager()
        for sink, name in self.registered:
            registry.unregisterUtility(sink, IAuditSink, name=name)
        api.portal.set_registry_record(SINKS_RECORD, ("plugin",))

    def register(self, name: str, sink: object, readable: bool = False):
        """Register one sink under a name for this test only.

        :param name: Utility name.
        :param sink: The sink.
        :param readable: Whether it should also provide ``IAuditSource``.
        :returns: The sink, for convenience.
        """
        provided = [IAuditSink] + ([IAuditSource] if readable else [])
        alsoProvides(sink, *provided)
        getGlobalSiteManager().registerUtility(sink, IAuditSink, name=name)
        self.registered.append((sink, name))
        return sink

    def configure(self, *names: str) -> None:
        """Point the site at these sinks, in this order.

        :param names: Utility names. Each must be registered: the field is a
            ``Choice`` over the registered sinks, so an unknown name is
            refused here exactly as it is in the control panel.
        """
        api.portal.set_registry_record(SINKS_RECORD, tuple(names))

    def drop(self, name: str) -> None:
        """Unregister a sink the site is still configured to use.

        The only way a configured name resolves to nothing: the setting was
        stored while the sink existed, and the extra providing it was removed
        afterwards. The field cannot be made to store an unknown name.

        :param name: Utility name to unregister.
        """
        for entry in list(self.registered):
            if entry[1] != name:
                continue
            getGlobalSiteManager().unregisterUtility(entry[0], IAuditSink, name=name)
            self.registered.remove(entry)


class TestWhichSinksASiteRecordsTo(SinkCase):
    """``audit_sinks`` names the destinations, and its absence means one."""

    def test_the_shipped_default_is_the_plugin_log(self):
        """Which is what the profile states."""
        assert sink_names() == (DEFAULT_SINK,)

    def test_an_empty_setting_falls_back(self):
        """An operator who clears the field has not asked to stop auditing;
        they have asked for the default, which is this site's own log."""
        self.configure()

        assert sink_names() == (DEFAULT_SINK,)

    def test_a_missing_record_falls_back(self, monkeypatch):
        """A site whose profile predates the record behaves as it did."""
        monkeypatch.setattr(api.portal, "get_registry_record", lambda *a, **kw: None)

        assert sink_names() == (DEFAULT_SINK,)

    def test_the_configured_order_is_kept(self):
        """Order decides which destination answers a read, so it is not a
        set."""
        self.register("first", Recorder())
        self.register("second", Recorder())
        self.configure("second", "first")

        assert sink_names() == ("second", "first")


class TestEveryConfiguredSinkGetsTheEvent(SinkCase):
    """Fan-out is the point: adding a destination adds, never replaces."""

    def test_a_single_extra_sink_receives_it(self):
        """The simplest case, and the one an operator tries first."""
        extra = self.register("extra", Recorder())
        self.configure("extra")

        record("userid-1", AUTHENTICATED, "dex", True)

        assert len(extra.written) == 1

    def test_all_of_them_receive_it(self):
        """Two destinations means two copies, not a choice between them."""
        one = self.register("one", Recorder())
        two = self.register("two", Recorder())
        self.configure("one", "two")

        record("userid-1", AUTHENTICATED, "dex", True)

        assert (len(one.written), len(two.written)) == (1, 1)

    def test_a_sink_not_configured_is_not_written_to(self):
        """Registering a sink installs it; naming it starts using it."""
        idle = self.register("idle", Recorder())
        self.configure(DEFAULT_SINK)

        record("userid-1", AUTHENTICATED, "dex", True)

        assert idle.written == []

    def test_the_plugin_log_still_receives_it_alongside(self):
        """The regression that matters: adding a database must not stop the
        control panel showing anything."""
        extra = self.register("extra", Recorder())
        self.configure(DEFAULT_SINK, "extra")

        record("userid-fanout", AUTHENTICATED, "dex", True)

        assert len(extra.written) == 1
        assert len(audit_entries("userid-fanout")) == 1

    def test_the_payload_is_the_same_for_each(self):
        """One event, recorded identically, rather than each sink being
        handed whatever the loop had left."""
        one = self.register("one", Recorder())
        two = self.register("two", Recorder())
        self.configure("one", "two")

        record("userid-1", AUTHENTICATED, "dex", True, {"reason": "why"})

        assert one.written == two.written


class TestOneBadSinkDoesNotStopTheRest(SinkCase):
    """A destination is not allowed to take the others down with it."""

    def test_a_failing_sink_does_not_stop_the_next(self):
        """The whole reason fan-out swallows per sink rather than per call."""
        self.register("boom", Exploding())
        after = self.register("after", Recorder())
        self.configure("boom", "after")

        record("userid-1", AUTHENTICATED, "dex", True)

        assert len(after.written) == 1

    def test_a_failing_sink_is_logged_with_its_name(self, caplog):
        """An operator has to know *which* destination is down."""
        self.register("boom", Exploding())
        self.configure("boom")

        record("userid-1", AUTHENTICATED, "dex", True)

        assert "boom" in caplog.text

    def test_a_name_that_no_longer_resolves_is_stepped_over(self):
        """An extra uninstalled after its sink was configured. The name
        stays in the registry record and resolves to nothing."""
        after = self.register("after", Recorder())
        self.register("departed", Recorder())
        self.configure("departed", "after")
        self.drop("departed")

        record("userid-1", AUTHENTICATED, "dex", True)

        assert len(after.written) == 1

    def test_a_name_that_no_longer_resolves_is_logged(self, caplog):
        """Silence would leave a site recording to fewer places than its
        operator believes."""
        self.register("departed", Recorder())
        self.configure("departed")
        self.drop("departed")

        record("userid-1", AUTHENTICATED, "dex", True)

        assert "departed" in caplog.text


class TestTheSettingRefusesAnUnknownSink(SinkCase):
    """The field is a ``Choice`` over what is registered, so a destination
    that does not exist cannot be stored in the first place."""

    def test_an_unknown_name_is_refused(self):
        """Which is the difference between a typo and a silent no-op."""
        with pytest.raises(Exception) as caught:
            self.configure("not-installed")

        assert "not-installed" in str(caught.value)

    def test_a_registered_name_is_accepted(self):
        """And registering the sink is all it takes to make it choosable."""
        self.register("arrived", Recorder())

        self.configure("arrived")

        assert sink_names() == ("arrived",)


class TestReadingComesFromASource(SinkCase):
    """Only a sink that provides ``IAuditSource`` answers a query."""

    def test_the_plugin_log_is_the_source_by_default(self):
        """Nothing configured means the built-in one."""
        assert isinstance(source(), PluginAuditSink)

    def test_the_first_readable_sink_wins(self):
        """Order is the operator's answer to which store is authoritative."""
        readable = self.register("readable", Readable(), readable=True)
        self.configure("readable", DEFAULT_SINK)

        assert source() is readable

    def test_a_write_only_sink_is_skipped(self):
        """A sink that cannot answer is passed over rather than asked."""
        self.register("writeonly", Recorder())
        self.configure("writeonly", DEFAULT_SINK)

        assert isinstance(source(), PluginAuditSink)

    def test_no_readable_sink_is_reported_as_none(self):
        """Which is what lets a caller say "recorded elsewhere" rather than
        show an empty log."""
        self.register("writeonly", Recorder())
        self.configure("writeonly")

        assert source() is None

    def test_entries_are_empty_without_a_source(self):
        """The convenience wrapper answers empty rather than raising."""
        self.register("writeonly", Recorder())
        self.configure("writeonly")

        assert audit_entries("userid-1") == []

    def test_entries_read_through_the_configured_source(self):
        """And a readable sink's own records are what comes back."""
        readable = self.register("readable", Readable(), readable=True)
        self.configure("readable")

        record("userid-1", AUTHENTICATED, "dex", True)

        assert len(audit_entries("userid-1")) == 1
        assert len(readable.written) == 1


class TestTheLogOnlySink(SinkCase):
    """A sink that writes and cannot be read back."""

    @pytest.fixture(autouse=True)
    def _log_sink(self) -> None:
        self.sink = getUtility(IAuditSink, name=LOG_SINK_NAME)

    def test_it_is_registered(self):
        """Registered whether or not a site uses it: a name that resolves to
        nothing cannot be chosen in the control panel."""
        assert isinstance(self.sink, LoggingAuditSink)

    def test_it_satisfies_the_sink_interface(self):
        """Writing is the whole of what it promises."""
        assert verifyObject(IAuditSink, self.sink)

    def test_it_is_not_a_source(self):
        """The point of it. A log file is somewhere records go, not somewhere
        a Plone site can query."""
        assert not IAuditSource.providedBy(self.sink)

    def test_it_has_no_entries_method_at_all(self):
        """Not an ``entries`` returning ``[]``, which every caller would read
        as nothing having happened."""
        assert not hasattr(self.sink, "entries")

    def test_recording_writes_a_line(self, caplog):
        """With the facts an operator greps for on it."""
        self.configure(LOG_SINK_NAME)

        # A successful sign-in is written at INFO, and the package logger
        # sits at WARNING, so the level has to be lowered to see one at all.
        with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
            record("userid-1", AUTHENTICATED, "dex", True)

        assert "userid-1" in caplog.text
        assert AUTHENTICATED in caplog.text
        assert "dex" in caplog.text

    def test_it_writes_one_line_per_event(self, caplog):
        """These are read by grepping, so a record is a line."""
        self.configure(LOG_SINK_NAME)

        with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
            record("userid-1", AUTHENTICATED, "dex", True)

        written = [r for r in caplog.records if r.name == LOGGER_NAME]
        assert len(written) == 1

    def test_a_refusal_is_a_warning(self, caplog):
        """A run of them is what an operator wants to notice."""
        self.configure(LOG_SINK_NAME)

        record("userid-1", FLOW_REFUSED, "dex", False)

        levels = {r.levelname for r in caplog.records if r.name == LOGGER_NAME}
        assert levels == {"WARNING"}

    def test_a_success_is_info(self, caplog):
        """And a successful sign-in is not, so a site can keep the ordinary
        traffic below the level it alerts on."""
        self.configure(LOG_SINK_NAME)

        with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
            record("userid-1", AUTHENTICATED, "dex", True)

        levels = {r.levelname for r in caplog.records if r.name == LOGGER_NAME}
        assert levels == {"INFO"}

    def test_an_unresolved_userid_is_written_as_a_dash(self, caplog):
        """Rather than as the word ``None``, which reads like a userid."""
        self.configure(LOG_SINK_NAME)

        record(None, FLOW_REFUSED, "dex", False)

        assert "userid=-" in caplog.text

    def test_it_writes_to_its_own_logger(self, caplog):
        """Which is the reason to choose this sink: authentication events can
        be routed to their own handler without moving everything else the
        add-on says."""
        self.configure(LOG_SINK_NAME)

        with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
            record("userid-1", AUTHENTICATED, "dex", True)

        assert any(r.name == LOGGER_NAME for r in caplog.records)


class TestRecordingToLogAndZODBTogether(SinkCase):
    """The combination an operator actually wants: keep the readable log,
    and ship a copy somewhere that outlives the site."""

    def test_both_receive_the_event(self, caplog):
        """One event, two destinations."""
        self.configure(DEFAULT_SINK, LOG_SINK_NAME)

        with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
            record("userid-both", AUTHENTICATED, "dex", True)

        assert len(audit_entries("userid-both")) == 1
        assert any(r.name == LOGGER_NAME for r in caplog.records)

    def test_the_readable_one_still_answers(self):
        """A write-only sink in the list must not make the control panel
        stop showing anything."""
        self.configure(LOG_SINK_NAME, DEFAULT_SINK)

        assert isinstance(source(), PluginAuditSink)

    def test_log_alone_leaves_nothing_readable(self):
        """And a site recording only to the log is told so."""
        self.configure(LOG_SINK_NAME)

        assert source() is None
