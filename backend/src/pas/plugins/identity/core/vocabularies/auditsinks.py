"""The audit destinations a site can record to.

Every :class:`~pas.plugins.identity.core.interfaces.IAuditSink` registered
under a name, which on a plain install is one and on a site with an extra
installed is more. Built from the component registry rather than from a
hard-coded list, so a sink shipped by another package appears here by being
registered, and a sink whose extra is not installed cannot be chosen at all.

Whether a destination can be *read back* is worth seeing while choosing it,
because it decides what the control panel and ``@audit-log`` are able to
answer. So a sink that also provides
:class:`~pas.plugins.identity.core.interfaces.IAuditSource` says so in its
title rather than leaving an operator to discover it by finding an empty log.
"""

from pas.plugins.identity.core.interfaces import IAuditSink
from pas.plugins.identity.core.interfaces import IAuditSource
from zope.component import getUtilitiesFor
from zope.interface import implementer
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


#: Name the vocabulary is registered and served under.
AUDIT_SINKS_VOCABULARY = "pas.plugins.identity.AuditSinks"


@implementer(IVocabularyFactory)
class AuditSinksVocabulary:
    """List the audit sinks registered on this site."""

    def __call__(self, context) -> SimpleVocabulary:
        """Build the vocabulary from the registered sink utilities.

        :param context: The context the vocabulary is looked up on. Unused:
            sinks are registered globally rather than per site.
        :returns: One term per named sink, ordered by name, each titled with
            whether its records can be read back again.
        """
        terms = []
        for name, sink in getUtilitiesFor(IAuditSink):
            if not name:
                # An unnamed sink cannot be named in the setting, so offering
                # it would produce a choice that stores a value nothing reads.
                continue
            readable = IAuditSource.providedBy(sink)
            title = f"{name} (readable)" if readable else f"{name} (write-only)"
            terms.append(SimpleTerm(value=name, token=name, title=title))
        terms.sort(key=lambda term: term.value)
        return SimpleVocabulary(terms)


AuditSinksVocabularyFactory = AuditSinksVocabulary()
