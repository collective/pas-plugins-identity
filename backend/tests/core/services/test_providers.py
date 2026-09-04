"""Integration tests for the control-panel API."""

from .. import body
from . import DEX_METADATA
from . import DEX_PROVIDER
from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.controlpanel import get_provider_record
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel import provider_record_names
from pas.plugins.identity.core.controlpanel import PROVIDERS_PREFIX
from pas.plugins.identity.core.controlpanel import SECRET_SENTINEL
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.interfaces import FlowError
from pas.plugins.identity.core.services.providers.delete import ProvidersDelete
from pas.plugins.identity.core.services.providers.drivers import DriversGet
from pas.plugins.identity.core.services.providers.get import ProvidersGet
from pas.plugins.identity.core.services.providers.patch import ProvidersPatch
from pas.plugins.identity.core.services.providers.post import ProvidersPost
from plone import api
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import TEST_USER_NAME

import json
import pytest


@pytest.fixture
def manager(portal):
    """Log in as somebody who may manage the site."""
    login(portal, TEST_USER_NAME)
    yield


class ControlPanelCase:
    """Invokes the control-panel services against this test's request."""

    def call(self, service, *segments, payload=None):
        """Invoke one of the control-panel services.

        :param service: The service class.
        :param segments: Path segments after the endpoint name.
        :param payload: JSON body, if any.
        :returns: The service's reply.
        """
        if payload is not None:
            body(self.request, payload)
        view = service(self.portal, self.request)
        for segment in segments:
            view.publishTraverse(self.request, segment)
        return view.reply()

    def status(self) -> int:
        """Return the status the service answered with.

        :returns: The HTTP status.
        """
        return self.request.response.getStatus()


