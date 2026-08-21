"""Unit tests for driver claim normalization (§4.4).

Table-driven against the recorded payloads in this package's ``__init__``;
nothing here touches the network or the ZODB.
"""

from . import DEX_USERINFO
from . import GITHUB_USER
from . import GITHUB_USER_NO_NAME
from . import GOOGLE_USERINFO
from . import UNVERIFIED_OIDC
from pas.plugins.identity.core.drivers import all_drivers
from pas.plugins.identity.core.drivers import BaseDriver
from pas.plugins.identity.core.drivers import EmailDriver
from pas.plugins.identity.core.drivers import GenericOIDCDriver
from pas.plugins.identity.core.drivers import get_driver
from pas.plugins.identity.core.drivers import GitHubDriver
from pas.plugins.identity.core.drivers import GoogleDriver
from pas.plugins.identity.core.interfaces import ClaimsError
from pas.plugins.identity.core.interfaces import IDriver
from zope.interface.verify import verifyObject

import pytest


#: Every driver shipped in v1.
ALL_DRIVERS = (GitHubDriver, GoogleDriver, GenericOIDCDriver, EmailDriver)

#: Keys the normalized schema always carries.
CLAIM_KEYS = {"fullname", "email", "email_verified", "picture_url", "username", "raw"}


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
            assert {"type", "title", "required", "secret"} <= set(descriptor), name

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
        """An unusable payload is a hard error, never a made-up subject (I1)."""
        with pytest.raises(ClaimsError):
            factory().subject({"unrelated": "value"})


class TestDriverRegistry:
    """D9 -- drivers are named utilities, and the name is the driver id."""

    def test_every_shipped_driver_is_registered(self, portal):
        """ZCML and :data:`ALL_DRIVERS` agree on what v1 ships."""
        assert set(all_drivers()) == {factory().driver_id for factory in ALL_DRIVERS}

    def test_lookup_agrees_with_enumeration(self, portal):
        """The two ways in reach the same utility."""
        for driver_id, driver in all_drivers().items():
            assert get_driver(driver_id) is driver

    def test_unknown_driver_is_none_not_an_error(self, portal):
        """An orphaned provider record must be inspectable, not fatal."""
        assert get_driver("no-such-driver") is None


class TestSecretFlagging:
    """I4 -- every surface must be able to mask secrets."""

    @pytest.mark.parametrize("factory", (GitHubDriver, GoogleDriver, GenericOIDCDriver))
    def test_client_secret_is_flagged(self, factory: type[BaseDriver]):
        """OAuth drivers mark ``client_secret`` secret."""
        assert factory().config_schema()["client_secret"]["secret"] is True

    @pytest.mark.parametrize("factory", (GitHubDriver, GoogleDriver, GenericOIDCDriver))
    def test_client_id_is_not_secret(self, factory: type[BaseDriver]):
        """The client id is public by design and must not be masked."""
        assert factory().config_schema()["client_id"]["secret"] is False

    def test_email_driver_has_no_secrets(self):
        """Magic link holds no provider credentials at all."""
        schema = EmailDriver().config_schema()

        assert not any(f["secret"] for f in schema.values())
        assert "client_secret" not in schema


class TestGitHubDriver:
    @pytest.fixture()
    def driver(self) -> GitHubDriver:
        """Return the GitHub driver."""
        return GitHubDriver()

    def test_subject_is_numeric_id_as_string(self, driver: GitHubDriver):
        """The numeric id is stringified so the store key is stable."""
        assert driver.subject(GITHUB_USER) == "1234567"

    def test_subject_falls_back_to_node_id(self, driver: GitHubDriver):
        """A payload without ``id`` still yields a stable subject."""
        assert driver.subject({"node_id": "MDQ6VXNlcjE="}) == "MDQ6VXNlcjE="

    @pytest.mark.parametrize(
        "key,expected",
        [
            ("fullname", "Érico Andrei"),
            ("email", "erico@plone.org"),
            ("email_verified", True),
            ("username", "ericof"),
            (
                "picture_url",
                "https://avatars.githubusercontent.com/u/1234567?v=4",
            ),
        ],
    )
    def test_claims(self, driver: GitHubDriver, key: str, expected):
        """Each documented claim is read from the right GitHub field."""
        assert driver.normalize_claims(GITHUB_USER)[key] == expected

    def test_email_is_lowercased(self, driver: GitHubDriver):
        """GitHub echoes the address as typed; the claim is canonical."""
        assert GITHUB_USER["email"] == "Erico@Plone.ORG"
        assert driver.normalize_claims(GITHUB_USER)["email"] == "erico@plone.org"

    def test_fullname_falls_back_to_login(self, driver: GitHubDriver):
        """An account with no display name is not created nameless."""
        claims = driver.normalize_claims(GITHUB_USER_NO_NAME)

        assert claims["fullname"] == "anon-dev"

    def test_allowed_groups_field_present(self, driver: GitHubDriver):
        """C4 parity: the deny-at-door gate is configurable per provider."""
        assert "allowed_groups" in driver.config_schema()


