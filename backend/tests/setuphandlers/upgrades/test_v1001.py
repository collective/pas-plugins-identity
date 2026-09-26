"""Version 1001: the group FTI can hold a group.

The reason the step exists: an FTI is a persistent object written at install,
so a site installed before containment keeps an empty
``allowed_content_types`` and offers nothing in the add menu inside a group,
with nothing to say why.
"""

from pas.plugins.identity.core.catalog import GROUP_PORTAL_TYPE
from plone import api

import pytest


class TestAGroupInsideAGroup:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, upgrade_from) -> None:
        self.upgrade_from = upgrade_from
        self.types = api.portal.get_tool("portal_types")

    def test_the_fti_allows_a_group_inside_a_group(self):
        """The state a site has to end up in."""
        fti = self.types[GROUP_PORTAL_TYPE]

        assert fti.allowed_content_types == (GROUP_PORTAL_TYPE,)
        assert fti.filter_content_types is True

    def test_the_upgrade_restores_it_on_a_site_that_lost_it(self):
        """The upgrade, driven against exactly the state it exists for: the
        FTI a site installed before containment actually has."""
        fti = self.types[GROUP_PORTAL_TYPE]
        fti.allowed_content_types = ()
        assert fti.allowed_content_types == ()

        self.upgrade_from("1000")

        assert self.types[GROUP_PORTAL_TYPE].allowed_content_types == (
            GROUP_PORTAL_TYPE,
        )
