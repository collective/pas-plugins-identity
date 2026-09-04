"""Integration tests for provider configuration."""

from . import DISABLED_PROVIDER
from . import GITHUB_PROVIDER
from . import ORPHANED_PROVIDER
from pas.plugins.identity.core.controlpanel import enabled_providers
from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.controlpanel import get_provider_record
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel import InvalidProviderId
from pas.plugins.identity.core.controlpanel import mask
from pas.plugins.identity.core.controlpanel import provider_record_names
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import SECRET_SENTINEL
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.controlpanel import unmask

import pytest


@pytest.fixture
def configured(portal):
    """Store one enabled and one disabled provider.

    :param portal: The Plone site.
    """
    set_providers([
        ProviderConfig.deserialize(GITHUB_PROVIDER),
        ProviderConfig.deserialize(DISABLED_PROVIDER),
    ])


class TestRegistryRecord:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_no_records_on_a_fresh_site(self):
        """Nothing is created until a provider is."""
        assert provider_record_names() == []

    def test_empty_registry_yields_no_providers(self):
        """A fresh site offers nothing rather than erroring."""
        assert get_providers() == []

    def test_round_trip(self):
        """What is stored comes back unchanged."""
        set_providers([ProviderConfig.deserialize(GITHUB_PROVIDER)])

        providers = get_providers()

        assert len(providers) == 1
        assert providers[0].provider_id == "github"
        assert providers[0].driver_id == "github"

    def test_a_list_setting_round_trips_as_a_tuple(self, configured):
        """A scope is a list of permissions, and comes back as one.

        Stored in a ``Tuple`` record rather than a ``TextLine``: a scope
        typed into one text box is where a stray comma becomes a permission
        of its own that the provider then rejects as unknown.
        """
        assert get_provider_record("github", "config.scope") == (
            "read:user",
            "user:email",
        )

    def test_a_list_arriving_as_json_is_stored(self):
        """JSON has one sequence type, and it decodes to a list.

        The record holding it takes a tuple, so a scope submitted through
        the control panel would be refused on the way in -- with a
        ``WrongType`` naming the value rather than the shape.
        """
        provider = ProviderConfig.deserialize(GITHUB_PROVIDER)
        provider.config = {**provider.config, "scope": ["repo", "gist"]}

        set_providers([provider])

        assert get_provider_record("github", "config.scope") == ("repo", "gist")

    def test_each_setting_is_its_own_record(self, configured):
        """A field is a record, not a key inside a blob."""
        assert get_provider_record("github", "driver") == "github"
        assert get_provider_record("github", "enabled") is True
        assert get_provider_record("google", "enabled") is False

    def test_config_records_are_nested_under_config(self, configured):
        """Driver settings are namespaced away from the provider's own."""
        assert (
            get_provider_record("github", "config.client_id")
            == GITHUB_PROVIDER["config"]["client_id"]
        )

    def test_secrets_stored_unmasked(self, configured):
        """The backend keeps the real value -- masking is an exit filter."""
        assert (
            get_provider_record("github", "config.client_secret") == "gho_supersecret"
        )

    def test_order_is_recorded(self, configured):
        """Records read back alphabetically, so order is stored explicitly."""
        assert get_provider_record("github", "order") == 0
        assert get_provider_record("google", "order") == 1

    def test_stored_order_survives_the_alphabet(self):
        """A provider list is returned in its order, not sorted by id."""
        set_providers([
            ProviderConfig.deserialize(DISABLED_PROVIDER),
            ProviderConfig.deserialize(GITHUB_PROVIDER),
        ])

        assert [p.provider_id for p in get_providers()] == ["google", "github"]

    def test_removed_provider_leaves_nothing_behind(self, configured):
        """Rewriting a shorter list deletes the vanished provider's records."""
        set_providers([ProviderConfig.deserialize(GITHUB_PROVIDER)])

        assert provider_record_names("google") == []

    def test_bool_config_round_trips_as_bool(self):
        """The driver's schema types the record, so a flag stays a flag."""
        set_providers([
            ProviderConfig(
                provider_id="gh",
                driver_id="github",
                config={"auto_link_by_email": True},
            )
        ])

        assert get_providers()[0].config["auto_link_by_email"] is True

    def test_a_dot_in_an_id_is_refused(self):
        """It would split into a further record level and lose the setting."""
        with pytest.raises(InvalidProviderId):
            set_providers([ProviderConfig(provider_id="a.b", driver_id="github")])


