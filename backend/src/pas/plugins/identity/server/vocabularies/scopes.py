"""The scopes a client may be registered for.

``scope`` was a free-text line, entered as a space-separated string. That
made a registration a typing exercise against a list nobody had: ``emails``
for ``email``, or a scope this server has never implemented, was stored
without complaint and then quietly narrowed away at the token endpoint --
where a client sees claims it asked for simply missing, which reads as a bug
in the server rather than as a mistake in the registration.

The terms come from
:func:`pas.plugins.identity.server.discovery.scopes_supported`, which is what
the discovery document advertises. One source, so a site that extends
:data:`~pas.plugins.identity.server.claims.SCOPE_CLAIMS` gets the new scope
offered in the form as well as announced to clients, and the form can never
offer one the token endpoint would drop.

A factory rather than a module-level ``SimpleVocabulary`` for two reasons:
``SCOPE_CLAIMS`` is extensible at runtime and a vocabulary built at import
time would freeze the shipped three, and a named utility is resolved when the
field is validated rather than when its module is imported, which keeps the
control panel's schema out of the server's import graph.
"""

from zope.interface import implementer
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


#: Name the vocabulary is registered and served under.
SCOPES_VOCABULARY = "pas.plugins.identity.Scopes"


@implementer(IVocabularyFactory)
class ScopesVocabulary:
    """List the scopes this server issues tokens for."""

    def __call__(self, context) -> SimpleVocabulary:
        """Build the vocabulary from what discovery advertises.

        :param context: The context the vocabulary is looked up on. Unused:
            what this server implements is site-wide.
        :returns: One term per advertised scope, in the order the discovery
            document lists them -- ``openid`` first, then the rest sorted.
        """
        from pas.plugins.identity.server.discovery import scopes_supported

        return SimpleVocabulary([
            SimpleTerm(value=scope, token=scope, title=scope)
            for scope in scopes_supported()
        ])


ScopesVocabularyFactory = ScopesVocabulary()
