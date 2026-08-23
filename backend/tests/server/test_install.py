from . import PROFILE_ID
from . import UNINSTALL_PROFILE_ID
from pas.plugins.identity.server.clients import CLIENTS_RECORD
from pas.plugins.identity.server.controlpanel import CONFIGLET_ID
from pas.plugins.identity.server.controlpanel import IIdentityServerControlpanel
from pas.plugins.identity.server.interfaces import IIdentityServerLayer
from pas.plugins.identity.server.interfaces import IServerSettings
from pas.plugins.identity.server.pas import PLUGIN_ID
from pas.plugins.identity.server.setuphandlers import install_plugin
from pas.plugins.identity.server.setuphandlers import uninstall_plugin
from plone import api
from plone.api.exc import InvalidParameterError
from plone.browserlayer.utils import registered_layers
from Products.PluggableAuthService.interfaces.plugins import IChallengePlugin
from zope.interface import alsoProvides
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

    def test_the_configlet_is_removed(self):
        """A menu entry pointing at a panel whose endpoints are gone is
        worse than no entry."""
        tool = api.portal.get_tool("portal_controlpanel")

        assert CONFIGLET_ID not in [a.getId() for a in tool.listActions()]

    @pytest.mark.parametrize("name", getFieldNames(IServerSettings))
    def test_records_removed(self, name):
        """Driven off the schema rather than a hand-kept list, so a field
        added without a matching removal fails here instead of quietly
        surviving an uninstall. A literal list said "every field the schema
        declares" while naming three of them."""
        assert (
            api.portal.get_registry_record(
                f"pas.plugins.identity.{name}", default="gone"
            )
            == "gone"
        )


class TestTheControlPanel:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, http_request) -> None:
        self.portal = portal
        self.tool = api.portal.get_tool("portal_controlpanel")
        self.request = http_request

    def test_the_configlet_is_registered(self):
        """Without it the panel exists but nothing links to it, and
        `@controlpanels` does not list it."""
        assert CONFIGLET_ID in [action.getId() for action in self.tool.listActions()]

    def test_it_points_at_the_frontend_route(self):
        """There is no Classic fallback form on purpose: the client list is
        a JSON record of hashed secrets, and a generic registry edit form
        over it offers a textarea in which a typo unregisters an app."""
        action = next(a for a in self.tool.listActions() if a.getId() == CONFIGLET_ID)

        assert "controlpanel/identity-clients" in action.getActionExpression()

    def test_it_needs_manage_portal(self):
        action = next(a for a in self.tool.listActions() if a.getId() == CONFIGLET_ID)

        assert action.getPermissions() == ("Manage portal",)

    def test_the_panel_is_served(self):
        """`@controlpanels` routes by id, which is what the frontend route of
        the same name is listed under. The request is marked with the server
        layer here because the publisher does that from the browserlayer
        registration, and the adapter is bound to it deliberately."""
        request = self.portal.REQUEST
        alsoProvides(request, IIdentityServerLayer)

        panel = api.content.get_view(CONFIGLET_ID, self.portal, request)

        # get_view looks up by name only, so the interface the panel is
        # bound to is asserted rather than implied by the lookup.
        assert IIdentityServerControlpanel.providedBy(panel)

    def test_it_is_not_served_without_the_layer(self):
        """Which is what keeps it out of a site that never switched the
        authorization server on."""
        with pytest.raises(InvalidParameterError):
            api.content.get_view(CONFIGLET_ID, self.portal, self.request)


class TestThePlugin:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.acl_users = portal.acl_users

    def test_the_plugin_is_installed(self):
        """It is the persistent home for the authorization codes."""
        assert PLUGIN_ID in self.acl_users

    def test_it_activates_extraction_and_authentication(self):
        """Exactly the two the Bearer plugin implements, and no more: a
        plugin that claims an interface it does not implement would be asked
        to answer, and answering nothing is not the same as not being
        asked."""
        plugins = self.acl_users.plugins
        active = {
            info["id"]
            for info in plugins.listPluginTypeInfo()
            if PLUGIN_ID in plugins.listPluginIds(info["interface"])
        }

        assert active == {"IExtractionPlugin", "IAuthenticationPlugin"}

    def test_it_does_not_challenge(self):
        """A request that fails to authenticate should fall through to
        whatever the site already does. Answering `WWW-Authenticate: Bearer`
        would be this add-on deciding the site is an API."""
        plugins = self.acl_users.plugins

        assert PLUGIN_ID not in plugins.listPluginIds(IChallengePlugin)

    def test_uninstalling_deactivates_it_everywhere(self):
        """A registration pointing at a deleted object is worse than an
        unused plugin, so uninstall sweeps every interface rather than the
        list install happens to know about."""
        plugins = self.acl_users.plugins

        uninstall_plugin(self.acl_users)

        assert not [
            info["id"]
            for info in plugins.listPluginTypeInfo()
            if PLUGIN_ID in plugins.listPluginIds(info["interface"])
        ]

    def test_installing_twice_keeps_the_codes_in_flight(self):
        """Re-applying the profile must not swap the plugin out from under a
        code that is mid-flow. Asserted through the store's contents rather
        than through object identity: `acl_users[PLUGIN_ID]` hands back a
        fresh acquisition wrapper every time, so `is` compares wrappers and
        passes for two different plugins as readily as for one."""
        code = self.acl_users[PLUGIN_ID].codes.issue(
            "app", "alice", "https://app.example.org/cb"
        )

        install_plugin(self.acl_users)

        assert self.acl_users[PLUGIN_ID].codes.redeem(
            code, "app", "https://app.example.org/cb"
        )

    def test_the_code_store_survives_a_missing_attribute(self):
        """A plugin persisted before the store existed keeps working, rather
        than needing an upgrade step for data worth sixty seconds."""
        plugin = self.acl_users[PLUGIN_ID]
        del plugin._codes

        assert plugin.codes.count() == 0

    def test_the_consent_store_survives_a_missing_attribute(self):
        """Same reasoning as the code store, with the opposite stakes: a lost
        code costs somebody one retry, a lost consent record costs them a
        prompt they have already answered."""
        plugin = self.acl_users[PLUGIN_ID]
        del plugin._consent

        assert plugin.consent.granted("alice", "app") is False

    def test_the_refresh_store_survives_a_missing_attribute(self):
        """The third store on this plugin, and the mildest loss of the three:
        losing it logs every client out rather than corrupting anything."""
        plugin = self.acl_users[PLUGIN_ID]
        del plugin._refresh

        assert plugin.refresh.count() == 0

    def test_uninstalling_when_absent_is_quiet(self):
        """A second uninstall, or one on a site that never installed it."""
        uninstall_plugin(self.acl_users)

        uninstall_plugin(self.acl_users)

        assert PLUGIN_ID not in self.acl_users
