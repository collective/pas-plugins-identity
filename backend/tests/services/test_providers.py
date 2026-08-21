"""Integration tests for the control-panel API (Gate 5, §4.5, S7/I4)."""

from . import DEX_METADATA
from . import DEX_PROVIDER
from .conftest import body
from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel import PROVIDERS_RECORD
from pas.plugins.identity.core.controlpanel import SECRET_SENTINEL
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.interfaces import FlowError
from pas.plugins.identity.core.services.providers import DriversGet
from pas.plugins.identity.core.services.providers import ProvidersDelete
from pas.plugins.identity.core.services.providers import ProvidersGet
from pas.plugins.identity.core.services.providers import ProvidersPatch
from pas.plugins.identity.core.services.providers import ProvidersPost
from plone import api
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import TEST_USER_NAME

import json
import pytest


@pytest.fixture()
def manager(portal):
    """Log in as somebody who may manage the site."""
    login(portal, TEST_USER_NAME)
    with api.env.adopt_roles(["Manager"]):
        yield


def call(service, portal, request_, *segments, payload=None):
    """Invoke one of the control-panel services.

    :param service: The service class.
    :param portal: The Plone site.
    :param request_: The current request.
    :param segments: Path segments after the endpoint name.
    :param payload: JSON body, if any.
    :returns: The service's reply.
    """
    if payload is not None:
        body(request_, payload)
    view = service(portal, request_)
    for segment in segments:
        view.publishTraverse(request_, segment)
    return view.reply()


class TestAccess:
    """Provider configuration names the site's identity providers and, for a
    misconfigured driver, could carry a secret. It is not public."""

    @pytest.mark.parametrize(
        "service",
        [DriversGet, ProvidersGet, ProvidersPost, ProvidersPatch, ProvidersDelete],
    )
    def test_anonymous_is_refused(self, portal, request_, service):
        """Nothing here answers anonymously."""
        logout()

        call(service, portal, request_, payload={})

        assert request_.response.getStatus() == 401

    @pytest.mark.parametrize("service", [DriversGet, ProvidersGet])
    def test_ordinary_member_is_refused(self, portal, request_, service):
        """Being logged in is not the same as being allowed."""
        login(portal, TEST_USER_NAME)

        result = call(service, portal, request_)

        assert request_.response.getStatus() == 403
        assert result["error"]["type"] == "Not allowed"


class TestDriverMetadata:
    def test_lists_every_driver(self, portal, request_, manager):
        """The widget renders a form per driver, so it needs them all."""
        result = call(DriversGet, portal, request_)

        assert {item["id"] for item in result["items"]} == {
            "github",
            "google",
            "oidc-generic",
            "email",
        }

    def test_carries_the_config_schema(self, portal, request_, manager):
        """Schema-driven rendering is the point (§4.5)."""
        result = call(DriversGet, portal, request_)
        github = next(i for i in result["items"] if i["id"] == "github")

        assert github["schema"]["client_id"]["secret"] is False
        assert github["schema"]["client_secret"]["secret"] is True

    def test_flags_which_fields_are_secret(self, portal, request_, manager):
        """So the widget can render a write-only field rather than a text box
        showing bullets that the user might try to edit."""
        result = call(DriversGet, portal, request_)

        for item in result["items"]:
            assert all("secret" in field for field in item["schema"].values())


class TestReading:
    def test_lists_configured_providers(self, portal, request_, manager, configured):
        """What the control panel shows."""
        result = call(ProvidersGet, portal, request_)

        assert [item["id"] for item in result["items"]] == ["dex", "github"]

    def test_reads_one(self, portal, request_, manager, configured):
        """Addressable individually, for an edit form."""
        result = call(ProvidersGet, portal, request_, "dex")

        assert result["id"] == "dex"
        assert result["@id"].endswith("/@identity-providers/dex")

    def test_unknown_is_a_404(self, portal, request_, manager, configured):
        """A provider that is not configured is not there."""
        call(ProvidersGet, portal, request_, "nope")

        assert request_.response.getStatus() == 404

    def test_secret_is_masked(self, portal, request_, manager, configured):
        """S7/I4 -- the client secret never leaves in readable form."""
        result = call(ProvidersGet, portal, request_, "dex")

        assert result["config"]["client_secret"] == SECRET_SENTINEL

    def test_non_secret_is_readable(self, portal, request_, manager, configured):
        """The client id is public by design; masking it would be useless
        and would stop an operator checking their own configuration."""
        result = call(ProvidersGet, portal, request_, "dex")

        assert result["config"]["client_id"] == "plone"

    def test_listing_masks_too(self, portal, request_, manager, configured):
        """Not just the detail view: it is the same data."""
        result = call(ProvidersGet, portal, request_)

        for item in result["items"]:
            assert SECRET_SENTINEL in item["config"].values()


