"""The email driver, behind magic-link login."""

from pas.plugins.identity.core.drivers.emaillink import EmailDriver

import pytest


class TestEmailDriver:
    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.driver = EmailDriver()

    def test_subject_is_lowercased_address(self):
        """The address is the subject; the store's case policy agrees."""
        assert self.driver.subject({"email": "Erico@Plone.ORG"}) == "erico@plone.org"

    def test_confirmed_address_is_verified(self):
        """Delivery is the proof, so the claim is unconditionally true."""
        claims = self.driver.normalize_claims({"email": "erico@plone.org"})

        assert claims["email_verified"] is True

    def test_verified_even_if_payload_says_otherwise(self):
        """The payload cannot downgrade what delivery already proved."""
        claims = self.driver.normalize_claims({
            "email": "erico@plone.org",
            "email_verified": False,
        })

        assert claims["email_verified"] is True

    def test_ttl_default_is_fifteen_minutes(self):
        """The default matches the ceiling the token layer enforces."""
        assert self.driver.settings_schema["token_ttl"].default == 900
