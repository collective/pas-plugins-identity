"""The driver for a Keycloak realm."""

from . import KEYCLOAK_USERINFO
from pas.plugins.identity.core.controlpanel import driver_defaults
from pas.plugins.identity.core.drivers import get_driver
from pas.plugins.identity.core.drivers.keycloak import KeycloakDriver
from pas.plugins.identity.core.drivers.oidc import GenericOIDCDriver
from pas.plugins.identity.core.drivers.settings import IKeycloakSettings
from pas.plugins.identity.core.drivers.settings import IOIDCSettings
from pas.plugins.identity.core.utils.propertymap import apply_property_map

import pytest


class TestKeycloakDriver:
    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.driver = KeycloakDriver()
        self.claims = self.driver.normalize_claims(KEYCLOAK_USERINFO)

    def test_is_registered(self):
        """It is a utility like every other driver, or nothing offers it."""
        assert isinstance(get_driver("keycloak"), KeycloakDriver)

    def test_is_a_generic_oidc_provider(self):
        """A realm gets no special path through the flow: what this driver
        adds is configuration, not protocol."""
        assert isinstance(self.driver, GenericOIDCDriver)

    def test_its_settings_are_the_oidc_ones(self):
        """Nothing is added to the form. The schema exists to say what the
        issuer of a Keycloak realm looks like."""
        assert IKeycloakSettings.extends(IOIDCSettings)
        assert set(IKeycloakSettings.names(all=True)) == set(
            IOIDCSettings.names(all=True)
        )

    def test_the_issuer_is_described_as_the_realm(self):
        """The server root is what people reach for, and it serves no
        discovery document. Asked of the driver's own schema, so a driver left
        on the generic one fails here too."""
        issuer = self.driver.settings_schema["issuer"]

        assert issuer.required
        assert "/realms/" in issuer.description
        assert issuer.description != IOIDCSettings["issuer"].description

    def test_subject_is_sub(self):
        """The realm's UUID, which a username change leaves alone."""
        assert (
            self.driver.subject(KEYCLOAK_USERINFO)
            == "d5b148c6-e6a9-4479-8ea0-e3b28ca71ab9"
        )

    def test_userid_defaults_to_the_realms_username(self):
        """``preferred_username``, which a realm releases under the
        ``profile`` scope, rather than a random id nobody recognises."""
        assert self.driver.default_userid_source == "username"
        assert self.claims["username"] == "elena"

    def test_trusts_email_verification_by_default(self):
        """A realm is usually the organization's own, and it sends a real
        boolean, so no text flag is needed for the trust to mean anything."""
        assert self.driver.default_trust_email_verification is True
        assert self.claims["email_verified"] is True

    def test_the_generic_driver_still_trusts_nobody(self):
        """The premise of the test above: this is a decision about a realm,
        not a change to what an arbitrary provider gets."""
        assert GenericOIDCDriver().default_trust_email_verification is False
        assert GenericOIDCDriver().default_userid_source == "uuid"

    def test_the_group_claim_is_the_generic_one(self):
        """A realm's Group Membership mapper names the claim ``groups``."""
        assert self.driver.default_group_claim == "groups"

    def test_the_seeded_mapping_resolves_against_a_real_payload(self):
        """A default realm sends a name and nothing else a Profile can hold,
        so one row, and that row resolves."""
        assert apply_property_map(self.driver.default_propertymap, self.claims) == {
            "fullname": "Elena Example",
        }

    def test_a_new_provider_starts_with_these_defaults(self):
        """What the add form is seeded with, which is where every default
        above actually reaches an operator."""
        assert driver_defaults(self.driver) == {
            "userid_source": "username",
            "trust_email_verification": True,
            "scope": ("openid", "email", "profile"),
            "group_claim": "groups",
        }