class TestCreating:
    def test_creates_a_provider(self, portal, request_, manager):
        """The C of CRUD."""
        result = call(
            ProvidersPost,
            portal,
            request_,
            payload={
                "id": "new-one",
                "driver": "oidc-generic",
                "title": "New",
                "config": {"issuer": "https://idp.example", "client_id": "plone"},
            },
        )

        assert request_.response.getStatus() == 201
        assert result["id"] == "new-one"
        assert get_provider("new-one") is not None

    def test_stores_the_secret_unmasked(self, portal, request_, manager):
        """Masking is an exit filter, not storage."""
        call(
            ProvidersPost,
            portal,
            request_,
            payload={
                "id": "new-one",
                "driver": "github",
                "config": {"client_id": "x", "client_secret": "gho_real"},
            },
        )

        assert get_provider("new-one").config["client_secret"] == "gho_real"

    def test_id_and_driver_are_required(self, portal, request_, manager):
        """A provider with no driver cannot do anything."""
        call(ProvidersPost, portal, request_, payload={"id": "x"})

        assert request_.response.getStatus() == 400

    def test_unknown_driver_is_refused(self, portal, request_, manager):
        """Better to refuse than to create a record nothing can serve."""
        call(
            ProvidersPost,
            portal,
            request_,
            payload={"id": "x", "driver": "no-such-driver"},
        )

        assert request_.response.getStatus() == 400

    def test_duplicate_id_is_refused(self, portal, request_, manager, configured):
        """Reusing an id would silently re-point every identity already
        stored against it."""
        call(
            ProvidersPost,
            portal,
            request_,
            payload={"id": "dex", "driver": "oidc-generic"},
        )

        assert request_.response.getStatus() == 409

    def test_bad_action_path_is_refused(self, portal, request_, manager, configured):
        """POST to a path that is neither create nor an action."""
        call(ProvidersPost, portal, request_, "dex", payload={})

        assert request_.response.getStatus() == 400


class TestUpdating:
    def test_updates_the_title(self, portal, request_, manager, configured):
        """The U of CRUD."""
        call(ProvidersPatch, portal, request_, "dex", payload={"title": "Renamed"})

        assert get_provider("dex").title == "Renamed"

    def test_toggles_enabled(self, portal, request_, manager, configured):
        """Turning a provider off is the common operation."""
        call(ProvidersPatch, portal, request_, "dex", payload={"enabled": False})

        assert get_provider("dex").enabled is False

    def test_round_trip_preserves_the_secret(
        self, portal, request_, manager, configured
    ):
        """S7/I4 -- the whole reason unmask exists. Read the provider, change
        the title, PATCH the config straight back with its masked secret."""
        read = call(ProvidersGet, portal, request_, "dex")

        call(
            ProvidersPatch,
            portal,
            request_,
            "dex",
            payload={"title": "Renamed", "config": read["config"]},
        )

        assert get_provider("dex").config["client_secret"] == "plone-secret"
        assert get_provider("dex").title == "Renamed"

    def test_a_real_new_secret_replaces_it(self, portal, request_, manager, configured):
        """Rotation still has to work."""
        call(
            ProvidersPatch,
            portal,
            request_,
            "dex",
            payload={"config": {"client_secret": "rotated"}},
        )

        assert get_provider("dex").config["client_secret"] == "rotated"

    def test_unknown_is_a_404(self, portal, request_, manager, configured):
        """Nothing to update."""
        call(ProvidersPatch, portal, request_, "nope", payload={"title": "x"})

        assert request_.response.getStatus() == 404

    def test_path_must_name_one_provider(self, portal, request_, manager, configured):
        """PATCH on the collection is not an update."""
        call(ProvidersPatch, portal, request_, payload={"title": "x"})

        assert request_.response.getStatus() == 400


