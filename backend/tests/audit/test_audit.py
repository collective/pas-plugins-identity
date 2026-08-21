"""Integration tests for the audit log (§4.6, D7, I4)."""

from . import CLAIMS
from datetime import timedelta
from pas.plugins.identity.core import audit as audit_module
from pas.plugins.identity.core.audit import AuditLog
from pas.plugins.identity.core.audit import AUTHENTICATED
from pas.plugins.identity.core.audit import EMAIL_VERIFIED
from pas.plugins.identity.core.audit import IDENTITY_LINKED
from pas.plugins.identity.core.audit import IDENTITY_UNLINKED
from pas.plugins.identity.core.audit import MAX_DAYS_RECORD
from pas.plugins.identity.core.audit import MAX_ENTRIES_RECORD
from pas.plugins.identity.core.audit import PluginAuditSink
from pas.plugins.identity.core.audit import record
from pas.plugins.identity.core.audit import RECORD_PII_RECORD
from pas.plugins.identity.core.audit import request_detail
from pas.plugins.identity.core.audit import UNATTRIBUTED
from pas.plugins.identity.core.events import EmailVerified
from pas.plugins.identity.core.events import ExternalIdentityAuthenticated
from pas.plugins.identity.core.events import IdentityLinked
from pas.plugins.identity.core.events import IdentityUnlinked
from pas.plugins.identity.core.events import UserClaimsRefreshed
from pas.plugins.identity.core.interfaces import IAuditSink
from pas.plugins.identity.core.pas import PLUGIN_ID
from plone import api
from zope.component import getUtility
from zope.event import notify
from zope.interface.verify import verifyObject

import pytest


@pytest.fixture()
def log(portal) -> AuditLog:
    """Return the installed plugin's audit log, emptied."""
    plugin = api.portal.get_tool("acl_users")[PLUGIN_ID]
    plugin.audit._by_userid.clear()
    return plugin.audit


class TestSinkRegistration:
    def test_sink_is_registered(self, portal):
        """The default sink is what ``record`` finds."""
        assert isinstance(getUtility(IAuditSink), PluginAuditSink)

    def test_sink_satisfies_its_interface(self, portal):
        """A replacement sink knows exactly what it has to provide."""
        assert verifyObject(IAuditSink, getUtility(IAuditSink))

    def test_sink_writes_to_the_plugin_log(self, portal, log):
        """The default sink is backed by the plugin's own store."""
        getUtility(IAuditSink).record("userid-1", AUTHENTICATED, "dex", True)

        assert len(log.entries("userid-1")) == 1

    def test_sink_reads_back(self, portal, log):
        """And reads through the same store."""
        log.record("userid-1", AUTHENTICATED, "dex", True)

        assert len(getUtility(IAuditSink).entries("userid-1")) == 1


class TestRecording:
    def test_entry_carries_the_facts(self, portal, log):
        """Event, provider and outcome are the point of an entry."""
        entry = log.record("userid-1", AUTHENTICATED, "dex", True, {"subject": "s"})

        assert entry.event == AUTHENTICATED
        assert entry.provider == "dex"
        assert entry.success is True
        assert entry.detail["subject"] == "s"
        assert entry.timestamp is not None

    def test_failures_are_recorded_too(self, portal, log):
        """A refused attempt is the interesting kind."""
        log.record(None, "flow-refused", "dex", False, {"reason": "bad state"})

        entry = log.entries()[0]
        assert entry.success is False
        assert entry.detail["reason"] == "bad state"

    def test_unattributed_entries_are_kept(self, portal, log):
        """A refusal has no userid, and must not be dropped for it."""
        log.record(None, "flow-refused", "dex", False)

        assert len(log.entries(UNATTRIBUTED)) == 1
        assert len(log.entries()) == 1

    def test_per_user_isolation(self, portal, log):
        """One user's log is not another's."""
        log.record("userid-1", AUTHENTICATED, "dex", True)
        log.record("userid-2", AUTHENTICATED, "dex", True)

        assert len(log.entries("userid-1")) == 1
        assert len(log.entries("userid-2")) == 1
        assert len(log.entries()) == 2

    def test_unknown_user_has_no_entries(self, portal, log):
        """Asking about a stranger is not an error."""
        assert log.entries("never-seen") == []

    def test_entries_are_newest_first(self, portal, log):
        """An operator reads the top of the log."""
        for index in range(3):
            log.record("userid-1", AUTHENTICATED, "dex", True, {"n": index})

        assert [e.detail["n"] for e in log.entries("userid-1")] == [2, 1, 0]

    def test_entry_serializes(self, portal, log):
        """The shape ``@audit-log`` will publish (Gate 4)."""
        entry = log.record("userid-1", AUTHENTICATED, "dex", True, {"subject": "s"})

        payload = entry.serialize()

        assert payload["event"] == AUTHENTICATED
        assert payload["provider"] == "dex"
        assert payload["success"] is True
        assert payload["detail"] == {"subject": "s"}
        assert payload["timestamp"].startswith(str(entry.timestamp.year))

    def test_repr(self, portal, log):
        """Debugging representation names the event."""
        entry = log.record("userid-1", AUTHENTICATED, "dex", True)

        assert AUTHENTICATED in repr(entry)


