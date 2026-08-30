"""The generic OpenID Connect driver."""

from . import DEX_USERINFO
from pas.plugins.identity.core.drivers.oidc import GenericOIDCDriver

import pytest


class TestGenericOIDCDriver:
    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.driver = GenericOIDCDriver()

    def test_subject_is_sub(self):
        """Dex's opaque subject is used verbatim."""
        assert self.driver.subject(DEX_USERINFO) == "CgVlcmljbxIFbG9jYWw"

    def test_username_from_preferred_username(self):
        """OIDC spells the login ``preferred_username``."""
        assert self.driver.normalize_claims(DEX_USERINFO)["username"] == "ericof"

    def test_issuer_is_required(self):
        """Discovery needs an issuer; the control panel must enforce it."""
        assert self.driver.settings_schema["issuer"].required is True
