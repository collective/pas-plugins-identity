"""An audit sink that writes to the Python log and nothing else.

The write-only case, and the reason
:class:`~pas.plugins.identity.core.interfaces.IAuditSource` is a separate
interface: a log file is somewhere records *go*, not somewhere a Plone site
can query. This sink provides
:class:`~pas.plugins.identity.core.interfaces.IAuditSink` alone, and a site
recording only here is told by ``@audit-log`` that its records live somewhere
this site cannot read, rather than shown an empty list.

Why it is worth having at all, when the built-in sink already keeps records
in the ZODB:

* **It leaves the database alone.** A ZODB write per authentication event is
  a write per login attempt, including the failed ones, which is exactly the
  traffic a site under credential-stuffing gets most of. A log line costs no
  transaction and cannot conflict.
* **It is the shape every other tool already reads.** Shipping records to
  journald, a sidecar, a log collector or a SIEM means writing lines that
  something else tails. That is a solved problem for logs and a bespoke
  integration for anything else.
* **It survives the site.** Records written here outlive an instance, a
  ``Data.fs`` restored from backup, and the retention bounds that purge the
  built-in log on every write.

Records go to a logger of this module's own rather than to the package logger,
so a deployment can route authentication events to their own handler, file or
level without moving everything else the add-on says. That separation is the
main reason to choose this sink, and it is why the logger is named rather than
inherited.

Privacy: this sink writes what it is handed, which is what
:func:`~pas.plugins.identity.core.audit.record` already assembled. The IP
address and user agent reach it only when ``audit_record_pii`` is on, exactly
as they reach the built-in sink. Worth remembering that a log file is a
different disclosure surface from the ZODB, though: it is usually readable by
more people, shipped off the host, and kept by a retention policy this package
does not control.
"""

from pas.plugins.identity.core.interfaces import IAuditSink
from pas.plugins.identity.core.interfaces import JSONDict
from zope.interface import implementer

import logging


#: Where this sink writes. Named rather than inherited from the package
#: logger so that authentication events can be routed on their own.
logger = logging.getLogger("pas.plugins.identity.audit")

#: Name this sink is registered under, and what a site puts in
#: ``audit_sinks`` to start recording here.
SINK_NAME = "log"


@implementer(IAuditSink)
class LoggingAuditSink:
    """Write each authentication event to the log, and answer no questions.

    Deliberately provides no ``entries``. A sink that offered one returning
    an empty list would be indistinguishable, to every caller, from a site
    where nothing had happened.
    """

    def record(
        self,
        userid: str | None,
        event: str,
        provider: str,
        success: bool,
        detail: JSONDict | None = None,
    ) -> None:
        """Write one authentication event as a single log line.

        One line rather than several, because a multi-line record is a
        multi-line record to grep, and these are read by grepping.

        The level follows the outcome: a refusal is a warning, since a run of
        them is what an operator wants to notice, and a success is info. This
        is the one decision the sink makes about what it is handed; everything
        else is written through.

        :param userid: Userid the event concerns, ``None`` when unresolved.
        :param event: Event name.
        :param provider: Provider id involved.
        :param success: Whether the attempt succeeded.
        :param detail: Extra, non-credential context. Never tokens.
        """
        logger.log(
            logging.INFO if success else logging.WARNING,
            "audit event=%s provider=%s userid=%s success=%s detail=%r",
            event,
            provider,
            userid if userid is not None else "-",
            success,
            detail or {},
        )