class TestAccess(ControlPanelCase):
    """Provider configuration names the site's identity providers and, for a
    misconfigured driver, could carry a secret. It is not public."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_) -> None:
        self.portal = portal
        self.request = request_

    @pytest.mark.parametrize(
        "service",
        [DriversGet, ProvidersGet, ProvidersPost, ProvidersPatch, ProvidersDelete],
    )
    def test_anonymous_is_refused(self, service):
        """Nothing here answers anonymously."""
        logout()

        self.call(service, payload={})

        assert self.status() == 401

    @pytest.mark.parametrize("service", [DriversGet, ProvidersGet])
    def test_ordinary_member_is_refused(self, service, member):
        """Being logged in is not the same as being allowed.

        A member of its own rather than the shared test user: the fixtures in
        ``tests/core/conftest.py`` make that one a ``Manager`` for the whole
        directory, so asking it this question would answer 200 and prove the
        opposite of what is written here.
        """
        result = self.call(service)

        assert self.status() == 403
        assert result["error"]["type"] == "Not allowed"


class TestDriverMetadata(ControlPanelCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, manager) -> None:
        self.portal = portal
        self.request = request_

    def test_lists_every_driver(self):
        """The widget renders a form per driver, so it needs them all."""
        result = self.call(DriversGet)

        assert {item["id"] for item in result["items"]} == {
            "github",
            "google",
            "oidc-generic",
            "plone-identity",
            "email",
        }

    def test_carries_an_ordinary_json_schema(self):
        """The shape `plone.restapi` emits everywhere else, so a client needs
        to know nothing about this package to build the form."""
        result = self.call(DriversGet)
        github = next(i for i in result["items"] if i["id"] == "github")
        schema = github["schema"]

        assert schema["type"] == "object"
        assert "client_id" in schema["properties"]
        assert "client_id" in schema["required"]
        assert schema["fieldsets"]

    def test_the_secret_is_a_password_widget(self):
        """So the form renders a write-only field rather than a text box
        showing bullets that somebody might try to edit."""
        result = self.call(DriversGet)
        github = next(i for i in result["items"] if i["id"] == "github")

        assert github["schema"]["properties"]["client_secret"]["widget"] == "password"

    def test_titles_are_translated_rather_than_literal(self):
        """The whole reason the hand-built dict had to go: it carried English
        strings that no `.po` file could ever reach."""
        result = self.call(DriversGet)
        github = next(i for i in result["items"] if i["id"] == "github")

        assert github["schema"]["properties"]["client_id"]["title"] == "Client ID"

    def test_the_userid_source_is_a_vocabulary(self):
        """Not a list of pairs this package invented a format for."""
        result = self.call(DriversGet)
        github = next(i for i in result["items"] if i["id"] == "github")
        field = github["schema"]["properties"]["userid_source"]

        assert [choice[0] for choice in field["choices"]] == [
            "uuid",
            "username",
            "email",
            "subject",
        ]

    def test_the_issuer_comes_first_for_a_discovered_provider(self):
        """`order_before`, honoured by `plone.autoform` -- which is what
        replaced spacing an `order` key by tens."""
        result = self.call(DriversGet)
        oidc = next(i for i in result["items"] if i["id"] == "oidc-generic")

        assert oidc["schema"]["fieldsets"][0]["fields"][0] == "issuer"


class TestReading(ControlPanelCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, manager, configured) -> None:
        self.portal = portal
        self.request = request_

    def test_lists_configured_providers(self):
        """What the control panel shows."""
        result = self.call(ProvidersGet)

        assert [item["id"] for item in result["items"]] == ["dex", "github"]

    def test_reads_one(self):
        """Addressable individually, for an edit form."""
        result = self.call(ProvidersGet, "dex")

        assert result["id"] == "dex"
        assert result["@id"].endswith("/@identity-providers/dex")

    def test_unknown_is_a_404(self):
        """A provider that is not configured is not there."""
        self.call(ProvidersGet, "nope")

        assert self.status() == 404

    def test_secret_is_masked(self):
        """The client secret never leaves in readable form."""
        result = self.call(ProvidersGet, "dex")

        assert result["config"]["client_secret"] == SECRET_SENTINEL

    def test_non_secret_is_readable(self):
        """The client id is public by design; masking it would be useless
        and would stop an operator checking their own configuration."""
        result = self.call(ProvidersGet, "dex")

        assert result["config"]["client_id"] == "plone"

    def test_listing_masks_too(self):
        """Not just the detail view: it is the same data."""
        result = self.call(ProvidersGet)

        for item in result["items"]:
            assert SECRET_SENTINEL in item["config"].values()


class TestCreating(ControlPanelCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, manager) -> None:
        self.portal = portal
        self.request = request_

    def test_creates_a_provider(self):
        """The C of CRUD."""
        result = self.call(
            ProvidersPost,
            payload={
                "id": "new-one",
                "driver": "oidc-generic",
                "title": "New",
                "config": {"issuer": "https://idp.example", "client_id": "plone"},
            },
        )

        assert self.status() == 201
        assert result["id"] == "new-one"
        assert get_provider("new-one") is not None

    def test_stores_the_secret_unmasked(self):
        """Masking is an exit filter, not storage."""
        self.call(
            ProvidersPost,
            payload={
                "id": "new-one",
                "driver": "github",
                "config": {"client_id": "x", "client_secret": "gho_real"},
            },
        )

        assert get_provider("new-one").config["client_secret"] == "gho_real"

    def test_id_and_driver_are_required(self):
        """A provider with no driver cannot do anything."""
        self.call(ProvidersPost, payload={"id": "x"})

        assert self.status() == 400

    def test_unknown_driver_is_refused(self):
        """Better to refuse than to create a record nothing can serve."""
        self.call(
            ProvidersPost,
            payload={"id": "x", "driver": "no-such-driver"},
        )

        assert self.status() == 400

    def test_duplicate_id_is_refused(self, configured):
        """Reusing an id would silently re-point every identity already
        stored against it."""
        self.call(
            ProvidersPost,
            payload={"id": "dex", "driver": "oidc-generic"},
        )

        assert self.status() == 409

    def test_bad_action_path_is_refused(self, configured):
        """POST to a path that is neither create nor an action."""
        self.call(ProvidersPost, "dex", payload={})

        assert self.status() == 400


class TestUpdating(ControlPanelCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, manager, configured) -> None:
        self.portal = portal
        self.request = request_

    def test_updates_the_title(self):
        """The U of CRUD."""
        self.call(ProvidersPatch, "dex", payload={"title": "Renamed"})

        assert get_provider("dex").title == "Renamed"

    def test_toggles_enabled(self):
        """Turning a provider off is the common operation."""
        self.call(ProvidersPatch, "dex", payload={"enabled": False})

        assert get_provider("dex").enabled is False

    def test_toggles_login_visibility(self):
        """Taking a provider off the login screen leaves it usable."""
        self.call(ProvidersPatch, "dex", payload={"show_in_login": False})

        provider = get_provider("dex")

        assert provider.show_in_login is False
        assert provider.usable is True

    def test_stores_a_style(self):
        """Icon and colours are what the login button is drawn from."""
        self.call(
            ProvidersPatch,
            "dex",
            payload={
                "icon": '<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0"/></svg>',
                "background_color": "#24292F",
            },
        )

        provider = get_provider("dex")

        assert "<path" in provider.icon
        assert provider.background_color == "#24292f"

    def test_stores_a_foreground_colour(self):
        """The other half of the pair, and the one a monochrome icon uses."""
        self.call(ProvidersPatch, "dex", payload={"foreground_color": "#FFF"})

        assert get_provider("dex").foreground_color == "#fff"

    def test_refuses_an_icon_that_is_not_an_svg(self):
        """400 rather than a traceback, and rather than a silent empty icon:
        an operator who pasted the wrong thing has to find out here."""
        result = self.call(ProvidersPatch, "dex", payload={"icon": "<html/>"})

        assert self.status() == 400
        assert result["error"]["type"] == "Invalid style"

    def test_refuses_a_colour_that_is_not_hex(self):
        """The value reaches a style attribute in the frontend."""
        self.call(ProvidersPatch, "dex", payload={"background_color": "red"})

        assert self.status() == 400

    def test_round_trip_preserves_the_secret(self):
        """The whole reason unmask exists. Read the provider, change
        the title, PATCH the config straight back with its masked secret."""
        read = self.call(ProvidersGet, "dex")

        self.call(
            ProvidersPatch,
            "dex",
            payload={"title": "Renamed", "config": read["config"]},
        )

        assert get_provider("dex").config["client_secret"] == "plone-secret"
        assert get_provider("dex").title == "Renamed"

    def test_a_real_new_secret_replaces_it(self):
        """Rotation still has to work."""
        self.call(
            ProvidersPatch,
            "dex",
            payload={"config": {"client_secret": "rotated"}},
        )

        assert get_provider("dex").config["client_secret"] == "rotated"

    def test_unknown_is_a_404(self):
        """Nothing to update."""
        self.call(ProvidersPatch, "nope", payload={"title": "x"})

        assert self.status() == 404

    def test_path_must_name_one_provider(self):
        """PATCH on the collection is not an update."""
        self.call(ProvidersPatch, payload={"title": "x"})

        assert self.status() == 400


class TestDeleting(ControlPanelCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, manager, configured) -> None:
        self.portal = portal
        self.request = request_

    def test_removes_the_provider(self):
        """The D of CRUD."""
        self.call(ProvidersDelete, "dex")

        assert get_provider("dex") is None
        assert [p.provider_id for p in get_providers()] == ["github"]

    def test_identities_are_left_alone(self):
        """Deleting a provider is a configuration change. Silently dropping
        every account that logs in through it is not something a control
        panel should do unasked."""
        plugin = api.portal.get_tool("acl_users")["identity"]
        plugin.store.add("dex", "subject-1", "userid-1", {})

        self.call(ProvidersDelete, "dex")

        assert plugin.store.userid_for("dex", "subject-1") == "userid-1"

    def test_unknown_is_a_404(self):
        """Nothing to delete."""
        self.call(ProvidersDelete, "nope")

        assert self.status() == 404

    def test_path_must_name_one_provider(self):
        """DELETE on the collection would be a very bad button to expose."""
        self.call(ProvidersDelete)

        assert self.status() == 400


class TestConnectionCheck(ControlPanelCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, manager, configured) -> None:
        self.portal = portal
        self.request = request_

    def test_reports_success(self, stub_metadata):
        """A reachable provider answers with the endpoints it resolved."""
        stub_metadata({**DEX_METADATA, "jwks": {"keys": []}})

        result = self.call(ProvidersPost, "dex", "test-connection", payload={})

        assert result["ok"] is True
        assert result["token_endpoint"] == DEX_METADATA["token_endpoint"]

    def test_reports_failure_cleanly(self, stub_metadata):
        """A dead URL is a report, not a traceback: this is a button an
        operator presses precisely when something is wrong."""
        stub_metadata(FlowError("dex: could not fetch discovery"))

        result = self.call(ProvidersPost, "dex", "test-connection", payload={})

        assert result["ok"] is False
        assert "could not fetch" in result["error"]
        assert self.status() == 200

    def test_reports_whether_a_key_set_was_found(self, stub_metadata):
        """Without a JWKS the id_token path cannot work, which is worth
        knowing before the first user tries to log in."""
        stub_metadata(DEX_METADATA)

        result = self.call(ProvidersPost, "dex", "test-connection", payload={})

        assert result["has_jwks"] is False

    def test_unknown_provider_is_a_404(self):
        """Nothing to test."""
        self.call(ProvidersPost, "nope", "test-connection", payload={})

        assert self.status() == 404

    def test_driver_without_an_issuer_still_reports(self):
        """The email driver has nothing to reach, and the check must say so
        rather than raise while trying to clear a cache that never existed."""
        from pas.plugins.identity.core.controlpanel import ProviderConfig
        from pas.plugins.identity.core.controlpanel import set_providers

        set_providers([
            *get_providers(),
            ProviderConfig.deserialize({
                "id": "email",
                "driver": "email",
                "enabled": True,
                "config": {},
            }),
        ])

        result = self.call(ProvidersPost, "email", "test-connection", payload={})

        assert result["ok"] is False

    def test_check_is_not_answered_from_cache(self, stub_metadata, monkeypatch):
        """A button that reports the last answer rather than the current one
        is worse than no button."""
        from pas.plugins.identity.core.flows import metadata as flow_metadata

        forgotten = []
        real_forget = flow_metadata.forget
        monkeypatch.setattr(
            flow_metadata,
            "forget",
            lambda issuer=None: (forgotten.append(issuer), real_forget(issuer))[1],
        )
        stub_metadata(DEX_METADATA)

        self.call(ProvidersPost, "dex", "test-connection", payload={})

        assert forgotten == [DEX_PROVIDER["config"]["issuer"]]


class TestPropertyMapThroughTheAPI(ControlPanelCase):
    """The control panel edits the map over the same endpoints."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, manager, configured) -> None:
        self.portal = portal
        self.request = request_

    def test_created_with_a_map(self):
        rendered = self.call(
            ProvidersPost,
            payload={
                "id": "keycloak",
                "driver": "oidc-generic",
                "propertymap": {"preferred_username": "username"},
            },
        )

        assert rendered["propertymap"] == {"preferred_username": "username"}
        assert get_provider("keycloak").propertymap == {
            "preferred_username": "username"
        }

    def test_listing_carries_the_map(self):
        rendered = self.call(ProvidersGet)

        assert "propertymap" in rendered["items"][0]

    def test_patched_in_place(self):
        self.call(ProvidersPatch, "dex", payload={"propertymap": {"login": "username"}})

        assert get_provider("dex").propertymap == {"login": "username"}

    def test_patch_can_clear_the_map(self):
        self.call(ProvidersPatch, "dex", payload={"propertymap": {}})

        assert get_provider("dex").propertymap == {}

    def test_a_dot_in_an_id_is_refused(self):
        """It would split into a further registry record level."""
        rendered = self.call(
            ProvidersPost,
            payload={"id": "not.allowed", "driver": "oidc-generic"},
        )

        assert rendered["error"]["type"] == "Invalid provider id"


