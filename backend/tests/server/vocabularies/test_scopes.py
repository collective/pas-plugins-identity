"""``scope`` on a client is picked from a list rather than typed.

It was a free-text line holding space-separated scopes, which made a
registration a typing exercise against a list nobody had. A typo was stored
without complaint and then narrowed away at the token endpoint, where the
client sees a claim it asked for simply missing -- which reads as a bug in the
server rather than as a mistake in the registration.

The interesting part is not that the vocabulary lists four scopes. It is that
it lists *the same* four the discovery document advertises, and keeps doing so
when a site extends what this server releases: two lists that agree today and
are computed separately drift the moment somebody adds a scope.
"""

from pas.plugins.identity.server.controlpanel.interfaces import IClientRecords
from pas.plugins.identity.server.discovery import scopes_supported
from pas.plugins.identity.server.vocabularies.scopes import SCOPES_VOCABULARY
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory

import pytest


@pytest.fixture
def vocabulary(portal):
    """Return the scopes vocabulary, built against the site.

    :param portal: The Plone site.
    :returns: The vocabulary.
    """
    factory = getUtility(IVocabularyFactory, name=SCOPES_VOCABULARY)
    return factory(portal)


class TestTheVocabulary:
    def test_it_is_registered(self, portal):
        """A ``Choice`` names it as a string, so a missing registration is not
        an import error: it is an empty picker on a form that looks fine."""
        assert getUtility(IVocabularyFactory, name=SCOPES_VOCABULARY) is not None

    def test_it_offers_what_discovery_advertises(self, vocabulary):
        """One list, computed once. A client reads the scopes out of the
        discovery document and the operator picks from the form; the two
        disagreeing is a registration that cannot work."""
        assert [term.value for term in vocabulary] == scopes_supported()

    def test_openid_comes_first(self, vocabulary):
        """The one scope every OpenID request must carry, so it reads first
        in the picker as it does in the document."""
        assert next(iter(vocabulary)).value == "openid"

    def test_a_term_is_titled_by_its_own_name(self, vocabulary):
        """A scope is what a client sends verbatim. Titling it anything else
        would show the operator a word no client will ever transmit."""
        assert all(term.title == term.value for term in vocabulary)

    def test_it_grows_with_what_the_server_releases(self, portal, monkeypatch):
        """The reason it is a factory and not a module-level vocabulary built
        at import time: a site that extends ``SCOPE_CLAIMS`` gets the scope
        advertised to clients, and must get it offered in the form too."""
        from pas.plugins.identity.server import claims

        monkeypatch.setitem(claims.SCOPE_CLAIMS, "phone", ("phone_number",))
        factory = getUtility(IVocabularyFactory, name=SCOPES_VOCABULARY)

        assert "phone" in [term.value for term in factory(portal)]


class TestTheField:
    def test_it_is_a_list_of_choices(self):
        """Not a line of text: a trailing space or a stray comma typed into a
        text box became a scope of its own."""
        field = IClientRecords["scope"]

        assert field.value_type.vocabularyName == SCOPES_VOCABULARY

    def test_it_is_optional(self):
        """A client that asks for no scope is a client that gets no claims,
        which is a registration rather than an incomplete form."""
        assert IClientRecords["scope"].required is False

    def test_an_absent_value_is_empty_rather_than_none(self):
        """``None`` and ``()`` both read as "no scopes", and the panel would
        have to handle two spellings of it."""
        field = IClientRecords["scope"]

        assert field.default == ()
        assert field.missing_value == ()
