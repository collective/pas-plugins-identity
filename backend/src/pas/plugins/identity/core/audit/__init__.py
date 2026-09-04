"""The audit log.

An authentication-event log, and deliberately not a session ledger: it records
that a login was attempted and how it ended, not what the user did afterwards.
Worth knowing before anyone reaches for it as an activity trail.

Storage is a bounded per-user ``OOBTree`` inside the PAS plugin, purged on
write against two registry-configured limits -- how many entries to keep per
user and how long to keep them. Purging on write rather than on a schedule
means the bound holds without anything having to run.

Privacy: the IP address and user agent are personal data, and are stored
only when ``pas.plugins.identity.audit_record_pii`` is switched on. It is off
by default. Credentials, tokens and authorization codes are never recorded, in
any configuration.
"""

from BTrees.OOBTree import OOBTree
from datetime import datetime
from datetime import timedelta
from datetime import UTC
from pas.plugins.identity import logger
from pas.plugins.identity.core.interfaces import IAuditSink
from pas.plugins.identity.core.interfaces import JSONDict
from persistent import Persistent
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from plone import api
from zope.interface import implementer
from ZPublisher.HTTPRequest import HTTPRequest


#: Registry key bounding how many entries are kept per user.
MAX_ENTRIES_RECORD = "pas.plugins.identity.audit_max_entries"

#: Registry key bounding how long entries are kept.
MAX_DAYS_RECORD = "pas.plugins.identity.audit_max_days"

#: Registry key opting in to storing IP address and user agent.
RECORD_PII_RECORD = "pas.plugins.identity.audit_record_pii"

#: Bucket for entries that cannot be attributed to a userid. A callback with
#: an unknown state has, by construction, no user to attribute it to, and
#: those are exactly the entries an operator investigating an attack wants.
UNATTRIBUTED = "\x00unattributed"

#: Event names this package records. Free-form strings would drift; a
#: consumer needs to be able to filter on something stable.
AUTHENTICATED = "authenticated"
IDENTITY_LINKED = "identity-linked"
IDENTITY_UNLINKED = "identity-unlinked"
EMAIL_VERIFIED = "email-verified"
CLAIMS_REFRESHED = "claims-refreshed"
FLOW_REFUSED = "flow-refused"
PAYLOAD_REJECTED = "payload-rejected"
LINK_REFUSED = "link-refused"
LINK_COLLISION = "link-collision"
MAGIC_LINK_SENT = "magic-link-sent"
MAGIC_LINK_CONFIRMED = "magic-link-confirmed"
MAGIC_LINK_REFUSED = "magic-link-refused"

#: A sign-in the provider authenticated and this site's policy refused:
#: a person outside every allowed group, or a new account at a provider
#: not allowed to create one. Distinct from ``flow-refused``, which
#: means the credential itself did not check out -- an operator looking
#: at a run of these is looking at their own configuration, not at an
#: attack.
SIGNIN_REFUSED = "signin-refused"


class AuditEntry(Persistent):
    """One recorded authentication event.

    :ivar event: Event name, one of this module's constants.
    :ivar provider: Provider id the event concerns.
    :ivar success: Whether the attempt succeeded.
    :ivar timestamp: When it happened, in UTC.
    :ivar detail: Extra non-credential context.
    """

    def __init__(
        self,
        event: str,
        provider: str,
        success: bool,
        detail: JSONDict | None = None,
    ) -> None:
        """Record one event.

        :param event: Event name.
        :param provider: Provider id.
        :param success: Whether the attempt succeeded.
        :param detail: Extra non-credential context.
        """
        self.event = event
        self.provider = provider
        self.success = success
        self.timestamp = datetime.now(UTC)
        self.detail = PersistentMapping(detail or {})

    def serialize(self) -> JSONDict:
        """Render the entry for an API response.

        :returns: JSON-ready mapping.
        """
        return {
            "event": self.event,
            "provider": self.provider,
            "success": self.success,
            "timestamp": self.timestamp.isoformat(),
            "detail": dict(self.detail),
        }

    def __repr__(self) -> str:
        """Return a debugging representation.

        :returns: Event name and provider.
        """
        return f"<AuditEntry {self.event} {self.provider} success={self.success}>"


