"""The driver for a peer Plone site running this package as an IdP."""

from . import PLONE_IDENTITY_USERINFO
from pas.plugins.identity.core.drivers import get_driver
from pas.plugins.identity.core.drivers.identity import PloneIdentityDriver
from pas.plugins.identity.core.drivers.oidc import GenericOIDCDriver
from pas.plugins.identity.core.propertymap import apply_property_map

import pytest


class TestPloneIdentityDriver:
    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.driver = PloneIdentityDriver()

    def test_is_registered(self):
        """It is a utility like every other driver, or nothing offers it."""
        assert isinstance(get_driver("plone-identity"), PloneIdentityDriver)

    def test_is_a_generic_oidc_provider(self):
        """A peer gets no special path through the flow.

        An authorization server built on this package is a conforming OIDC
        provider; what this driver adds is configuration, not protocol.
        """
        assert isinstance(self.driver, GenericOIDCDriver)

    def test_asks_for_the_address_scope(self):
        """The peer releases an address claim behind a scope of its own, and
        the mapping below resolves to nothing without it."""
        assert "address" in self.driver.config_schema()["scope"]["default"]

    def test_userid_defaults_to_the_remote_subject(self):
        """One person keeps one id across the federation.

        A peer mints an opaque, stable userid and puts it in ``sub``, which
        is the whole reason to federate rather than have each site invent its
        own name for the same human.
        """
        assert self.driver.config_schema()["userid_source"]["default"] == "subject"

    def test_the_generic_driver_still_defaults_to_a_random_id(self):
        """The premise of the test above: this is a decision about a *peer*,
        not a change to what an arbitrary provider gets."""
        assert GenericOIDCDriver().config_schema()["userid_source"]["default"] == "uuid"

    def test_subject_is_sub(self):
        """The peer's userid, verbatim."""
        assert (
            self.driver.subject(PLONE_IDENTITY_USERINFO)
            == "8f14e45fceea167a5a36dedd4bea2543"
        )

    def test_the_seeded_mapping_resolves_against_a_real_payload(self):
        """Every claim it names is one the peer actually publishes.

        This is the test that would have caught a mapping written against a
        claim nobody sends: the defaults are only worth seeding if they
        resolve, and a mapping that quietly resolves to nothing looks
        identical to one that is right.
        """
        claims = self.driver.normalize_claims(PLONE_IDENTITY_USERINFO)

        assert apply_property_map(self.driver.default_propertymap, claims) == {
            "email": "erico@plone.org",
            "fullname": "Érico Andrei",
            "home_page": "https://plone.org",
            "location": "São Paulo, Brazil",
            "portrait": "http://id.localhost/portal_memberdata/portraits/ericof",
        }

    def test_the_address_is_read_through_the_dotted_path(self):
        """``address`` is an object; ``formatted`` is its readable line."""
        claims = self.driver.normalize_claims(PLONE_IDENTITY_USERINFO)

        assert self.driver.default_propertymap["address.formatted"] == "location"
        assert claims["raw"]["address"] == {"formatted": "São Paulo, Brazil"}

    def test_nothing_maps_to_description(self):
        """There is no biography claim to write there."""
        assert "description" not in self.driver.default_propertymap.values()