class TestGenericSetupRoundTrip(ControlPanelCase):
    """The registry records are the single source of truth, and GenericSetup
    carries them."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, manager, configured) -> None:
        self.portal = portal
        self.request = request_

    def _values(self) -> dict:
        """Capture every provider record the way an export would.

        :returns: Mapping of record name to stored value.
        """
        values = {}
        for name in provider_record_names():
            provider_id, field = name[len(PROVIDERS_PREFIX) :].split(".", 1)
            values[name] = get_provider_record(provider_id, field)
        return values

    def test_export_carries_every_setting_as_its_own_record(self):
        """An export picks up real records, not one blob to be parsed."""
        names = set(provider_record_names())

        assert f"{PROVIDERS_PREFIX}dex.driver" in names
        assert f"{PROVIDERS_PREFIX}dex.config.client_secret" in names
        assert f"{PROVIDERS_PREFIX}github.enabled" in names

    def test_rewriting_reproduces_the_same_records(self):
        """Round trip: capture the records, wipe them, write the same
        providers back, and land on byte-identical records. That is the
        property an export and re-import depends on."""
        before = self._values()
        # Guards the comparison below: two dicts of None would match each
        # other happily and prove nothing.
        assert before[f"{PROVIDERS_PREFIX}dex.config.client_secret"] == "plone-secret"
        providers = get_providers()
        set_providers([])
        assert provider_record_names() == []

        set_providers(providers)

        assert self._values() == before
        assert [p.provider_id for p in get_providers()] == ["dex", "github"]
        assert get_provider("dex").config["client_secret"] == "plone-secret"

    def test_api_export_omits_the_secret(self):
        """What the *API* renders is masked even though the registry
        holds the real value, so an export taken through the REST surface
        cannot carry a secret out."""
        rendered = self.call(ProvidersGet)

        assert "plone-secret" not in json.dumps(rendered)


class TestASignInPolicyThatAdmitsNobody(ControlPanelCase):
    """``create_user`` off with nothing to match an existing account on.

    Switching it off means "admit only people who already have an account
    here", and the only thing that finds one is a match on a verified address.
    Without ``auto_link_by_email`` to look, and ``trust_email_verification``
    for this provider's word to count, there is nothing to match on: every
    sign-in is refused, on the first login and every login after it, with
    nothing on the login page to say why.

    So the combination is refused where an operator's edit arrives, rather
    than saved and discovered by a user who cannot get in.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, manager, configured) -> None:
        self.portal = portal
        self.request = request_

    def create(self, config: dict):
        """POST a new provider carrying a config.

        :param config: The driver settings to send.
        :returns: The service's reply.
        """
        return self.call(
            ProvidersPost,
            payload={
                "id": "gated",
                "driver": "oidc-generic",
                "config": {"issuer": "https://idp.example", **config},
            },
        )

    def test_creating_it_is_refused(self):
        self.create({"create_user": False})

        assert self.status() == 400

    def test_the_refusal_says_what_to_switch_on(self):
        """An error naming neither switch would leave an operator guessing at
        which of two unrelated-looking fields it meant."""
        result = self.create({"create_user": False})

        assert "auto_link_by_email" in result["error"]["message"]
        assert "trust_email_verification" in result["error"]["message"]

    def test_nothing_is_stored(self):
        self.create({"create_user": False})

        assert get_provider("gated") is None

    def test_half_of_it_is_still_refused(self):
        """Both switches are needed, so one of them is not enough."""
        self.create({"create_user": False, "auto_link_by_email": True})

        assert self.status() == 400

    def test_the_workable_combination_is_accepted(self):
        """The half that keeps this from being a switch nobody can use."""
        self.create({
            "create_user": False,
            "auto_link_by_email": True,
            "trust_email_verification": True,
        })

        assert self.status() == 201

    def test_leaving_it_on_needs_neither_switch(self):
        """The default, and every site that never touches this."""
        self.create({"create_user": True})

        assert self.status() == 201

    def test_patching_into_it_is_refused_too(self):
        """The edit that turns a working provider into a locked one, which is
        the likelier way to arrive here."""
        self.call(
            ProvidersPatch,
            "dex",
            payload={"config": {"create_user": False}},
        )

        assert self.status() == 400

    def test_the_patch_leaves_the_provider_alone(self):
        self.call(
            ProvidersPatch,
            "dex",
            payload={"config": {"create_user": False}},
        )

        assert get_provider("dex").config.get("create_user") is not False


