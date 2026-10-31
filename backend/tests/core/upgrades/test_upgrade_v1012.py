"""The step that adds the client address headers setting.

Driven against a site that lacks the record and holds a setting value of its
own that the step must keep.
"""

from pas.plugins.identity.core.utils.clientip import HEADERS_RECORD
from pas.plugins.identity.upgrades.v1012 import add_client_ip_headers
from plone import api
from plone.registry.interfaces import IRegistry
from zope.component import getUtility

import pytest


#: A setting the default profile states a value for, so that re-importing the
#: registry step in place of this one would put that value back.
CHOSEN = "pas.plugins.identity.audit_max_days"


class TestTheStep:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.registry = getUtility(IRegistry)
        del self.registry.records[HEADERS_RECORD]
        api.portal.set_registry_record(CHOSEN, 30)

        add_client_ip_headers(api.portal.get_tool("portal_setup"))

    def test_the_setting_exists(self):
        assert HEADERS_RECORD in self.registry.records

    def test_it_names_no_header(self):
        """An upgrade must not start believing a header nobody vouched for."""
        assert self.registry[HEADERS_RECORD] == ()

    def test_a_chosen_setting_keeps_its_value(self):
        assert self.registry[CHOSEN] == 30
