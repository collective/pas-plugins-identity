from . import PROFILE_ID
from . import UNINSTALL_PROFILE_ID
from pas.plugins.identity.server.clients import CLIENTS_RECORD
from pas.plugins.identity.server.interfaces import IIdentityServerLayer
from pas.plugins.identity.server.interfaces import IServerSettings
from plone import api
from plone.browserlayer.utils import registered_layers
from zope.schema import getFieldNames

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


class TestServerInstall:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_browser_layer_registered(self):
        """Everything this layer publishes binds to it, so its absence is
        what keeps an /authorize endpoint out of a site that never asked for
        one."""
        assert IIdentityServerLayer in registered_layers()

    def test_every_schema_field_has_a_record(self):
        """The XML is named after the interface, so a field added without a
        matching record would be read as its schema default and never
        noticed."""
        for name in getFieldNames(IServerSettings):
            record = f"pas.plugins.identity.{name}"
            assert api.portal.get_registry_record(record, default=None) is not None

    def test_the_ttl_default_is_fifteen_minutes(self):
        """D3."""
        assert (
            api.portal.get_registry_record(
                "pas.plugins.identity.server_access_token_ttl"
            )
            == 900
        )

    def test_no_clients_are_registered_out_of_the_box(self):
        """An empty string, not None: the record is deliberately left out of
        the XML so the schema default applies -- an empty <value> would
        import as None."""
        assert api.portal.get_registry_record(CLIENTS_RECORD) == ""

    def test_no_issuer_is_configured_out_of_the_box(self):
        """A site has to say what it is called before it can sign anything as
        that name."""
        assert (
            api.portal.get_registry_record("pas.plugins.identity.server_issuer") == ""
        )


class TestPostUninstall:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        setup = api.portal.get_tool("portal_setup")
        setup.runAllImportStepsFromProfile(f"profile-{UNINSTALL_PROFILE_ID}")

    def test_browser_layer_removed(self):
        """Which is what takes the endpoints away again."""
        assert IIdentityServerLayer not in registered_layers()

    @pytest.mark.parametrize(
        "name",
        ["server_clients", "server_issuer", "server_access_token_ttl"],
    )
    def test_records_removed(self, name):
        """Every field the schema declares, so uninstall stays in step with
        install rather than drifting a record at a time."""
        assert (
            api.portal.get_registry_record(
                f"pas.plugins.identity.{name}", default="gone"
            )
            == "gone"
        )
