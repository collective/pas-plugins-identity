"""``group_ids`` names groups from a vocabulary rather than free text.

The value is a group id, and nothing used to check that it named a group.
The groups plugin filters an unknown id out rather than failing, so a typo
produced a membership that silently granted nothing -- the worst shape for a
mistake about who is in which group.

The interesting question is not whether the vocabulary lists groups; it is
what happens to a Profile that already names a group which has since gone.
The doctor reports those as ``unknown-group`` and explicitly does not treat
them as fatal, so validation must not make such a Profile unreadable.
"""

from pas.plugins.identity.core.vocabularies.groups import GROUPS_VOCABULARY
from plone import api
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory

import pytest


def build(portal):
    """Return the groups vocabulary, built against the site.

    A function rather than a fixture because several tests need it built
    *after* they have changed what groups exist.

    :param portal: The Plone site.
    :returns: The vocabulary.
    """
    return getUtility(IVocabularyFactory, name=GROUPS_VOCABULARY)(portal)


class TestTheVocabulary:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_group) -> None:
        self.portal = portal
        self.make_group = make_group

    def test_the_field_uses_it(self):
        """Which is what gives the widget something to offer."""
        from pas.plugins.identity.core.behaviors.membership import IGroupMembership

        value_type = IGroupMembership["group_ids"].value_type

        assert value_type.vocabularyName == GROUPS_VOCABULARY

    def test_it_lists_a_content_group(self):
        """The groups this layer makes."""
        assert "editors" not in [term.value for term in build(self.portal)]

        self.make_group("editors", title="Editors")

        assert "editors" in [term.value for term in build(self.portal)]

    def test_it_lists_plones_own_groups(self):
        """Membership names an id without caring which plugin answers for
        it, so a site keeping some principals in source_groups still has
        them offered."""
        assert "Administrators" in [term.value for term in build(self.portal)]

    def test_it_leaves_out_virtual_groups(self):
        """Nobody is explicitly a member of AuthenticatedUsers, so storing
        it would be a membership that means nothing."""
        assert "AuthenticatedUsers" not in [term.value for term in build(self.portal)]

    def test_terms_are_titled(self):
        """A group listing shows titles, and so should the widget."""
        term = next(t for t in build(self.portal) if t.value == "Administrators")

        assert term.title == "Administrators"


class TestAGroupThatWentAway:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_profile, make_group) -> None:
        self.portal = portal
        make_group("editors", title="Editors")
        self.profile = make_profile("alice", group_ids=("editors",))

    def test_the_profile_keeps_the_stale_id(self):
        """Deleting the group must not rewrite anybody's membership behind
        their back; the doctor reports it instead."""
        api.content.delete(obj=self.portal["identity-profiles"]["editors"])

        assert self.profile.group_ids == ("editors",)

    def test_the_stale_id_is_still_readable(self):
        """The check that matters. A vocabulary constrains what may be
        *written*; a Profile that already names a departed group has to stay
        readable, or removing a group would take its members' Profiles down
        with it."""
        api.content.delete(obj=self.portal["identity-profiles"]["editors"])

        assert self.profile.group_ids[0] == "editors"
        assert self.profile.userid == "alice"
