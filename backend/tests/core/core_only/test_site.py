"""What installing ``core`` alone gives a site, and what each part does there."""

from . import CORE_PROFILE
from . import PROVIDER
from . import sign_in
from pas.plugins.identity import PACKAGE_NAME
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.controlpanel.controlpanel import CONFIGLET_ID
from pas.plugins.identity.core.controlpanel.controlpanel import IdentityConfigletPanel
from pas.plugins.identity.core.controlpanel.interfaces import IIdentityCorePanelSchema
from pas.plugins.identity.core.interfaces import IUsersAsContent
from pas.plugins.identity.core.interfaces import LockoutRefused
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.core.pas.profile import PLUGIN_ID as PROFILE_PLUGIN_ID
from pas.plugins.identity.core.principal_types import users_as_content
from pas.plugins.identity.core.services.jwt import mint_token
from pas.plugins.identity.exportimport import export_site
from pas.plugins.identity.exportimport import ExportImportError
from pas.plugins.identity.exportimport import import_site
from pas.plugins.identity.exportimport.schema import NOT_CONTENT
from plone import api
from plone.app.testing import logout
from plone.restapi.deserializer.controlpanels import ControlpanelDeserializeFromJson
from plone.restapi.serializer.controlpanels import ControlpanelSerializeToJson
from Products.GenericSetup.tool import UNKNOWN
from zExceptions import BadRequest

import json
import pytest


pytestmark = pytest.mark.no_profile_container

#: Where ``core``'s settings live in the registry.
SETTINGS = "pas.plugins.identity"


class TestTheInstall:
    @pytest.fixture(autouse=True)
    def _setup(self, core_only) -> None:
        self.portal = core_only
        self.setup = api.portal.get_tool("portal_setup")
        self.acl_users = api.portal.get_tool("acl_users")

    def test_core_is_installed(self):
        assert self.setup.getLastVersionForProfile(CORE_PROFILE) == ("1000",)

    def test_contenttypes_is_not(self):
        profile_id = f"{PACKAGE_NAME}:contenttypes"

        assert self.setup.getLastVersionForProfile(profile_id) == UNKNOWN

    def test_the_site_is_not_marked(self):
        assert not IUsersAsContent.providedBy(self.portal)
        assert users_as_content() is False

    def test_the_identity_plugin_is_installed(self):
        assert PLUGIN_ID in self.acl_users.objectIds()

    def test_the_profile_plugin_is_not(self):
        assert PROFILE_PLUGIN_ID not in self.acl_users.objectIds()

    def test_no_user_type(self):
        assert "UserProfile" not in api.portal.get_tool("portal_types").objectIds()

    def test_the_type_records_are_empty(self):
        """Which is what makes the adder decline to ``source_users``."""
        assert (
            api.portal.get_registry_record("pas.plugins.identity.user_content_type")
            == ""
        )

    def test_api_user_create_uses_source_users(self):
        api.user.create(email="bob@example.com", username="bob", password="secret123!")

        assert "bob" in self.acl_users.source_users.getUserIds()


class TestAFirstLogin:
    """A first federated login writes the account the rest of Plone sees."""

    @pytest.fixture(autouse=True)
    def _setup(self, identity_plugin) -> None:
        self.plugin = identity_plugin
        self.userid = sign_in(identity_plugin)

    def test_the_user_exists(self):
        """Before this, the login returned a userid nothing could resolve."""
        assert api.user.get(userid=self.userid) is not None

    def test_the_account_is_a_source_users_row(self):
        source_users = api.portal.get_tool("acl_users").source_users

        assert self.userid in source_users.getUserIds()

    def test_a_token_can_be_minted(self):
        """The callback's last step, which answered 500 without an account."""
        assert mint_token(self.userid)

    def test_the_name_is_seeded(self):
        member = api.user.get(userid=self.userid)

        assert member.getProperty("fullname") == "Érico Andrei"

    def test_the_first_offered_address_is_the_email(self):
        """No Profile holds every address here, and nobody is asked."""
        member = api.user.get(userid=self.userid)

        assert member.getProperty("email") == "erico@plone.org"

    def test_the_password_is_a_placeholder(self):
        assert self.userid in self.plugin.placeholder_passwords

    def test_the_placeholder_is_not_a_way_in(self):
        """The lockout guard must not count it, or the last identity could go."""
        with pytest.raises(LockoutRefused):
            self.plugin.unlink(self.userid, PROVIDER, "dex-subject-1")

    def test_a_second_login_is_the_same_user(self):
        assert sign_in(self.plugin) == self.userid


class TestAMissingAccount:
    """An identity whose account was deleted gets the same userid back."""

    @pytest.fixture(autouse=True)
    def _setup(self, identity_plugin) -> None:
        self.plugin = identity_plugin
        self.userid = sign_in(identity_plugin)
        api.user.delete(username=self.userid)
        assert api.user.get(userid=self.userid) is None

    def test_the_account_is_restored(self):
        assert sign_in(self.plugin) == self.userid
        assert api.user.get(userid=self.userid) is not None


class TestThePropertyMap:
    """Applied to the member's properties, and never over a value."""

    @pytest.fixture(autouse=True)
    def _setup(self, identity_plugin) -> None:
        self.plugin = identity_plugin
        set_providers([
            ProviderConfig(
                provider_id=PROVIDER,
                driver_id="oidc-generic",
                title="Dex",
                propertymap={"location": "location"},
            )
        ])

    def test_a_mapped_claim_is_written(self):
        userid = sign_in(self.plugin)

        assert api.user.get(userid=userid).getProperty("location") == "Brasília"

    def test_a_local_edit_survives_the_next_login(self):
        userid = sign_in(self.plugin)
        api.user.get(userid=userid).setMemberProperties({"location": "Recife"})

        sign_in(self.plugin)

        assert api.user.get(userid=userid).getProperty("location") == "Recife"