class AuditLog(Persistent):
    """Bounded per-user store of :class:`AuditEntry` objects."""

    def __init__(self) -> None:
        """Create an empty log."""
        self._by_userid: OOBTree = OOBTree()

    def record(
        self,
        userid: str | None,
        event: str,
        provider: str,
        success: bool,
        detail: JSONDict | None = None,
    ) -> AuditEntry:
        """Append an entry and purge whatever now falls outside the bounds.

        :param userid: Userid the event concerns; ``None`` when unresolved.
        :param event: Event name.
        :param provider: Provider id.
        :param success: Whether the attempt succeeded.
        :param detail: Extra non-credential context.
        :returns: The stored entry.
        """
        entry = AuditEntry(event, provider, success, detail)
        key = userid or UNATTRIBUTED
        entries = self._by_userid.get(key)
        if entries is None:
            entries = self._by_userid[key] = PersistentList()
        entries.append(entry)
        self._purge(entries)
        return entry

    def entries(self, userid: str | None = None) -> list[AuditEntry]:
        """Return recorded entries, newest first.

        :param userid: Restrict to one user; ``None`` returns everything,
            including the unattributed bucket.
        :returns: Matching entries.
        """
        if userid is not None:
            found = list(self._by_userid.get(userid, ()))
        else:
            found = [entry for bucket in self._by_userid.values() for entry in bucket]
        return sorted(found, key=lambda entry: entry.timestamp, reverse=True)

    def _purge(self, entries: PersistentList) -> None:
        """Trim one user's entries back inside the configured bounds.

        :param entries: The list to trim, oldest first.
        """
        max_days = _setting(MAX_DAYS_RECORD, 180)
        if max_days > 0:
            cutoff = datetime.now(UTC) - timedelta(days=max_days)
            while entries and entries[0].timestamp < cutoff:
                del entries[0]

        max_entries = _setting(MAX_ENTRIES_RECORD, 500)
        if max_entries > 0:
            excess = len(entries) - max_entries
            if excess > 0:
                del entries[:excess]


def _setting(record: str, default: int) -> int:
    """Read an integer registry setting.

    :param record: Registry key.
    :param default: Value to use when the record is missing or empty.
    :returns: The configured value.
    """
    value = api.portal.get_registry_record(record, default=default)
    return default if value is None else value


def record_pii() -> bool:
    """Report whether IP address and user agent may be stored.

    :returns: Whether the opt-in flag is on.
    """
    return bool(api.portal.get_registry_record(RECORD_PII_RECORD, default=False))


def request_detail(request: HTTPRequest | None) -> JSONDict:
    """Return the request context an entry may carry.

    Empty unless the privacy flag is on: an IP address identifies a person's
    machine, and the default for this package is not to keep one.

    :param request: The current request, or ``None``.
    :returns: Mapping with ``ip`` and ``user_agent``, or an empty mapping.
    """
    if request is None or not record_pii():
        return {}
    return {
        "ip": request.get("HTTP_X_FORWARDED_FOR") or request.get("REMOTE_ADDR", ""),
        "user_agent": request.get("HTTP_USER_AGENT", ""),
    }


@implementer(IAuditSink)
class PluginAuditSink:
    """Default sink: writes into the identity plugin's own log.

    Registered as a global utility, but resolves the plugin on every call, so
    it writes to whichever Plone site is being served. A deployment that wants
    entries somewhere else -- syslog, a SIEM -- overrides the utility.
    """

    def record(
        self,
        userid: str | None,
        event: str,
        provider: str,
        success: bool,
        detail: JSONDict | None = None,
    ) -> None:
        """Append one authentication event.

        :param userid: Userid the event concerns, ``None`` when unresolved.
        :param event: Event name.
        :param provider: Provider id involved.
        :param success: Whether the attempt succeeded.
        :param detail: Extra, non-credential context. Never tokens.
        """
        log = _log()
        if log is None:
            return
        log.record(userid, event, provider, success, detail)

    def entries(self, userid: str | None = None) -> list[AuditEntry]:
        """Return recorded entries, newest first.

        :param userid: Restrict to one user; ``None`` returns site-wide.
        :returns: Matching entries.
        """
        log = _log()
        return [] if log is None else log.entries(userid)


def _log() -> AuditLog | None:
    """Return the current site's audit log.

    :returns: The log, or ``None`` when the add-on is not installed here --
        auditing must never be the reason a request fails.
    """
    from pas.plugins.identity.core.pas import PLUGIN_ID

    try:
        plugin = api.portal.get_tool("acl_users")[PLUGIN_ID]
    except (KeyError, AttributeError, api.exc.CannotGetPortalError):
        logger.info("No identity plugin here; dropping an audit entry")
        return None
    return plugin.audit


def record(
    userid: str | None,
    event: str,
    provider: str,
    success: bool,
    detail: JSONDict | None = None,
    request: HTTPRequest | None = None,
) -> None:
    """Record one event through the configured sink.

    The single entry point every caller in this package uses, so that
    replacing the sink replaces it everywhere. A failure to audit is logged
    and swallowed: refusing a login because the audit log is unwritable would
    turn a bookkeeping problem into an outage.

    :param userid: Userid the event concerns, ``None`` when unresolved.
    :param event: Event name.
    :param provider: Provider id involved.
    :param success: Whether the attempt succeeded.
    :param detail: Extra, non-credential context.
    :param request: Current request, for the opt-in PII fields.
    """
    from zope.component import queryUtility

    sink = queryUtility(IAuditSink, default=None)
    if sink is None:
        return
    payload = {**(detail or {}), **request_detail(request)}
    try:
        sink.record(userid, event, provider, success, payload)
    except Exception:
        logger.exception("Could not write an audit entry for %r", event)
