"""Integration tests for the control-panel API."""

from .. import body
from . import DEX_METADATA
from . import DEX_PROVIDER
from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel import PROVIDERS_RECORD
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
    with api.env.adopt_roles(["Manager"]):
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
    def test_ordinary_member_is_refused(self, service):
        """Being logged in is not the same as being allowed."""
        login(self.portal, TEST_USER_NAME)

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
            "email",
        }

    def test_carries_the_config_schema(self):
        """Schema-driven rendering is the point."""
        result = self.call(DriversGet)
        github = next(i for i in result["items"] if i["id"] == "github")

        assert github["schema"]["client_id"]["secret"] is False
        assert github["schema"]["client_secret"]["secret"] is True

    def test_flags_which_fields_are_secret(self):
        """So the widget can render a write-only field rather than a text box
        showing bullets that the user might try to edit."""
        result = self.call(DriversGet)

        for item in result["items"]:
            assert all("secret" in field for field in item["schema"].values())


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


class TestGenericSetupRoundTrip(ControlPanelCase):
    """The registry record is the single source of truth, and GenericSetup
    carries it."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, manager, configured) -> None:
        self.portal = portal
        self.request = request_

    def test_export_carries_the_providers(self):
        """What an export would pick up is the JSON we stored."""
        raw = api.portal.get_registry_record(PROVIDERS_RECORD)

        assert [entry["id"] for entry in json.loads(raw)] == ["dex", "github"]

    def test_reimport_restores_them(self):
        """Round trip: read the record out, wipe it, put it back."""
        raw = api.portal.get_registry_record(PROVIDERS_RECORD)
        set_providers([])
        assert get_providers() == []

        api.portal.set_registry_record(PROVIDERS_RECORD, raw)

        assert [p.provider_id for p in get_providers()] == ["dex", "github"]
        assert get_provider("dex").config["client_secret"] == "plone-secret"

    def test_api_export_omits_the_secret(self):
        """What the *API* renders is masked even though the registry
        holds the real value, so an export taken through the REST surface
        cannot carry a secret out."""
        rendered = self.call(ProvidersGet)

        assert "plone-secret" not in json.dumps(rendered)