class TestGoogleDriver:
    @pytest.fixture()
    def driver(self) -> GoogleDriver:
        """Return the Google driver."""
        return GoogleDriver()

    def test_subject_is_sub(self, driver: GoogleDriver):
        """OIDC subject, never the mutable email (I1)."""
        assert driver.subject(GOOGLE_USERINFO) == "104928374650192837465"

    @pytest.mark.parametrize(
        "key,expected",
        [
            ("fullname", "Érico Andrei"),
            ("email", "erico@plone.org"),
            ("email_verified", True),
            ("picture_url", "https://lh3.googleusercontent.com/a/ACg8ocK"),
        ],
    )
    def test_claims(self, driver: GoogleDriver, key: str, expected):
        """Each documented claim is read from the right OIDC field."""
        assert driver.normalize_claims(GOOGLE_USERINFO)[key] == expected

    def test_hosted_domain_field_present(self, driver: GoogleDriver):
        """Workspace restriction is configurable."""
        assert "hosted_domain" in driver.config_schema()


class TestGenericOIDCDriver:
    @pytest.fixture()
    def driver(self) -> GenericOIDCDriver:
        """Return the generic OIDC driver."""
        return GenericOIDCDriver()

    def test_subject_is_sub(self, driver: GenericOIDCDriver):
        """Dex's opaque subject is used verbatim."""
        assert driver.subject(DEX_USERINFO) == "CgVlcmljbxIFbG9jYWw"

    def test_username_from_preferred_username(self, driver: GenericOIDCDriver):
        """OIDC spells the login ``preferred_username``."""
        assert driver.normalize_claims(DEX_USERINFO)["username"] == "ericof"

    def test_issuer_is_required(self, driver: GenericOIDCDriver):
        """Discovery needs an issuer; the control panel must enforce it."""
        assert driver.config_schema()["issuer"]["required"] is True


class TestEmailVerifiedIsStrict:
    """S2 -- only a literal ``True`` counts as verified."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            (True, True),
            (False, False),
            (None, False),
            ("true", False),
            ("True", False),
            (1, False),
            ("", False),
        ],
    )
    def test_email_verified(self, value, expected: bool):
        """Truthy-but-not-True values are treated as unverified."""
        payload = {"sub": "s", "email": "e@example.com", "email_verified": value}

        assert (
            GenericOIDCDriver().normalize_claims(payload)["email_verified"] is expected
        )

    def test_missing_key_is_unverified(self):
        """A provider that says nothing has asserted nothing."""
        payload = {"sub": "s", "email": "e@example.com"}

        assert GenericOIDCDriver().normalize_claims(payload)["email_verified"] is False

    def test_forged_unverified_payload(self):
        """The S2 attack shape normalizes to unverified."""
        claims = GenericOIDCDriver().normalize_claims(UNVERIFIED_OIDC)

        assert claims["email"] == "erico@plone.org"
        assert claims["email_verified"] is False


class TestEmailDriver:
    @pytest.fixture()
    def driver(self) -> EmailDriver:
        """Return the email driver."""
        return EmailDriver()

    def test_subject_is_lowercased_address(self, driver: EmailDriver):
        """The address is the subject; the store's case policy agrees."""
        assert driver.subject({"email": "Erico@Plone.ORG"}) == "erico@plone.org"

    def test_confirmed_address_is_verified(self, driver: EmailDriver):
        """Delivery is the proof, so the claim is unconditionally true."""
        claims = driver.normalize_claims({"email": "erico@plone.org"})

        assert claims["email_verified"] is True

    def test_verified_even_if_payload_says_otherwise(self, driver: EmailDriver):
        """The payload cannot downgrade what delivery already proved."""
        claims = driver.normalize_claims({
            "email": "erico@plone.org",
            "email_verified": False,
        })

        assert claims["email_verified"] is True

    def test_ttl_default_matches_s5(self, driver: EmailDriver):
        """S5 caps the magic-link lifetime at 15 minutes."""
        assert driver.config_schema()["token_ttl"]["default"] == 900


class TestTextHelpers:
    """Edge cases in the shared field-reading helper."""

    @pytest.mark.parametrize(
        "payload,expected",
        [
            ({"name": "  Érico  "}, "Érico"),
            ({"name": "   "}, ""),
            ({"name": None}, ""),
            ({"name": 42}, ""),
            ({}, ""),
        ],
    )
    def test_fullname_reading(self, payload: dict, expected: str):
        """Whitespace is trimmed; non-strings never leak into claims."""
        payload = {"sub": "s", **payload}

        assert GenericOIDCDriver().normalize_claims(payload)["fullname"] == expected

    def test_subject_rejects_boolean(self):
        """``True`` is an int in Python; it must not become subject ``"1"``."""
        with pytest.raises(ClaimsError):
            GitHubDriver().subject({"id": True})

    def test_subject_rejects_blank_string(self):
        """A whitespace-only subject is no subject."""
        with pytest.raises(ClaimsError):
            GoogleDriver().subject({"sub": "   "})