class TestBounds:
    """§4.6 -- the log is bounded, and purged on write rather than on a
    schedule, so the bound holds without anything having to run."""

    def test_entry_count_is_capped(self, portal, log):
        """Write past the cap and the oldest are evicted."""
        api.portal.set_registry_record(MAX_ENTRIES_RECORD, 10)

        for index in range(15):
            log.record("userid-1", AUTHENTICATED, "dex", True, {"n": index})

        entries = log.entries("userid-1")
        assert len(entries) == 10
        assert [e.detail["n"] for e in entries][-1] == 5

    def test_the_plan_bound_holds(self, portal, log):
        """The §4.6 example: write 600, keep 500, oldest evicted."""
        api.portal.set_registry_record(MAX_ENTRIES_RECORD, 500)

        for index in range(600):
            log.record("userid-1", AUTHENTICATED, "dex", True, {"n": index})

        entries = log.entries("userid-1")
        assert len(entries) == 500
        assert [e.detail["n"] for e in entries][-1] == 100

    def test_old_entries_expire(self, portal, log):
        """Age is the other bound."""
        api.portal.set_registry_record(MAX_DAYS_RECORD, 30)
        stale = log.record("userid-1", AUTHENTICATED, "dex", True)
        stale.timestamp = stale.timestamp - timedelta(days=31)

        log.record("userid-1", AUTHENTICATED, "dex", True)

        assert len(log.entries("userid-1")) == 1

    def test_recent_entries_survive(self, portal, log):
        """And a day-old entry is not old."""
        api.portal.set_registry_record(MAX_DAYS_RECORD, 30)
        recent = log.record("userid-1", AUTHENTICATED, "dex", True)
        recent.timestamp = recent.timestamp - timedelta(days=1)

        log.record("userid-1", AUTHENTICATED, "dex", True)

        assert len(log.entries("userid-1")) == 2

    def test_zero_disables_the_count_bound(self, portal, log):
        """An operator who wants everything can say so."""
        api.portal.set_registry_record(MAX_ENTRIES_RECORD, 0)

        for _ in range(20):
            log.record("userid-1", AUTHENTICATED, "dex", True)

        assert len(log.entries("userid-1")) == 20

    def test_zero_disables_the_age_bound(self, portal, log):
        """Likewise for retention."""
        api.portal.set_registry_record(MAX_DAYS_RECORD, 0)
        stale = log.record("userid-1", AUTHENTICATED, "dex", True)
        stale.timestamp = stale.timestamp - timedelta(days=9999)

        log.record("userid-1", AUTHENTICATED, "dex", True)

        assert len(log.entries("userid-1")) == 2

    def test_missing_record_falls_back_to_the_default(self, portal, log, monkeypatch):
        """A site whose registry lost the record still gets a bound."""
        monkeypatch.setattr(api.portal, "get_registry_record", lambda *a, **kw: None)

        assert audit_module._setting(MAX_ENTRIES_RECORD, 500) == 500


