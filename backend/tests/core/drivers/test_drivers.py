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
from pas.plugins.identity.core.drivers.settings import IDriverSettings
from pas.plugins.identity.core.interfaces import ClaimsError
from pas.plugins.identity.core.interfaces import IDriver
from plone.app.users.browser.schemaeditor import getFromBaseSchema
from plone.app.users.schema import IUserDataSchema
from zope.i18nmessageid import Message
from zope.interface.verify import verifyObject
from zope.schema import getFieldsInOrder
from zope.schema.interfaces import IPassword

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
    def test_settings_schema_is_an_interface(self, factory: type[BaseDriver]):
        """Not a dict this package invented.

        The whole point of the change these tests were rewritten for: a
        schema `plone.restapi` can serialize, `plone.autoform` can order, a
        z3c.form can render, and the translation machinery can reach.
        """
        schema = factory().settings_schema

        assert issubclass(schema, IDriverSettings)

    @pytest.mark.parametrize("factory", ALL_DRIVERS)
    def test_every_field_is_translatable(self, factory: type[BaseDriver]):
        """A title that is a plain `str` never reaches a `.po` file, and the
        field would be English on every site in the world."""
        for name, field in getFieldsInOrder(factory().settings_schema):
            assert isinstance(field.title, Message), name

    @pytest.mark.parametrize("factory", ALL_DRIVERS)
    def test_field_order_is_the_declaration_order(self, factory: type[BaseDriver]):
        """There is no `order` key to keep unique any more -- a schema has an
        order, so nothing can claim the same position as anything else."""
        names = [name for name, _field in getFieldsInOrder(factory().settings_schema)]

        assert len(names) == len(set(names))
        assert names

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
    def test_client_secret_is_a_password_field(self, factory: type[BaseDriver]):
        """Which is what marks it secret now.

        There is no `secret` flag to set and therefore none to forget: the
        field type is the declaration, and `mask` reads `IPassword`.
        """
        field = factory().settings_schema["client_secret"]

        assert IPassword.providedBy(field)

    @pytest.mark.parametrize("factory", OAUTH_DRIVERS)
    def test_client_id_is_not(self, factory: type[BaseDriver]):
        """The client id is public by design and must not be masked."""
        field = factory().settings_schema["client_id"]

        assert not IPassword.providedBy(field)

    def test_email_driver_has_no_secrets(self):
        """Magic link holds no provider credentials at all."""
        schema = EmailDriver().settings_schema

        assert not any(
            IPassword.providedBy(field) for _name, field in getFieldsInOrder(schema)
        )
        assert "client_secret" not in schema


class TestDefaultPropertyMap:
    """What a driver may seed into a new provider's attribute mapping."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    @pytest.mark.parametrize("factory", ALL_DRIVERS)
    def test_targets_a_field_the_site_has(self, factory: type[BaseDriver]):
        """A seeded mapping writes somewhere a fresh site actually has.

        The vocabulary the control panel offers is built from the site's live
        member schema, and a site may extend it -- but a *default* may only
        name what a stock site already carries, because that is all a fresh
        one has. ``username`` is the trap this catches: providers publish it,
        Plone has no member field for it, and a default naming it would look
        right in the form and resolve to nothing on every login.
        """
        stock = set(getFromBaseSchema(IUserDataSchema))

        for claim, field in factory().default_propertymap.items():
            assert field in stock, f"{claim} -> {field}"

    def test_username_is_not_a_member_field(self):
        """The premise of the test above, stated rather than assumed."""
        assert "username" not in set(getFromBaseSchema(IUserDataSchema))

    @pytest.mark.parametrize("factory", ALL_DRIVERS)
    def test_claims_are_paths(self, factory: type[BaseDriver]):
        """Every key is a non-empty claim path; an empty one resolves to
        ``None`` for every provider forever."""
        for claim in factory().default_propertymap:
            assert claim and claim.strip() == claim