class TestLookup:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_get_provider(self, configured):
        """A configured provider is found by id."""
        assert get_provider("github").driver_id == "github"

    def test_get_unknown_provider(self, configured):
        """An unknown id yields ``None``."""
        assert get_provider("nope") is None

    def test_enabled_excludes_disabled(self, configured):
        """A disabled provider is not offered for login."""
        assert [p.provider_id for p in enabled_providers()] == ["github"]

    def test_enabled_excludes_orphans(self):
        """A provider whose driver is gone cannot work, so it is not shown."""
        set_providers([
            ProviderConfig.deserialize(GITHUB_PROVIDER),
            ProviderConfig.deserialize(ORPHANED_PROVIDER),
        ])

        assert [p.provider_id for p in enabled_providers()] == ["github"]

    def test_orphans_still_listed_for_management(self):
        """The control panel must still show one, so it can be repaired."""
        set_providers([ProviderConfig.deserialize(ORPHANED_PROVIDER)])

        assert [p.provider_id for p in get_providers()] == ["legacy"]

    def test_driver_resolves(self, configured):
        """The record names a real driver."""
        assert get_provider("github").driver.driver_id == "github"

    def test_orphan_driver_is_none(self):
        """A missing driver is reported, not faked."""
        set_providers([ProviderConfig.deserialize(ORPHANED_PROVIDER)])

        assert get_provider("legacy").driver is None


class TestMasking:
    """Secrets are write-only through every API surface."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.config = GITHUB_PROVIDER["config"]

    def test_secret_is_masked(self):
        """The client secret never leaves in readable form."""
        masked = mask("github", self.config)

        assert masked["client_secret"] == SECRET_SENTINEL

    def test_non_secret_survives(self):
        """The client id is public and must stay readable."""
        masked = mask("github", self.config)

        assert masked["client_id"] == "Iv1.abc123"

    def test_empty_secret_not_masked(self):
        """An unset secret reads as unset, not as "something is there"."""
        masked = mask("github", {"client_id": "x", "client_secret": ""})

        assert masked["client_secret"] == ""

    def test_serialize_masks_by_default(self):
        """Anything rendered for an API response is masked."""
        provider = ProviderConfig.deserialize(GITHUB_PROVIDER)

        assert provider.serialize()["config"]["client_secret"] == SECRET_SENTINEL

    def test_serialize_for_storage_does_not_mask(self):
        """Writing back to the registry keeps the real value."""
        provider = ProviderConfig.deserialize(GITHUB_PROVIDER)

        payload = provider.serialize(mask_secrets=False)

        assert payload["config"]["client_secret"] == "gho_supersecret"

    def test_unknown_driver_masks_everything(self):
        """A removed driver must not start publishing its own secrets."""
        masked = mask("no-such-driver", ORPHANED_PROVIDER["config"])

        assert masked == {
            "client_id": SECRET_SENTINEL,
            "client_secret": SECRET_SENTINEL,
        }

    def test_orphan_serialize_masks_everything(self):
        """The same protection through the object API."""
        provider = ProviderConfig.deserialize(ORPHANED_PROVIDER)

        config = provider.serialize()["config"]

        assert set(config.values()) == {SECRET_SENTINEL}


class TestUnmasking:
    """A control panel round-trip must not overwrite a secret with bullets."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.stored = GITHUB_PROVIDER["config"]
        self.orphaned = ORPHANED_PROVIDER["config"]

    def test_sentinel_restores_stored_secret(self):
        """PATCHing back what was read leaves the secret alone."""
        incoming = {**self.stored, "client_secret": SECRET_SENTINEL}

        result = unmask("github", incoming, self.stored)

        assert result["client_secret"] == "gho_supersecret"

    def test_new_value_replaces_secret(self):
        """A real new secret is stored."""
        incoming = {**self.stored, "client_secret": "gho_rotated"}

        result = unmask("github", incoming, self.stored)

        assert result["client_secret"] == "gho_rotated"

    def test_sentinel_without_stored_value_is_dropped(self):
        """The sentinel is never written to the registry as a value."""
        incoming = {"client_id": "x", "client_secret": SECRET_SENTINEL}

        result = unmask("github", incoming, {})

        assert "client_secret" not in result

    def test_non_secret_fields_untouched(self):
        """Unmasking only concerns secrets."""
        incoming = {**self.stored, "client_id": "Iv1.changed"}

        result = unmask("github", incoming, self.stored)

        assert result["client_id"] == "Iv1.changed"

    def test_unknown_driver_restores_every_sentinel(self):
        """:func:`mask` masked every value for an orphaned provider, so
        unmasking must restore every one of them -- otherwise the round-trip
        that only renamed the provider overwrites its whole config with
        bullets."""
        incoming = dict.fromkeys(self.orphaned, SECRET_SENTINEL)

        result = unmask("no-such-driver", incoming, self.orphaned)

        assert result == self.orphaned

    def test_unknown_driver_still_accepts_new_values(self):
        """Restoring sentinels must not freeze an orphan's configuration."""
        incoming = {
            **dict.fromkeys(self.orphaned, SECRET_SENTINEL),
            "client_id": "new-id",
        }

        result = unmask("no-such-driver", incoming, self.orphaned)

        assert result["client_id"] == "new-id"
        assert result["client_secret"] == "legacy-secret"

    def test_round_trip_preserves_secret(self, configured):
        """The full read-modify-write cycle the control panel performs."""
        provider = get_provider("github")
        read = provider.serialize()

        read["title"] = "GitHub (renamed)"
        provider.title = read["title"]
        provider.config = unmask("github", read["config"], provider.config)
        set_providers([provider, get_provider("google")])

        assert get_provider_record("github", "title") == "GitHub (renamed)"
        assert (
            get_provider_record("github", "config.client_secret") == "gho_supersecret"
        )


