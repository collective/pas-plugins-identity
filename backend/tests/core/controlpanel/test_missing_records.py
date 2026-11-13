"""A site that keeps its users as content and lacks some of the records for it.

The marker says Profile settings belong on the panel; the registry is what
holds them. When the two disagree, the panel used to name a field with no
record and fail as a whole with a ``KeyError`` -- the settings the site does
have went with it. It now serves the panel a site without Profiles gets, and
the log names the profile step that puts the records back.
"""

from pas.plugins.identity.core.controlpanel.controlpanel import CONFIGLET_ID
from pas.plugins.identity.core.controlpanel.controlpanel import IdentityConfigletPanel
from pas.plugins.identity.core.controlpanel.controlpanel import SCHEMA_PREFIX
from pas.plugins.identity.core.controlpanel.controlpanel import served_schema
from pas.plugins.identity.core.controlpanel.interfaces import IIdentityCorePanelSchema
from pas.plugins.identity.core.controlpanel.interfaces import IIdentityPanelSchema
from pas.plugins.identity.core.controlpanel.interfaces import IProfileSettings
from plone import api
from plone.restapi.serializer.controlpanels import ControlpanelSerializeToJson
from zope.schema import getFieldNames

import logging
import pytest


#: One Profile setting, and the record a site may have lost.
LOST = "profile_container_id"


def forget(*names: str) -> None:
    """Delete Profile setting records from the registry.

    :param names: Field names of :class:`IProfileSettings`.
    """
    records = api.portal.get_tool("portal_registry").records
    for name in names:
        del records[f"{SCHEMA_PREFIX}.{name}"]


class TestTheSchema:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_with_every_record_the_profile_settings_are_served(self):
        assert served_schema() is IIdentityPanelSchema

    def test_one_lost_record_leaves_them_out(self):
        forget(LOST)

        assert served_schema() is IIdentityCorePanelSchema

    def test_every_lost_record_leaves_them_out(self):
        forget(*getFieldNames(IProfileSettings))

        assert served_schema() is IIdentityCorePanelSchema

    def test_the_log_names_the_remedy(self, caplog):
        forget(LOST)

        with caplog.at_level(logging.WARNING):
            served_schema()

        assert "pas.plugins.identity:contenttypes" in caplog.text
        assert LOST in caplog.text

    def test_nothing_is_written_to_fix_it(self):
        """Reading a panel is not where a registry gets changed."""
        forget(LOST)

        served_schema()

        assert (
            f"{SCHEMA_PREFIX}.{LOST}"
            not in api.portal.get_tool("portal_registry").records
        )


class TestThePanels:
    """Both panels stay up, with the settings the site does have."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, http_request) -> None:
        self.portal = portal
        self.request = http_request
        forget(LOST)

    def test_the_rest_panel_serializes(self):
        panel = IdentityConfigletPanel(self.portal, self.request)
        panel.__name__ = CONFIGLET_ID

        data = ControlpanelSerializeToJson(panel)()

        assert LOST not in data["data"]
        assert "callback_url" in data["data"]

    def test_the_classic_form_renders(self):
        view = api.content.get_view("identity-controlpanel", self.portal, self.request)

        assert "callback_url" in view()

    def test_a_reinstall_brings_them_back(self):
        """The remedy the log names, applied the way it says."""
        setup = api.portal.get_tool("portal_setup")
        setup.runImportStepFromProfile(
            "profile-pas.plugins.identity:contenttypes", "plone.app.registry"
        )

        assert served_schema() is IIdentityPanelSchema