class TestEditingAProviderWhoseConfigHasAList(ControlPanelCase):
    """``PATCH @identity-providers/<id>`` with an array in the body.

    The route from the traceback, driven end to end: the frontend round-trips
    a provider's whole configuration back, JSON turns every tuple into an
    array, and an array decodes to a list. The write then put that list
    against a ``Tuple`` record and answered 500.

    Worth going through the service rather than the storage helpers, because
    what made this reach an operator is that it happens on an edit nobody
    would associate with configuration at all -- a checkbox.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, manager, configured) -> None:
        self.portal = portal
        self.request = request_

    def test_toggling_a_checkbox_does_not_fail(self):
        """The reported symptom: unchecking "show on the login page".

        204 rather than 200: the service answers with no body, and Zope
        downgrades an empty 200. What matters here is that it is not a 500.
        """
        self.call(
            ProvidersPatch,
            "dex",
            payload={"show_in_login": False, "config": {"scope": ["openid"]}},
        )

        assert self.status() == 204

    def test_the_toggle_took_effect(self):
        """So the fix cannot be a service that swallows the write."""
        self.call(
            ProvidersPatch,
            "dex",
            payload={"show_in_login": False, "config": {"scope": ["openid"]}},
        )

        assert get_provider("dex").show_in_login is False

    def test_the_list_is_stored_as_a_tuple(self):
        self.call(
            ProvidersPatch, "dex", payload={"config": {"scope": ["openid", "email"]}}
        )

        assert get_provider("dex").config["scope"] == ("openid", "email")

    def test_an_empty_array_is_stored(self):
        """The value in the traceback, and what a form sends for a collection
        nobody filled in."""
        self.call(ProvidersPatch, "dex", payload={"config": {"scope": []}})

        assert get_provider("dex").config["scope"] == ()

    def test_a_driver_with_no_collection_in_its_schema(self):
        """The magic-link provider, which is where this was found. Its schema
        declares two integers, so nothing about the key being sent says it
        should be a tuple -- and the record it lands in is one anyway."""
        self.call(
            ProvidersPost,
            payload={"id": "magic", "driver": "email", "config": {"scope": []}},
        )

        assert self.status() == 201
        assert get_provider("magic").config["scope"] == ()

    def test_creating_one_with_an_array_works_too(self):
        """``POST`` builds a provider where ``PATCH`` assigns to one, and both
        have to hold."""
        self.call(
            ProvidersPost,
            payload={
                "id": "new-one",
                "driver": "oidc-generic",
                "config": {"issuer": "https://idp.example", "scope": ["openid"]},
            },
        )

        assert self.status() == 201
        assert get_provider("new-one").config["scope"] == ("openid",)
