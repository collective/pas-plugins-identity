"""The driver registry, and the contract every driver has to satisfy.

Table-driven against the recorded payloads in this package's ``__init__``;
nothing here touches the network or the ZODB.
"""

from . import ALL_DRIVERS
from . import CLAIM_KEYS
from . import DEX_USERINFO
from . import GITHUB_USER
from . import GOOGLE_USERINFO
from . import OAUTH_DRIVERS
from pas.plugins.identity.core.drivers import all_drivers
from pas.plugins.identity.core.drivers import get_driver
from pas.plugins.identity.core.drivers.base import BaseDriver
from pas.plugins.identity.core.drivers.emaillink import EmailDriver
from pas.plugins.identity.core.drivers.github import GitHubDriver
from pas.plugins.identity.core.drivers.google import GoogleDriver
from pas.plugins.identity.core.drivers.oidc import GenericOIDCDriver
from pas.plugins.identity.core.interfaces import ClaimsError
from pas.plugins.identity.core.interfaces import IDriver
from zope.interface.verify import verifyObject

import pytest


class TestDriverContract:
    """Properties every driver must have, whoever wrote it."""

    @pytest.mark.parametrize("factory", ALL_DRIVERS)
    def test_provides_interface(self, factory: type[BaseDriver]):
        """The driver implements the declared interface."""
        assert verifyObject(IDriver, factory())

    @pytest.mark.parametrize("factory", ALL_DRIVERS)
    def test_has_id_and_title(self, factory: type[BaseDriver]):
        """Both are non-empty; the control panel renders them."""
        driver = factory()

        assert driver.driver_id
        assert driver.title

    @pytest.mark.parametrize("factory", ALL_DRIVERS)
    def test_config_schema_descriptors_complete(self, factory: type[BaseDriver]):
        """Every field declares the keys the Volto widget generator needs."""
        for name, descriptor in factory().config_schema().items():
            assert {"type", "title", "required", "secret", "order"} <= set(
                descriptor
            ), name

    @pytest.mark.parametrize("factory", ALL_DRIVERS)
    def test_config_schema_order_is_unambiguous(self, factory: type[BaseDriver]):
        """No two fields claim the same position.

        A schema is serialised as a JSON object with sorted keys, so ``order``
        is the only thing the form has to go on. Two fields sharing a number
        would be separated alphabetically instead -- which is the bug this
        replaced, hiding in one driver rather than all of them.
        """
        orders = [d["order"] for d in factory().config_schema().values()]

        assert len(orders) == len(set(orders))

    @pytest.mark.parametrize("factory", ALL_DRIVERS)
    def test_driver_ids_are_unique(self, factory: type[BaseDriver]):
        """Ids are utility names, so collisions would silently shadow."""
        ids = [f().driver_id for f in ALL_DRIVERS]

        assert ids.count(factory().driver_id) == 1

    @pytest.mark.parametrize(
        "factory,payload",
        [
            (GitHubDriver, GITHUB_USER),
            (GoogleDriver, GOOGLE_USERINFO),
            (GenericOIDCDriver, DEX_USERINFO),
            (EmailDriver, {"email": "erico@plone.org"}),
        ],
    )
    def test_normalize_returns_full_schema(
        self, factory: type[BaseDriver], payload: dict
    ):
        """Normalization always fills every documented key."""
        assert set(factory().normalize_claims(payload)) == CLAIM_KEYS

    @pytest.mark.parametrize(
        "factory,payload",
        [
            (GitHubDriver, GITHUB_USER),
            (GoogleDriver, GOOGLE_USERINFO),
            (GenericOIDCDriver, DEX_USERINFO),
        ],
    )
    def test_raw_is_preserved(self, factory: type[BaseDriver], payload: dict):
        """``raw`` carries the input untouched, for driver-specific consumers."""
        assert factory().normalize_claims(payload)["raw"] == payload

    @pytest.mark.parametrize("factory", ALL_DRIVERS)
    def test_subject_missing_raises(self, factory: type[BaseDriver]):
        """An unusable payload is a hard error, never a made-up subject."""
        with pytest.raises(ClaimsError):
            factory().subject({"unrelated": "value"})


class TestDriverRegistry:
    """Drivers are named utilities, and the name is the driver id."""

    @pytest.fixture(scope="class")
    def portal(self, portal_class):
        """Return the portal."""
        yield portal_class

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.drivers = all_drivers()

    def test_every_shipped_driver_is_registered(self):
        """ZCML and :data:`ALL_DRIVERS` agree on what this package ships."""
        assert set(self.drivers) == {factory().driver_id for factory in ALL_DRIVERS}

    def test_lookup_agrees_with_enumeration(self):
        """The two ways in reach the same utility."""
        for driver_id, driver in self.drivers.items():
            assert get_driver(driver_id) is driver

    def test_unknown_driver_is_none_not_an_error(self):
        """An orphaned provider record must be inspectable, not fatal."""
        assert get_driver("no-such-driver") is None


class TestSecretFlagging:
    """Every surface must be able to mask secrets."""

    @pytest.mark.parametrize("factory", OAUTH_DRIVERS)
    def test_client_secret_is_flagged(self, factory: type[BaseDriver]):
        """OAuth drivers mark ``client_secret`` secret."""
        assert factory().config_schema()["client_secret"]["secret"] is True

    @pytest.mark.parametrize("factory", OAUTH_DRIVERS)
    def test_client_id_is_not_secret(self, factory: type[BaseDriver]):
        """The client id is public by design and must not be masked."""
        assert factory().config_schema()["client_id"]["secret"] is False

    def test_email_driver_has_no_secrets(self):
        """Magic link holds no provider credentials at all."""
        schema = EmailDriver().config_schema()

        assert not any(f["secret"] for f in schema.values())
        assert "client_secret" not in schema
