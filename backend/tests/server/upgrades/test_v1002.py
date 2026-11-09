"""Server profile version 1002: Applications in Volto's user menu.

Driven against a site whose core profile has already taken it to 1013, which
is the order the steps are meant to run in: the category exists, without
Applications.
"""

from .. import PROFILE_ID
from plone import api

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


class TestApplicationsAdded:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.category = api.portal.get_tool("portal_actions")["personal_tools"]
        self.category.manage_delObjects(["applications"])
        assert "applications" not in self.category.objectIds()

        setup_tool = api.portal.get_tool("portal_setup")
        setup_tool.setLastVersionForProfile(PROFILE_ID, "1001")
        setup_tool.upgradeProfile(PROFILE_ID)

    def test_it_lands_before_site_setup(self):
        assert self.category.objectIds()[-2:] == ["applications", "plone_setup"]