class TestDeleting:
    def test_removes_the_provider(self, portal, request_, manager, configured):
        """The D of CRUD."""
        call(ProvidersDelete, portal, request_, "dex")

        assert get_provider("dex") is None
        assert [p.provider_id for p in get_providers()] == ["github"]

    def test_identities_are_left_alone(self, portal, request_, manager, configured):
        """Deleting a provider is a configuration change. Silently dropping
        every account that logs in through it is not something a control
        panel should do unasked."""
        plugin = api.portal.get_tool("acl_users")["identity"]
        plugin.store.add("dex", "subject-1", "userid-1", {})

        call(ProvidersDelete, portal, request_, "dex")

        assert plugin.store.userid_for("dex", "subject-1") == "userid-1"

    def test_unknown_is_a_404(self, portal, request_, manager, configured):
        """Nothing to delete."""
        call(ProvidersDelete, portal, request_, "nope")

        assert request_.response.getStatus() == 404

    def test_path_must_name_one_provider(self, portal, request_, manager, configured):
        """DELETE on the collection would be a very bad button to expose."""
        call(ProvidersDelete, portal, request_)

        assert request_.response.getStatus() == 400


class TestConnectionCheck:
    def test_reports_success(
        self, portal, request_, manager, configured, stub_metadata
    ):
        """A reachable provider answers with the endpoints it resolved."""
        stub_metadata({**DEX_METADATA, "jwks": {"keys": []}})

        result = call(
            ProvidersPost, portal, request_, "dex", "test-connection", payload={}
        )

        assert result["ok"] is True
        assert result["token_endpoint"] == DEX_METADATA["token_endpoint"]

    def test_reports_failure_cleanly(
        self, portal, request_, manager, configured, stub_metadata
    ):
        """A dead URL is a report, not a traceback: this is a button an
        operator presses precisely when something is wrong."""
        stub_metadata(FlowError("dex: could not fetch discovery"))

        result = call(
            ProvidersPost, portal, request_, "dex", "test-connection", payload={}
        )

        assert result["ok"] is False
        assert "could not fetch" in result["error"]
        assert request_.response.getStatus() == 200

    def test_reports_whether_a_key_set_was_found(
        self, portal, request_, manager, configured, stub_metadata
    ):
        """Without a JWKS the id_token path cannot work, which is worth
        knowing before the first user tries to log in."""
        stub_metadata(DEX_METADATA)

        result = call(
            ProvidersPost, portal, request_, "dex", "test-connection", payload={}
        )

        assert result["has_jwks"] is False

    def test_unknown_provider_is_a_404(self, portal, request_, manager, configured):
        """Nothing to test."""
        call(ProvidersPost, portal, request_, "nope", "test-connection", payload={})

        assert request_.response.getStatus() == 404

    def test_driver_without_an_issuer_still_reports(
        self, portal, request_, manager, configured
    ):
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

        result = call(
            ProvidersPost, portal, request_, "email", "test-connection", payload={}
        )

        assert result["ok"] is False

    def test_check_is_not_answered_from_cache(
        self, portal, request_, manager, configured, stub_metadata, monkeypatch
    ):
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

        call(ProvidersPost, portal, request_, "dex", "test-connection", payload={})

        assert forgotten == [DEX_PROVIDER["config"]["issuer"]]


class TestGenericSetupRoundTrip:
    """The registry record is the single source of truth, and GenericSetup
    carries it (§4.5)."""

    def test_export_carries_the_providers(self, portal, request_, manager, configured):
        """What an export would pick up is the JSON we stored."""
        raw = api.portal.get_registry_record(PROVIDERS_RECORD)

        assert [entry["id"] for entry in json.loads(raw)] == ["dex", "github"]

    def test_reimport_restores_them(self, portal, request_, manager, configured):
        """Round trip: read the record out, wipe it, put it back."""
        raw = api.portal.get_registry_record(PROVIDERS_RECORD)
        set_providers([])
        assert get_providers() == []

        api.portal.set_registry_record(PROVIDERS_RECORD, raw)

        assert [p.provider_id for p in get_providers()] == ["dex", "github"]
        assert get_provider("dex").config["client_secret"] == "plone-secret"

    def test_api_export_omits_the_secret(self, portal, request_, manager, configured):
        """S7 -- what the *API* renders is masked even though the registry
        holds the real value, so an export taken through the REST surface
        cannot carry a secret out."""
        rendered = call(ProvidersGet, portal, request_)

        assert "plone-secret" not in json.dumps(rendered)
