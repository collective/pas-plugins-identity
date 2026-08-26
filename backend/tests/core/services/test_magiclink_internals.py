"""The magic-link service edges the round-trip tests do not reach."""

from pas.plugins.identity.core.flows import magiclink
from pas.plugins.identity.core.services import jwt
from pas.plugins.identity.core.services.magiclink import confirm
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from plone import api

import pytest


class TestAutoLinkEdges:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, configured) -> None:
        self.portal = portal
        self.plugin = api.portal.get_tool("acl_users")["identity"]

    def test_claims_without_an_address_cannot_match(self):
        """A provider that verifies an address it did not send us matches
        nothing -- and must not raise on the way to deciding that."""
        from pas.plugins.identity.core.controlpanel import get_providers
        from pas.plugins.identity.core.controlpanel import set_providers

        providers = get_providers()
        for provider in providers:
            if provider.provider_id == "dex":
                provider.config = {**provider.config, "auto_link_by_email": True}
        set_providers(providers)

        userid, _ = self.plugin.authenticateCredentials({
            "extractor": "pas.plugins.identity",
            "provider": "dex",
            "subject": "no-address",
            "claims": {"email_verified": True},
        })

        assert self.plugin.store.userid_for("dex", "no-address") == userid
        assert self.plugin.store.identities_for(userid)[0].provider == "dex"


class TestMisconfiguredSite:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_) -> None:
        self.portal = portal
        self.request = request_
        self.plugin = api.portal.get_tool("acl_users")["identity"]

    def test_confirm_without_a_jwt_plugin_is_a_501(self, monkeypatch):
        """Same answer as the OAuth callback gives: the site is misconfigured,
        not the request."""
        from .. import body
        from . import EMAIL_PROVIDER_RECORD
        from pas.plugins.identity.core.controlpanel import get_providers
        from pas.plugins.identity.core.controlpanel import ProviderConfig
        from pas.plugins.identity.core.controlpanel import set_providers

        set_providers([
            *get_providers(),
            ProviderConfig.deserialize(EMAIL_PROVIDER_RECORD),
        ])
        monkeypatch.setattr(confirm, "mint_token", lambda userid: None)
        token, _ = magiclink.issue("erico@plone.org")

        body(self.request, {"token": token})
        result = confirm.MagicLinkConfirm(self.portal, self.request).reply()

        assert self.request.response.getStatus() == 501
        assert "JWT authentication plugin" in result["error"]["message"]

    def test_jwt_helper_returns_none_without_the_plugin(self, monkeypatch):
        """The helper itself, so the 501 above is not the only thing pinning
        this behaviour."""
        monkeypatch.setattr(jwt, "JWT_PLUGIN_META_TYPE", "No Such Plugin")

        userid, _ = self.plugin.authenticateCredentials({
            "extractor": "pas.plugins.identity",
            "provider": EMAIL_PROVIDER,
            "subject": "erico@plone.org",
            "claims": {"email": "erico@plone.org", "email_verified": True},
        })

        assert jwt.mint_token(userid) is None
