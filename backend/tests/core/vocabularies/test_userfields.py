"""The vocabulary of Profile fields a claim can be mapped onto."""

from pas.plugins.identity.core.behaviors.details import IProfileDetails
from pas.plugins.identity.core.contents.profile import IUserProfileSchema
from pas.plugins.identity.core.subscribers import WRITABLE_FIELDS
from pas.plugins.identity.core.utils.propertymap import MAPPABLE_FIELDS
from pas.plugins.identity.core.vocabularies.userfields import USER_FIELDS_VOCABULARY
from pas.plugins.identity.exportimport.schema import USER_FIELDS
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory

import pytest


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

    def test_offers_exactly_the_fields_a_login_writes(self):
        """Not a list kept in step by hand: the same tuple the sync filters
        on, so the picker cannot offer a row the login would drop."""
        assert self.tokens() == list(MAPPABLE_FIELDS)

    def test_offers_nothing_handled_somewhere_else(self):
        """``email`` and ``portrait`` are the two guesses that read as
        reasonable. An address is appended by ``sync_addresses`` and a
        portrait is synced from the ``picture_url`` claim, so a row naming
        either was stored, exported, and dropped on every login."""
        tokens = self.tokens()

        assert "email" not in tokens
        assert "portrait" not in tokens

    def test_offers_nothing_a_provider_may_never_write(self):
        """``login`` is half of the enumeration index, ``group_ids`` is
        membership, and ``userid`` is the join to the identity store."""
        tokens = self.tokens()

        assert "login" not in tokens
        assert "group_ids" not in tokens
        assert "userid" not in tokens

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

    def test_in_the_order_the_fields_are_declared(self):
        """Four terms, so a sort by title would only hide which of them the
        form considers the important one."""
        assert self.tokens()[0] == "fullname"


class TestTheThreeAnswersAgree:
    """One definition, and the two filters that used to be their own.

    A login filtered on ``WRITABLE_FIELDS``, a principal document on
    ``USER_FIELDS``, and the control panel on nothing at all. The first two
    happened to hold the same four names; nothing made them.
    """

    def test_a_login_filters_on_the_definition(self):
        assert frozenset(MAPPABLE_FIELDS) == WRITABLE_FIELDS

    def test_a_principal_document_carries_the_definition(self):
        assert USER_FIELDS is MAPPABLE_FIELDS
