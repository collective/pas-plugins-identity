"""Magic-link token lifetime and the burn store."""

from datetime import datetime
from datetime import timedelta
from datetime import UTC
from pas.plugins.identity.core.flows import magiclink
from plone import api

import pytest


class TestTTLClamping:
    """The lifetime is capped at fifteen minutes whatever is configured."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.plugin = api.portal.get_tool("acl_users")["identity"]

    @pytest.mark.parametrize("configured", [None, 0, -1, ""])
    def test_unusable_values_fall_back_to_the_default(self, configured):
        """A missing or nonsensical setting is not a licence for forever."""
        assert magiclink.ttl_for(configured) == magiclink.DEFAULT_TTL

    def test_a_shorter_ttl_is_honoured(self):
        """An operator may tighten it."""
        assert magiclink.ttl_for(60) == 60

    def test_a_longer_ttl_is_clamped(self):
        """But not loosen it past the ceiling: a link that lives longer stops
        being a login and becomes a bearer credential."""
        assert magiclink.ttl_for(86400) == magiclink.MAX_TTL


class TestBurnStoreHousekeeping:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.plugin = api.portal.get_tool("acl_users")["identity"]

    def test_expired_burns_are_swept(self):
        """The burn store only has to remember a token until it would have
        expired anyway; past that it is dead weight."""
        store = self.plugin.magic_links
        past = datetime.now(UTC) - timedelta(hours=1)
        store.burn("stale-jti", past)

        # Any write sweeps.
        store.burn("fresh-jti", datetime.now(UTC) + timedelta(minutes=5))

        assert store.is_burned("fresh-jti") is True
        assert store.is_burned("stale-jti") is False

    def test_counts_requests_in_the_window(self):
        """The counter a control panel would read to show remaining quota."""
        store = self.plugin.magic_links
        store.check_and_record("address:someone@plone.org", 5)
        store.check_and_record("address:someone@plone.org", 5)

        assert store.requests_in_window("address:someone@plone.org") == 2
        assert store.requests_in_window("address:nobody@plone.org") == 0

    def test_stale_stamps_do_not_count(self):
        """The limit is a rate, not a quota."""
        store = self.plugin.magic_links
        bucket = "address:someone@plone.org"
        store._requests[bucket] = [
            datetime.now(UTC) - magiclink.RATE_WINDOW - timedelta(minutes=1)
        ]

        assert store.requests_in_window(bucket) == 0


class TestLazyStore:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.plugin = api.portal.get_tool("acl_users")["identity"]

    def test_plugin_predating_the_store_gains_one(self):
        """A plugin persisted before magic links existed must not raise."""
        del self.plugin._magic_links

        store = self.plugin.magic_links

        assert isinstance(store, magiclink.MagicLinkStore)
        assert self.plugin.magic_links is store