class TestTheGroupMap:
    """Membership lands in ``source_groups``, which is where this site keeps it."""

    @pytest.fixture(autouse=True)
    def _setup(self, identity_plugin) -> None:
        self.plugin = identity_plugin
        api.group.create(groupname="site-staff")
        set_providers([
            ProviderConfig(
                provider_id=PROVIDER,
                driver_id="oidc-generic",
                title="Dex",
                groupmap={"staff": "site-staff"},
            )
        ])

    def test_a_new_user_is_added_to_the_mapped_group(self):
        """It raised ``UserNotFoundError`` while the user had no account."""
        userid = sign_in(self.plugin)

        groups = [group.getId() for group in api.group.get_groups(username=userid)]

        assert "site-staff" in groups


class TestThePanel:
    @pytest.fixture(autouse=True)
    def _setup(self, core_only, http_request) -> None:
        self.portal = core_only
        self.request = http_request

    def test_the_schema_has_no_profile_settings(self):
        panel = api.content.get_view(CONFIGLET_ID, self.portal, self.request)

        assert panel.schema is IIdentityCorePanelSchema

    def test_the_panel_serializes(self):
        """Naming a record the site lacks failed the whole panel."""
        panel = IdentityConfigletPanel(self.portal, self.request)
        # The serializer builds the panel's ``@id`` from ``__name__``, which
        # the publisher sets while traversing and nothing sets here.
        panel.__name__ = CONFIGLET_ID

        data = ControlpanelSerializeToJson(panel)()

        assert "profile_container_id" not in data["data"]
        assert "callback_url" in data["data"]

    def test_the_classic_form_renders(self):
        view = api.content.get_view("identity-controlpanel", self.portal, self.request)

        assert "callback_url" in view()


class TestThePersonalTools:
    @pytest.fixture(autouse=True)
    def _setup(self, core_only, http_request) -> None:
        self.portal = core_only
        self.request = http_request

    def test_the_profile_is_volto_s_own_form(self):
        view = api.content.get_view("identity-profile-url", self.portal, self.request)

        assert view() == f"{self.portal.absolute_url()}/personal-information"

    def test_anonymous_has_none(self):
        logout()
        view = api.content.get_view("identity-profile-url", self.portal, self.request)

        assert view() == ""


class TestExportImport:
    """A document is Profiles and Groups, and this site has neither."""

    @pytest.fixture(autouse=True)
    def _setup(self, core_only) -> None:
        self.portal = core_only

    def test_an_export_is_refused(self):
        with pytest.raises(ExportImportError, match="contenttypes"):
            export_site()

    def test_an_import_is_refused(self):
        document = {"version": 1, "generator": "x", "groups": [], "users": []}

        result = import_site(document)

        assert result.refusals == [NOT_CONTENT]


class TestSavingThePanel:
    """``PATCH @controlpanels`` with whatever a client sends.

    A frontend built against a site with Profiles, or a script copying one
    site's settings to another, sends the profile settings as well. This
    site has no records for them, and creating them would put half of the
    ``contenttypes`` profile on a site that never installed it.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, core_only, http_request) -> None:
        self.portal = core_only
        self.request = http_request
        self.registry = api.portal.get_tool("portal_registry")

    def save(self, data: dict) -> None:
        """Save through the panel, as ``PATCH @controlpanels`` does.

        :param data: The request body.
        """
        self.request["BODY"] = json.dumps(data)
        panel = IdentityConfigletPanel(self.portal, self.request)
        panel.__name__ = CONFIGLET_ID
        ControlpanelDeserializeFromJson(panel)()

    def test_a_setting_of_this_site_is_saved(self):
        self.save({"callback_url": "/signed-in"})

        assert api.portal.get_registry_record(f"{SETTINGS}.callback_url") == (
            "/signed-in"
        )

    def test_profile_settings_create_no_records(self):
        self.save({
            "callback_url": "/signed-in",
            "profile_container_id": "people",
            "profile_enumeration_states": ["complete"],
        })

        assert not [
            name for name in self.registry.records if "profile_container" in name
        ]

    def test_profile_settings_do_not_stop_the_rest(self):
        self.save({"profile_container_id": "people", "callback_url": "/signed-in"})

        assert api.portal.get_registry_record(f"{SETTINGS}.callback_url") == (
            "/signed-in"
        )

    def test_a_value_the_field_refuses_is_refused(self):
        with pytest.raises(BadRequest):
            self.save({"discovery_timeout": "soon"})


class TestDocumentsOfAnyShape:
    """Nothing is written on this site, whatever a document holds."""

    @pytest.fixture(autouse=True)
    def _setup(self, core_only) -> None:
        self.portal = core_only
        self.source_users = api.portal.get_tool("acl_users").source_users

    @pytest.mark.parametrize(
        "document",
        [
            None,
            "a string",
            [],
            42,
            {},
            {"version": 999, "users": [], "groups": []},
            {"version": 1, "users": "not a list", "groups": []},
            {
                "version": 1,
                "groups": [],
                "users": [{"userid": "ericof", "emails": ["erico@plone.org"]}],
            },
        ],
        ids=[
            "null",
            "string",
            "list",
            "integer",
            "empty",
            "future",
            "users-not-a-list",
            "valid",
        ],
    )
    @pytest.mark.parametrize("dry_run", [True, False], ids=["dry", "wet"])
    def test_it_is_refused(self, document, dry_run):
        users = set(self.source_users.getUserIds())

        result = import_site(document, dry_run=dry_run)

        assert result.refused
        assert set(self.source_users.getUserIds()) == users