class TestProviderConfig:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.provider = ProviderConfig("gh", "github")

    def test_title_falls_back_to_driver(self):
        """A provider without a title still renders a login button."""
        assert self.provider.serialize()["title"] == "GitHub"

    def test_title_wins_over_driver(self):
        """A site can label its provider whatever it likes."""
        provider = ProviderConfig("gh", "github", title="Company SSO")

        assert provider.serialize()["title"] == "Company SSO"

    def test_orphan_title_falls_back_to_empty(self):
        """No driver, no default title -- but no crash either."""
        provider = ProviderConfig("legacy", "no-such-driver")

        assert provider.serialize()["title"] == ""

    def test_enabled_unless_told_otherwise(self):
        """A minimally-specified provider is offered."""
        assert self.provider.enabled is True

    def test_driver_defaults_fill_in(self):
        """A provider created with no config still gets sane settings.

        The scope in particular: GitHub's API returns no email address
        without it, so a provider created without one is a sign-in that
        half works.
        """
        assert self.provider.config == {
            "scope": ("read:user", "user:email"),
            "trust_email_verification": True,
            "accept_string_booleans": False,
            "auto_link_by_email": False,
            "create_user": True,
            "userid_source": "username",
        }

    def test_a_supplied_value_wins(self):
        """The default fills a gap; it never overrules a decision."""
        provider = ProviderConfig("gh", "github", config={"scope": ["repo"]})

        assert provider.config["scope"] == ("repo",)

    def test_an_explicit_empty_value_is_kept(self):
        """Clearing a setting is a decision, not a gap to fill."""
        provider = ProviderConfig("gh", "github", config={"scope": []})

        assert provider.config["scope"] == ()

    def test_a_field_with_no_default_stays_absent(self):
        """Nothing is invented for a setting only the operator can know."""
        assert "client_id" not in self.provider.config

    def test_an_orphan_gets_nothing(self):
        """No driver, no schema, no defaults -- and no crash."""
        provider = ProviderConfig("legacy", "no-such-driver", config={"a": "b"})

        assert provider.config == {"a": "b"}

    def test_repr(self):
        """The object has a readable repr for debugging."""
        assert repr(self.provider) == "<ProviderConfig gh (github)>"
