"""Integration tests for provider configuration (§4.5, I4/S7)."""

from . import DISABLED_PROVIDER
from . import GITHUB_PROVIDER
from . import ORPHANED_PROVIDER
from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel import mask
from pas.plugins.identity.core.controlpanel import PROVIDERS_RECORD
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import SECRET_SENTINEL
from pas.plugins.identity.core.controlpanel import enabled_providers
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.controlpanel import unmask
from plone import api

import json
import pytest


#: Sentinel telling "record absent" apart from "record present but empty".
_MISSING = object()


@pytest.fixture()
def configured(portal):
    """Store one enabled and one disabled provider."""
    set_providers([
        ProviderConfig.deserialize(GITHUB_PROVIDER),
        ProviderConfig.deserialize(DISABLED_PROVIDER),
    ])


class TestRegistryRecord:
    def test_record_installed(self, portal):
        """The default profile created the record.

        An empty ``<value></value>`` for a Text field imports as ``None``
        rather than ``""``, which is why the reader coerces before parsing.
        """
        record = api.portal.get_registry_record(PROVIDERS_RECORD, default=_MISSING)

        assert record is not _MISSING
        assert not record

    def test_empty_registry_yields_no_providers(self, portal):
        """A fresh site offers nothing rather than erroring."""
        assert get_providers() == []

    def test_round_trip(self, portal):
        """What is stored comes back unchanged."""
        set_providers([ProviderConfig.deserialize(GITHUB_PROVIDER)])

        providers = get_providers()

        assert len(providers) == 1
        assert providers[0].provider_id == "github"
        assert providers[0].driver_id == "github"

    def test_stored_as_json(self, portal, configured):
        """The record is plain JSON, so GenericSetup can carry it."""
        raw = api.portal.get_registry_record(PROVIDERS_RECORD)

        assert [entry["id"] for entry in json.loads(raw)] == ["github", "google"]

    def test_secrets_stored_unmasked(self, portal, configured):
        """The backend keeps the real value -- masking is an exit filter."""
        stored = json.loads(api.portal.get_registry_record(PROVIDERS_RECORD))

        assert stored[0]["config"]["client_secret"] == "gho_supersecret"


class TestLookup:
    def test_get_provider(self, portal, configured):
        """A configured provider is found by id."""
        assert get_provider("github").driver_id == "github"

    def test_get_unknown_provider(self, portal, configured):
        """An unknown id yields ``None``."""
        assert get_provider("nope") is None

    def test_enabled_excludes_disabled(self, portal, configured):
        """A disabled provider is not offered for login."""
        assert [p.provider_id for p in enabled_providers()] == ["github"]

    def test_enabled_excludes_orphans(self, portal):
        """A provider whose driver is gone cannot work, so it is not shown."""
        set_providers([
            ProviderConfig.deserialize(GITHUB_PROVIDER),
            ProviderConfig.deserialize(ORPHANED_PROVIDER),
        ])

        assert [p.provider_id for p in enabled_providers()] == ["github"]

    def test_orphans_still_listed_for_management(self, portal):
        """The control panel must still show one, so it can be repaired."""
        set_providers([ProviderConfig.deserialize(ORPHANED_PROVIDER)])

        assert [p.provider_id for p in get_providers()] == ["legacy"]

    def test_driver_resolves(self, portal, configured):
        """The record names a real driver."""
        assert get_provider("github").driver.driver_id == "github"

    def test_orphan_driver_is_none(self, portal):
        """A missing driver is reported, not faked."""
        set_providers([ProviderConfig.deserialize(ORPHANED_PROVIDER)])

        assert get_provider("legacy").driver is None