class TestPrivacy:
    """D7 -- IP and user agent are personal data and are opt-in."""

    def test_pii_is_off_by_default(self, portal):
        """The default profile must not switch on data collection."""
        assert api.portal.get_registry_record(RECORD_PII_RECORD) is False

    def test_no_request_context_by_default(self, portal):
        """With the flag off, nothing about the machine is stored."""
        assert request_detail(portal.REQUEST) == {}

    def test_request_context_when_opted_in(self, portal):
        """With it on, the operator gets what they asked for."""
        api.portal.set_registry_record(RECORD_PII_RECORD, True)
        portal.REQUEST.environ["REMOTE_ADDR"] = "203.0.113.7"
        portal.REQUEST.environ["HTTP_USER_AGENT"] = "test-agent"

        detail = request_detail(portal.REQUEST)

        assert detail["ip"] == "203.0.113.7"
        assert detail["user_agent"] == "test-agent"

    def test_forwarded_for_wins(self, portal):
        """Behind a proxy the socket address is the proxy's."""
        api.portal.set_registry_record(RECORD_PII_RECORD, True)
        portal.REQUEST.environ["REMOTE_ADDR"] = "10.0.0.1"
        portal.REQUEST.environ["HTTP_X_FORWARDED_FOR"] = "203.0.113.7"

        assert request_detail(portal.REQUEST)["ip"] == "203.0.113.7"

    def test_no_request_yields_nothing(self, portal):
        """Not every caller has a request."""
        api.portal.set_registry_record(RECORD_PII_RECORD, True)

        assert request_detail(None) == {}


class TestSubscribers:
    """Successes are recorded from the event contract."""

    def test_authentication_is_recorded(self, portal, log):
        """Every successful login leaves a trace."""
        notify(
            ExternalIdentityAuthenticated(
                "userid-1", "dex", "subject-1", CLAIMS, True, True
            )
        )

        entry = log.entries("userid-1")[0]
        assert entry.event == AUTHENTICATED
        assert entry.detail["is_new_user"] is True
        assert entry.detail["subject"] == "subject-1"

    def test_link_is_recorded(self, portal, log):
        """Linking is a security-relevant act."""
        notify(IdentityLinked("userid-1", "github", "1234567", CLAIMS))

        assert log.entries("userid-1")[0].event == IDENTITY_LINKED

    def test_unlink_is_recorded(self, portal, log):
        """So is unlinking."""
        notify(IdentityUnlinked("userid-1", "github", "1234567"))

        assert log.entries("userid-1")[0].event == IDENTITY_UNLINKED

    def test_email_verification_is_recorded_with_the_address(self, portal, log):
        """An entry that will not say which address was verified is useless."""
        notify(EmailVerified("userid-1", "Erico@Plone.ORG"))

        entry = log.entries("userid-1")[0]
        assert entry.event == EMAIL_VERIFIED
        assert entry.detail["address"] == "erico@plone.org"

    def test_claims_refresh_records_no_claims(self, portal, log):
        """The useful fact is that a refresh happened; the claims themselves
        are the user's personal data and change on every login."""
        notify(UserClaimsRefreshed("userid-1", "dex", CLAIMS))

        entry = log.entries("userid-1")[0]
        assert "claims" not in entry.detail
        assert entry.detail == {}


class TestNeverBreaksALogin:
    """A bookkeeping problem must not become an outage."""

    def test_a_failing_sink_is_swallowed(self, portal, monkeypatch):
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

    def test_no_sink_is_not_an_error(self, portal, monkeypatch):
        """A site that deliberately unregistered the sink still works."""
        import zope.component

        monkeypatch.setattr(zope.component, "queryUtility", lambda *a, **kw: None)

        record("userid-1", AUTHENTICATED, "dex", True)


class TestSinkWithoutAPlugin:
    """Auditing must never be the reason a request fails, including on a
    Zope root or a site where the add-on is not installed."""

    @pytest.fixture()
    def no_plugin(self, portal, monkeypatch):
        """Make the identity plugin unreachable."""

        def missing(name):
            """Raise as a site without the add-on would.

            :param name: Tool name.
            :raises KeyError: Always.
            """
            raise KeyError(name)

        monkeypatch.setattr(api.portal, "get_tool", missing)

    def test_record_is_a_no_op(self, no_plugin):
        """Nothing to write to is not an error."""
        PluginAuditSink().record("userid-1", AUTHENTICATED, "dex", True)

    def test_entries_are_empty(self, no_plugin):
        """And reading gives nothing rather than raising."""
        assert PluginAuditSink().entries("userid-1") == []


class TestLazyLog:
    def test_plugin_predating_the_audit_log_gains_one(self, portal):
        """A plugin persisted before the audit log existed must not raise on
        first use; it gets a log the same way a fresh one does."""
        plugin = api.portal.get_tool("acl_users")[PLUGIN_ID]
        del plugin._audit

        log = plugin.audit

        assert isinstance(log, AuditLog)
        assert plugin.audit is log
