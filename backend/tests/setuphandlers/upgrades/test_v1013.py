"""Version 1013: the ``personal_tools`` actions for Volto's user menu.

Driven against the state a site installed before them is in: no
``personal_tools`` category at all, and actions of its own in other
categories that the step must leave alone.
"""

from plone import api

import pytest


class TestPersonalToolsAdded:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, upgrade_from) -> None:
        self.tool = api.portal.get_tool("portal_actions")
        self.tool.manage_delObjects(["personal_tools"])
        self.tool["user"]["logout"].visible = False
        assert "personal_tools" not in self.tool.objectIds()

        upgrade_from("1012")

    def test_the_category_holds_every_entry(self):
        assert self.tool["personal_tools"].objectIds() == [
            "profile",
            "identity_profile",
            "preferences",
            "identities",
            "plone_setup",
        ]

    def test_the_other_categories_are_left_alone(self):
        """A merge, not a purge: an action a site changed keeps the change."""
        assert self.tool["user"]["logout"].visible is False
