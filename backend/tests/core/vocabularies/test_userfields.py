"""The vocabulary of user fields a claim can be mapped onto."""

from pas.plugins.identity.core.vocabularies.userfields import USER_FIELDS_VOCABULARY
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

    def test_offers_the_standard_member_fields(self):
        tokens = self.tokens()

        assert "fullname" in tokens
        assert "email" in tokens

    def test_offers_the_extended_profile_fields(self):
        """These come from IUserDataSchema, not from a list kept here."""
        tokens = self.tokens()

        assert "home_page" in tokens
        assert "location" in tokens

    def test_excludes_registration_mechanics(self):
        """The reason this is not plone.app.users.user_registration_fields:
        a claim must never be written to a password field."""
        tokens = self.tokens()

        assert "password" not in tokens
        assert "password_ctl" not in tokens
        assert "mail_me" not in tokens

    def test_terms_carry_a_human_title(self):
        """The control panel shows the label the user form uses."""
        term = self.vocabulary.getTerm("fullname")

        assert term.title
        assert term.title != "fullname"

    def test_sorted_by_title(self):
        """A long list is only usable in a predictable order."""
        titles = [term.title.lower() for term in self.vocabulary]

        assert titles == sorted(titles)
