"""A membership change reindexes the one index it feeds.

``group_ids`` is indexed under its own name and feeds nothing else, so a write
that changes only it has no reason to rewrite ``SearchableText``,
``sortable_title`` and the rest with the values they already hold. The
metadata record is still refreshed, because the brain is what
``getGroupsForPrincipal`` reads.
"""

from pas.plugins.identity.core.behaviors.membership import IGroupMembership
from pas.plugins.identity.core.catalog import IdentityProfileCatalog
from pas.plugins.identity.core.indexers.subscribers import _indexes_for
from plone import api
from zope.interface import Interface
from zope.lifecycleevent import Attributes
from zope.lifecycleevent import ObjectModifiedEvent

import pytest


class TestTheIndexesAnEventNames:
    def test_group_ids_alone_is_narrowed(self):
        event = ObjectModifiedEvent(None, Attributes(IGroupMembership, "group_ids"))

        assert _indexes_for(event) == ["group_ids"]

    def test_no_description_reindexes_everything(self):
        assert _indexes_for(ObjectModifiedEvent(None)) is None

    def test_another_field_reindexes_everything(self):
        """``fullname`` is not an index of its own name: it feeds
        ``sortable_title`` and ``SearchableText``."""
        event = ObjectModifiedEvent(
            None,
            Attributes(IGroupMembership, "group_ids"),
            Attributes(Interface, "fullname"),
        )

        assert _indexes_for(event) is None

    def test_a_description_without_attributes_reindexes_everything(self):
        """A transition event carries no descriptions at all."""
        assert _indexes_for(object()) is None


class TestAMembershipChange:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, catalog, make_profile, make_group, monkeypatch) -> None:
        self.catalog = catalog
        make_group("editors")
        make_profile("alice", fullname="Alice Liddell")
        self.calls: list[list[str] | None] = []
        original = IdentityProfileCatalog.reindexObject

        def recording(catalog, obj, idxs=None, *args, **kwargs):
            self.calls.append(idxs)
            return original(catalog, obj, idxs, *args, **kwargs)

        monkeypatch.setattr(IdentityProfileCatalog, "reindexObject", recording)

    def test_adding_reindexes_group_ids_alone(self):
        """Through the whole path, from ``plone.api`` down: the narrowing only
        happens if the plugin's event says what changed."""
        api.group.add_user(groupname="editors", username="alice")

        assert self.calls == [["group_ids"]]

    def test_removing_reindexes_group_ids_alone(self):
        api.group.add_user(groupname="editors", username="alice")
        self.calls.clear()

        api.group.remove_user(groupname="editors", username="alice")

        assert self.calls == [["group_ids"]]

    def test_the_brain_still_answers(self):
        """The half that keeps the narrowing honest: the index and the
        metadata column both carry the new membership."""
        api.group.add_user(groupname="editors", username="alice")

        brains = self.catalog.unrestrictedSearchResults(group_ids="editors")
        assert [brain.userid for brain in brains] == ["alice"]
        assert tuple(brains[0].group_ids) == ("editors",)
