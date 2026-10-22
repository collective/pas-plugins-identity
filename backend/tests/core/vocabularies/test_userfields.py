"""The vocabulary of Profile fields a claim can be mapped onto."""

from pas.plugins.identity.core.behaviors.details import IProfileDetails
from pas.plugins.identity.core.contents.profile import IUserProfileSchema
from pas.plugins.identity.core.utils.propertymap import mappable_fields
from pas.plugins.identity.core.vocabularies.userfields import USER_FIELDS_VOCABULARY
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory

import pytest


def vocabulary_tokens(portal) -> list[str]:
    """Return every token the vocabulary offers, built afresh.

    :param portal: The Plone site.
    :returns: The field names.
    """
    factory = getUtility(IVocabularyFactory, name=USER_FIELDS_VOCABULARY)
    return [term.token for term in factory(portal)]


class TestUserFieldsVocabulary:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.vocabulary = getUtility(IVocabularyFactory, name=USER_FIELDS_VOCABULARY)(
            portal
        )

    def tokens(self) -> list[str]:
        """Return every token the vocabulary offers.

        :returns: The field names.
        """
        return [term.token for term in self.vocabulary]

    def test_registered_under_its_name(self):
        """The frontend asks for it by name through @vocabularies."""
        assert self.vocabulary is not None

    def test_offers_the_text_fields_of_the_shipped_type(self):
        """The type's own schema first, then its behaviors, in that order."""
        assert self.tokens() == ["fullname", "description", "home_page", "location"]

    def test_offers_exactly_the_fields_a_login_writes(self):
        """Not a list kept in step by hand: the same function the sync filters
        on, so the picker cannot offer a row the login would drop."""
        assert self.tokens() == list(mappable_fields())

    def test_offers_nothing_handled_somewhere_else(self):
        """``email`` and ``portrait`` are the two guesses that read as
        reasonable. An address is appended by ``sync_addresses`` and a
        portrait is synced from the ``picture_url`` claim, so a row naming
        either was stored, exported, and dropped on every login."""
        tokens = self.tokens()

        assert "email" not in tokens
        assert "emails" not in tokens
        assert "portrait" not in tokens

    def test_offers_nothing_a_provider_may_never_write(self):
        """``login`` is half of the enumeration index, ``group_ids`` is
        membership, and ``userid`` is the join to the identity store."""
        tokens = self.tokens()

        assert "login" not in tokens
        assert "group_ids" not in tokens
        assert "userid" not in tokens

    def test_offers_nothing_that_describes_the_object(self):
        """``plone.shortname`` and ``plone.versioning`` are on the shipped
        type, and their fields say nothing about the person."""
        tokens = self.tokens()

        assert "id" not in tokens
        assert "changeNote" not in tokens
        assert "versioning_enabled" not in tokens

    def test_terms_carry_the_label_the_profile_form_uses(self):
        """Read off the schema rather than restated here, so a field renamed
        on the form is renamed in this picker in the same commit."""
        assert (
            self.vocabulary.getTerm("fullname").title
            == IUserProfileSchema["fullname"].title
        )
        assert (
            self.vocabulary.getTerm("home_page").title
            == IProfileDetails["home_page"].title
        )

    def test_a_field_is_titled_rather_than_named(self):
        """``description`` is shown as *Biography*, which is what the profile
        form calls it and what an operator is looking for."""
        assert self.vocabulary.getTerm("description").title == "Biography"


class TestABehaviorTheSiteAdds:
    """#143: a behavior on the user type is a destination once enabled."""

    @pytest.fixture(autouse=True)
    def _setup(self, extra_profile_fields) -> None:
        self.portal = extra_profile_fields

    def test_its_fields_are_offered(self):
        tokens = vocabulary_tokens(self.portal)

        assert {"social_links", "tags", "age"} <= set(tokens)

    def test_after_the_type_s_own_fields(self):
        assert vocabulary_tokens(self.portal)[:4] == [
            "fullname",
            "description",
            "home_page",
            "location",
        ]

    def test_a_readonly_field_is_not_offered(self):
        """Nothing may write it, a login included."""
        assert "badge" not in vocabulary_tokens(self.portal)

    def test_titled_by_the_behavior(self):
        factory = getUtility(IVocabularyFactory, name=USER_FIELDS_VOCABULARY)

        assert factory(self.portal).getTerm("social_links").title == "Social links"


class TestABehaviorTheSiteHasNotEnabled:
    """Read when asked for, so nothing lingers from a type it is not on."""

    def test_its_fields_are_not_offered(self, portal):
        assert "social_links" not in vocabulary_tokens(portal)
