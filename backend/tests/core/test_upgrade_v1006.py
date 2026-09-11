"""The step that holds exporting providers to Manager.

A permission declared in ZCML exists on every site as soon as the code does;
what an older site lacks is the rolemap's floor for it. The step is driven here
against a site whose setting for the permission is not that floor.
"""

from pas.plugins.identity.core.services.providers import EXPORT_PERMISSION
from pas.plugins.identity.upgrades.v1006 import restrict_provider_export
from plone import api

import pytest


class TestTheStep:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        # Widened and acquiring, so that the step visibly replaces a setting
        # rather than confirming one that was already right.
        portal.manage_permission(
            EXPORT_PERMISSION, roles=["Manager", "Site Administrator"], acquire=True
        )
        restrict_provider_export(api.portal.get_tool("portal_setup"))

    def test_acquisition_is_off(self):
        """Held wherever it is asked, whatever the application root grants."""
        assert not self.portal.acquiredRolesAreUsedBy(EXPORT_PERMISSION)

    def test_only_a_manager_holds_it(self):
        roles = [
            role["name"]
            for role in self.portal.rolesOfPermission(EXPORT_PERMISSION)
            if role["selected"]
        ]

        assert roles == ["Manager"]
