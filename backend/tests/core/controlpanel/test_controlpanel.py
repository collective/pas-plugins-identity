"""The control panel entry, and the registry records behind it.

The panel people use is rendered by the frontend, so what has to be true on
the backend is narrow but easy to lose: the configlet exists and points
somewhere real, the adapter is registered under the name the frontend routes
to, the Classic form renders, and every record the settings schema declares
was actually created by the profile.
"""

from pas.plugins.identity.core.controlpanel.controlpanel import CONFIGLET_ID
from pas.plugins.identity.core.controlpanel.interfaces import IIdentityControlpanel
from pas.plugins.identity.core.controlpanel.interfaces import IIdentitySettings
from pas.plugins.identity.core.controlpanel.view import IdentitySettingsControlPanel
from plone import api
from zope.component import getMultiAdapter
from zope.component import queryMultiAdapter
from zope.schema import getFieldNames

import pytest


class TestConfiglet:
    @pytest.fixture(scope="class")
    def portal(self, portal_class):
        """Return the portal."""
        yield portal_class

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.tool = api.portal.get_tool("portal_controlpanel")

    def test_configlet_is_registered(self):
        """Without it the panel exists but nothing links to it."""
        assert CONFIGLET_ID in [action.id for action in self.tool.listActions()]

    def test_configlet_needs_manage_portal(self):
        """Provider configuration is not for ordinary members."""
        action = next(a for a in self.tool.listActions() if a.id == CONFIGLET_ID)

        assert action.permissions == ("Manage portal",)

    def test_configlet_points_at_the_classic_form(self):
        """A control panel entry that 404s is worse than no entry."""
        action = next(a for a in self.tool.listActions() if a.id == CONFIGLET_ID)

        assert "identity-controlpanel" in action.getActionExpression()

    def test_panel_adapter_is_reachable(self):
        """``@controlpanels/identity-providers`` resolves to our panel."""
        panel = queryMultiAdapter(
            (self.portal, self.portal.REQUEST),
            IIdentityControlpanel,
            name=CONFIGLET_ID,
        )

        assert panel is not None
        assert panel.schema is IIdentitySettings


class TestSettingsRecords:
    @pytest.fixture(scope="class")
    def portal(self, portal_class):
        """Return the portal."""
        yield portal_class

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    @pytest.mark.parametrize("name", getFieldNames(IIdentitySettings))
    def test_record_exists(self, name: str):
        """Every field in the schema is a record the profile created."""
        record = f"pas.plugins.identity.{name}"

        assert api.portal.get_registry_record(record, default=None) is not None

    @pytest.mark.parametrize(
        "name,expected",
        [
            ("callback_url", ""),
            ("audit_max_entries", 500),
            ("audit_max_days", 180),
            ("audit_record_pii", False),
        ],
    )
    def test_default_value(self, name: str, expected):
        """The shipped defaults, which the privacy notes depend on."""
        assert (
            api.portal.get_registry_record(f"pas.plugins.identity.{name}") == expected
        )


class TestClassicView:
    """The plain registry form the configlet points at."""

    @pytest.fixture(scope="class")
    def portal(self, portal_class):
        """Return the portal."""
        yield portal_class

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.request = portal.REQUEST

    def test_view_is_registered(self):
        """Reachable as ``@@identity-controlpanel``."""
        view = getMultiAdapter(
            (self.portal, self.request), name="identity-controlpanel"
        )

        assert isinstance(view, IdentitySettingsControlPanel)

    def test_form_edits_the_settings_schema(self):
        """The same schema the profile imports, under the same prefix, so the
        form writes the records the rest of the package reads."""
        view = getMultiAdapter(
            (self.portal, self.request), name="identity-controlpanel"
        )

        assert view.form.schema is IIdentitySettings
        assert view.form.schema_prefix == "pas.plugins.identity"

    def test_view_renders(self):
        """Rendering is the only thing that catches a broken widget or a
        field the registry has no record for."""
        view = getMultiAdapter(
            (self.portal, self.request), name="identity-controlpanel"
        )

        assert "identity-controlpanel" in view()