class TestMasking:
    """I4/S7 -- secrets are write-only through every API surface."""

    def test_secret_is_masked(self, portal):
        """The client secret never leaves in readable form."""
        masked = mask("github", GITHUB_PROVIDER["config"])

        assert masked["client_secret"] == SECRET_SENTINEL

    def test_non_secret_survives(self, portal):
        """The client id is public and must stay readable."""
        masked = mask("github", GITHUB_PROVIDER["config"])

        assert masked["client_id"] == "Iv1.abc123"

    def test_empty_secret_not_masked(self, portal):
        """An unset secret reads as unset, not as "something is there"."""
        masked = mask("github", {"client_id": "x", "client_secret": ""})

        assert masked["client_secret"] == ""

    def test_serialize_masks_by_default(self, portal):
        """Anything rendered for an API response is masked."""
        provider = ProviderConfig.deserialize(GITHUB_PROVIDER)

        assert provider.serialize()["config"]["client_secret"] == SECRET_SENTINEL

    def test_serialize_for_storage_does_not_mask(self, portal):
        """Writing back to the registry keeps the real value."""
        provider = ProviderConfig.deserialize(GITHUB_PROVIDER)

        payload = provider.serialize(mask_secrets=False)

        assert payload["config"]["client_secret"] == "gho_supersecret"

    def test_unknown_driver_masks_everything(self, portal):
        """A removed driver must not start publishing its own secrets."""
        masked = mask("no-such-driver", ORPHANED_PROVIDER["config"])

        assert masked == {
            "client_id": SECRET_SENTINEL,
            "client_secret": SECRET_SENTINEL,
        }

    def test_orphan_serialize_masks_everything(self, portal):
        """The same protection through the object API."""
        provider = ProviderConfig.deserialize(ORPHANED_PROVIDER)

        config = provider.serialize()["config"]

        assert set(config.values()) == {SECRET_SENTINEL}


class TestUnmasking:
    """A control panel round-trip must not overwrite a secret with bullets."""

    def test_sentinel_restores_stored_secret(self, portal):
        """PATCHing back what was read leaves the secret alone."""
        stored = GITHUB_PROVIDER["config"]
        incoming = {**stored, "client_secret": SECRET_SENTINEL}

        result = unmask("github", incoming, stored)

        assert result["client_secret"] == "gho_supersecret"

    def test_new_value_replaces_secret(self, portal):
        """A real new secret is stored."""
        stored = GITHUB_PROVIDER["config"]
        incoming = {**stored, "client_secret": "gho_rotated"}

        result = unmask("github", incoming, stored)

        assert result["client_secret"] == "gho_rotated"

    def test_sentinel_without_stored_value_is_dropped(self, portal):
        """The sentinel is never written to the registry as a value."""
        incoming = {"client_id": "x", "client_secret": SECRET_SENTINEL}

        result = unmask("github", incoming, {})

        assert "client_secret" not in result

    def test_non_secret_fields_untouched(self, portal):
        """Unmasking only concerns secrets."""
        stored = GITHUB_PROVIDER["config"]
        incoming = {**stored, "client_id": "Iv1.changed"}

        result = unmask("github", incoming, stored)

        assert result["client_id"] == "Iv1.changed"

    def test_round_trip_preserves_secret(self, portal, configured):
        """The full read-modify-write cycle the control panel performs."""
        provider = get_provider("github")
        read = provider.serialize()

        read["title"] = "GitHub (renamed)"
        provider.title = read["title"]
        provider.config = unmask("github", read["config"], provider.config)
        set_providers([provider, get_provider("google")])

        stored = json.loads(api.portal.get_registry_record(PROVIDERS_RECORD))
        assert stored[0]["title"] == "GitHub (renamed)"
        assert stored[0]["config"]["client_secret"] == "gho_supersecret"


class TestProviderConfig:
    def test_title_falls_back_to_driver(self, portal):
        """A provider without a title still renders a login button."""
        provider = ProviderConfig("gh", "github")

        assert provider.serialize()["title"] == "GitHub"

    def test_title_wins_over_driver(self, portal):
        """A site can label its provider whatever it likes."""
        provider = ProviderConfig("gh", "github", title="Company SSO")

        assert provider.serialize()["title"] == "Company SSO"

    def test_orphan_title_falls_back_to_empty(self, portal):
        """No driver, no default title -- but no crash either."""
        provider = ProviderConfig("legacy", "no-such-driver")

        assert provider.serialize()["title"] == ""

    def test_defaults(self, portal):
        """A minimally-specified provider is enabled with no config."""
        provider = ProviderConfig("gh", "github")

        assert provider.enabled is True
        assert provider.config == {}

    def test_repr(self, portal):
        """The object has a readable repr for debugging."""
        provider = ProviderConfig("gh", "github")

        assert repr(provider) == "<ProviderConfig gh (github)>"
