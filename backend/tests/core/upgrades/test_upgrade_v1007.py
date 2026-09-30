"""The step that adds the address confirmation setting and its catalog column.

Driven against a site that lacks both, holding a Profile indexed before the
column existed and a setting value of its own that the step must keep.
"""

from pas.plugins.identity.core.catalog import query_catalog
from pas.plugins.identity.core.confirmation import CONFIRM_RECORD
from pas.plugins.identity.core.confirmation import confirmation_pending_on_brain
from pas.plugins.identity.core.confirmation import PENDING_ATTRIBUTE
from pas.plugins.identity.core.container import PREFIX
from pas.plugins.identity.upgrades.v1007 import add_email_confirmation
from plone import api
from plone.registry.interfaces import IRegistry
from zope.component import getUtility

import pytest


#: A setting on the same interface that the default profile states a value
#: for, so that re-importing the registry step in place of this one would put
#: that value back.
CHOSEN = f"{PREFIX}.group_container_title"


class TestTheStep:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_profile) -> None:
        self.registry = getUtility(IRegistry)
        self.catalog = query_catalog()
        make_profile("alice", fullname="Alice Liddell", email="alice@example.com")
        del self.registry.records[CONFIRM_RECORD]
        self.catalog.delColumn(PENDING_ATTRIBUTE)
        api.portal.set_registry_record(CHOSEN, "Teams")

        add_email_confirmation(api.portal.get_tool("portal_setup"))

    def test_the_setting_exists(self):
        assert CONFIRM_RECORD in self.registry.records

    def test_it_is_off(self):
        assert self.registry[CONFIRM_RECORD] is False

    def test_a_chosen_setting_keeps_its_value(self):
        assert self.registry[CHOSEN] == "Teams"

    def test_the_column_exists(self):
        assert PENDING_ATTRIBUTE in self.catalog.schema()

    def test_a_profile_indexed_before_it_is_not_waiting(self):
        """Nothing is reindexed, which is only safe because the empty column
        reads as the right answer for every Profile already there."""
        api.portal.set_registry_record(CONFIRM_RECORD, True)
        brain = self.catalog.unrestrictedSearchResults(userid="alice")[0]

        assert confirmation_pending_on_brain(brain) is False
