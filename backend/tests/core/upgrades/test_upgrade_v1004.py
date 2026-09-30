"""The step that removes property map rows no login applies.

The rows exist: the control panel took free text for the target field, and
this package's own default map seeded ``email`` into every provider created
through it. None of them was ever applied -- ``claim_fields`` filtered them
out on every login -- so the step is not about correctness of behaviour. It is
about a form that can be saved: the field refuses the whole map now, and a
provider carrying an old row refuses an edit nobody made.
"""

from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.upgrades.v1004 import drop_unmappable_rows
from pas.plugins.identity.upgrades.v1004 import usable

import pytest


class TestUsable:
    """The filter itself, without a site."""

    def test_keeps_a_row_a_login_writes(self):
        assert usable({"bio": "description"}) == {"bio": "description"}

    def test_drops_the_address(self):
        """Appended by ``sync_addresses``, never mapped."""
        assert usable({"email": "email"}) == {}

    def test_drops_the_portrait(self):
        """Synced from the ``picture_url`` claim, with no row at all."""
        assert usable({"picture": "portrait"}) == {}

    def test_drops_what_a_provider_may_never_write(self):
        assert usable({"username": "login", "teams": "group_ids"}) == {}

    def test_leaves_an_empty_map_empty(self):
        assert usable({}) == {}


class TestTheStep:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, store_legacy_propertymap) -> None:
        self.portal = portal
        self.store_legacy = store_legacy_propertymap
        set_providers([
            ProviderConfig(
                provider_id="github",
                driver_id="github",
                title="GitHub",
                propertymap={"bio": "description"},
            ),
            ProviderConfig(
                provider_id="keycloak",
                driver_id="oidc-generic",
                title="Keycloak",
                propertymap={"name": "fullname"},
            ),
        ])

    def test_a_dead_row_is_removed(self):
        self.store_legacy(
            "github", {"bio": "description", "email": "email", "picture": "portrait"}
        )

        drop_unmappable_rows(None)

        assert get_provider("github").propertymap == {"bio": "description"}

    def test_a_map_that_was_already_usable_is_left_alone(self):
        drop_unmappable_rows(None)

        assert get_provider("keycloak").propertymap == {"name": "fullname"}

    def test_every_provider_is_visited(self):
        """Not only the first one that needs it."""
        self.store_legacy("github", {"email": "email"})
        self.store_legacy("keycloak", {"name": "fullname", "picture": "portrait"})

        drop_unmappable_rows(None)

        assert get_provider("github").propertymap == {}
        assert get_provider("keycloak").propertymap == {"name": "fullname"}

    def test_what_it_leaves_behind_can_be_saved_again(self):
        """The point of the step. Before it, the provider's next save is
        refused by the field over a row the operator never typed."""
        self.store_legacy("github", {"bio": "description", "email": "email"})
        drop_unmappable_rows(None)

        set_providers([
            *(p for p in [get_provider("github")] if p is not None),
        ])

        assert get_provider("github").propertymap == {"bio": "description"}

    def test_a_row_removal_is_logged(self, caplog):
        """Nothing is lost, but a map is an operator's own configuration and
        a row disappearing from it without a word is not an upgrade."""
        self.store_legacy("github", {"email": "email"})

        with caplog.at_level("INFO"):
            drop_unmappable_rows(None)

        assert "dropping property map row" in caplog.text
        assert "'github'" in caplog.text
