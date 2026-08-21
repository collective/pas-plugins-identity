"""The magic-link edges the round-trip tests do not reach (Gate 3, S5)."""

from datetime import datetime
from datetime import timedelta
from datetime import UTC
from pas.plugins.identity.core.flows import magiclink
from pas.plugins.identity.core.services import magiclink as service
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from plone import api

import pytest


class TestTTLClamping:
    """S5 caps the lifetime at fifteen minutes whatever is configured."""

    @pytest.mark.parametrize("configured", [None, 0, -1, ""])
    def test_unusable_values_fall_back_to_the_default(self, portal, configured):
        """A missing or nonsensical setting is not a licence for forever."""
        assert magiclink.ttl_for(configured) == magiclink.DEFAULT_TTL

    def test_a_shorter_ttl_is_honoured(self, portal):
        """An operator may tighten it."""
        assert magiclink.ttl_for(60) == 60

    def test_a_longer_ttl_is_clamped(self, portal):
        """But not loosen it past the S5 ceiling: a link that lives longer
        stops being a login and becomes a bearer credential."""
        assert magiclink.ttl_for(86400) == magiclink.MAX_TTL


class TestBurnStoreHousekeeping:
    def test_expired_burns_are_swept(self, portal):
        """The burn store only has to remember a token until it would have
        expired anyway; past that it is dead weight."""
        store = api.portal.get_tool("acl_users")["identity"].magic_links
        past = datetime.now(UTC) - timedelta(hours=1)
        store.burn("stale-jti", past)

        # Any write sweeps.
        store.burn("fresh-jti", datetime.now(UTC) + timedelta(minutes=5))

        assert store.is_burned("fresh-jti") is True
        assert store.is_burned("stale-jti") is False

    def test_counts_requests_in_the_window(self, portal):
        """The counter a control panel would read to show remaining quota."""
        store = api.portal.get_tool("acl_users")["identity"].magic_links
        store.check_and_record("address:someone@plone.org", 5)
        store.check_and_record("address:someone@plone.org", 5)

        assert store.requests_in_window("address:someone@plone.org") == 2
        assert store.requests_in_window("address:nobody@plone.org") == 0

    def test_stale_stamps_do_not_count(self, portal):
        """The limit is a rate, not a quota."""
        store = api.portal.get_tool("acl_users")["identity"].magic_links
        bucket = "address:someone@plone.org"
        store._requests[bucket] = [
            datetime.now(UTC) - magiclink.RATE_WINDOW - timedelta(minutes=1)
        ]

        assert store.requests_in_window(bucket) == 0


class TestLazyStore:
    def test_plugin_predating_the_store_gains_one(self, portal):
        """A plugin persisted before magic links existed must not raise."""
        plugin = api.portal.get_tool("acl_users")["identity"]
        del plugin._magic_links

        store = plugin.magic_links

        assert isinstance(store, magiclink.MagicLinkStore)
        assert plugin.magic_links is store


class TestAutoLinkEdges:
    def test_claims_without_an_address_cannot_match(self, portal, configured):
        """A provider that verifies an address it did not send us matches
        nothing -- and must not raise on the way to deciding that."""
        from pas.plugins.identity.core.controlpanel import get_providers
        from pas.plugins.identity.core.controlpanel import set_providers

        providers = get_providers()
        for provider in providers:
            if provider.provider_id == "dex":
                provider.config = {**provider.config, "auto_link_by_email": True}
        set_providers(providers)

        plugin = api.portal.get_tool("acl_users")["identity"]
        userid, _ = plugin.authenticateCredentials({
            "extractor": "pas.plugins.identity",
            "provider": "dex",
            "subject": "no-address",
            "claims": {"email_verified": True},
        })

        assert plugin.store.userid_for("dex", "no-address") == userid
        assert plugin.store.identities_for(userid)[0].provider == "dex"


class TestMisconfiguredSite:
    def test_confirm_without_a_jwt_plugin_is_a_501(self, portal, request_, monkeypatch):
        """Same answer as the OAuth callback gives: the site is misconfigured,
        not the request."""
        from .conftest import body
        from .test_magiclink import EMAIL_PROVIDER_RECORD
        from pas.plugins.identity.core.controlpanel import get_providers
        from pas.plugins.identity.core.controlpanel import ProviderConfig
        from pas.plugins.identity.core.controlpanel import set_providers

        set_providers([
            *get_providers(),
            ProviderConfig.deserialize(EMAIL_PROVIDER_RECORD),
        ])
        monkeypatch.setattr(service, "_jwt_token", lambda userid: None)
        token, _ = magiclink.issue("erico@plone.org")

        body(request_, {"token": token})
        result = service.MagicLinkConfirm(portal, request_).reply()

        assert request_.response.getStatus() == 501
        assert "JWT authentication plugin" in result["error"]["message"]

    def test_jwt_helper_returns_none_without_the_plugin(self, portal, monkeypatch):
        """The helper itself, so the 501 above is not the only thing pinning
        this behaviour."""
        monkeypatch.setattr(
            service, "JWT_PLUGIN_META_TYPE", "No Such Plugin", raising=False
        )
        from pas.plugins.identity.core.services import callback

        monkeypatch.setattr(callback, "JWT_PLUGIN_META_TYPE", "No Such Plugin")

        plugin = api.portal.get_tool("acl_users")["identity"]
        userid, _ = plugin.authenticateCredentials({
            "extractor": "pas.plugins.identity",
            "provider": EMAIL_PROVIDER,
            "subject": "erico@plone.org",
            "claims": {"email": "erico@plone.org", "email_verified": True},
        })

        assert service._jwt_token(userid) is None
