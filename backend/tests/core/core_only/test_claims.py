"""What a provider sends, and what a core-only site does with it.

On a site with Profiles, every claim passes through a schema field before it
is stored: it is shaped for the field, validated, and skipped when it does
not fit. A core-only site has no schema. The claims land in
``mutable_properties``, which stores whatever it is handed, so the shaping
has to happen on the way in or not at all.

Claims are a ``TypedDict``, which nothing enforces at runtime. A driver
normalizes the provider's payload, but ``raw`` is that payload untouched, a
property map may point anywhere inside it, and a third-party driver may fill
the normalized keys with whatever it was sent. So these tests feed the login
the shapes a provider can actually produce, and assert the two things that
must hold whatever arrives: the person gets in, and every property holds
text.
"""

from . import CLAIMS
from . import PROVIDER
from . import sign_in
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from plone import api

import pytest


pytestmark = pytest.mark.no_profile_container

#: Values a provider can send where text is expected, and that are not text.
#: ``None`` is JSON's ``null``; the containers are JSON's arrays and objects;
#: a boolean is not a name or a place either.
NOT_TEXT = {
    "null": None,
    "true": True,
    "false": False,
    "list": ["Érico", "Andrei"],
    "empty-list": [],
    "object": {"formatted": "Érico Andrei"},
    "empty-object": {},
}

#: JSON numbers, and the text they are written as. A provider sending ``42``
#: for a field meant ``"42"``, and the Profile path writes it so.
NUMBERS = {"integer": (42, "42"), "float": (4.2, "4.2"), "zero": (0, "0")}

#: Text a provider can send that is still text, but is not a tidy line.
AWKWARD_TEXT = {
    "empty": "",
    "blank": "   ",
    "padded": "  Érico Andrei  ",
    "newline": "Érico\nAndrei",
    "control": "Érico\x00Andrei",
    "emoji": "Érico 🦄 Andrei",
    "rtl": "إريكو",
    "long": "É" * 10_000,
}


def claims_with(**overrides) -> dict:
    """Return :data:`CLAIMS` with some keys replaced.

    :param overrides: Keys to replace. A value of ``...`` removes the key.
    :returns: A fresh claims mapping.
    """
    claims = {**CLAIMS, "raw": dict(CLAIMS["raw"])}
    for key, value in overrides.items():
        if value is ...:
            claims.pop(key, None)
        else:
            claims[key] = value
    return claims


def property_of(userid: str, name: str):
    """Return one property of a member, as the rest of Plone reads it.

    :param userid: The userid.
    :param name: The property name.
    :returns: Its value.
    """
    return api.user.get(userid=userid).getProperty(name)


def use_map(propertymap: dict[str, str]) -> None:
    """Configure the provider with a property map.

    :param propertymap: Claim path to user field.
    """
    set_providers([
        ProviderConfig(
            provider_id=PROVIDER,
            driver_id="oidc-generic",
            title="Dex",
            propertymap=propertymap,
        )
    ])


class TestTheNormalizedClaims:
    """``fullname`` and ``email`` seed a new account, whatever they hold."""

    @pytest.fixture(autouse=True)
    def _setup(self, identity_plugin) -> None:
        self.plugin = identity_plugin

    @pytest.mark.parametrize("key", ["fullname", "email"])
    @pytest.mark.parametrize("value", NOT_TEXT.values(), ids=NOT_TEXT.keys())
    def test_a_value_that_is_not_text_is_not_stored(self, key, value):
        """A provider that sent a list for a name has not sent a name."""
        userid = sign_in(self.plugin, claims=claims_with(**{key: value}))

        assert property_of(userid, key) == ""

    @pytest.mark.parametrize("key", ["fullname", "email"])
    @pytest.mark.parametrize("value,expected", NUMBERS.values(), ids=NUMBERS.keys())
    def test_a_number_is_written_as_text(self, key, value, expected):
        userid = sign_in(self.plugin, claims=claims_with(**{key: value}))

        assert property_of(userid, key) == expected

    @pytest.mark.parametrize("key", ["fullname", "email"])
    def test_a_missing_claim_seeds_nothing(self, key):
        userid = sign_in(self.plugin, claims=claims_with(**{key: ...}))

        assert property_of(userid, key) == ""

    @pytest.mark.parametrize("value", AWKWARD_TEXT.values(), ids=AWKWARD_TEXT.keys())
    def test_awkward_text_is_still_a_name(self, value):
        """Not this package's to tidy: a name is what the provider says."""
        userid = sign_in(self.plugin, claims=claims_with(fullname=value))

        assert isinstance(property_of(userid, "fullname"), str)

    def test_no_claims_at_all(self):
        """An extractor that found nothing to normalize still names a
        subject, and the subject is what the account is minted for."""
        userid = sign_in(self.plugin, claims={})

        assert api.user.get(userid=userid) is not None

    def test_a_returning_login_does_not_reseed(self):
        """Seeding is for a new account. A name changed in Plone stays."""
        userid = sign_in(self.plugin)
        api.user.get(userid=userid).setMemberProperties({"fullname": "Érico"})

        sign_in(self.plugin, claims=claims_with(fullname="Somebody Else"))

        assert property_of(userid, "fullname") == "Érico"


class TestTheRawPayload:
    """``raw`` is the provider's document, and any shape of it is possible."""

    @pytest.fixture(autouse=True)
    def _setup(self, identity_plugin) -> None:
        self.plugin = identity_plugin
        use_map({"location": "location"})

    @pytest.mark.parametrize(
        "raw",
        [None, "a string", ["a", "list"], 42, {}],
        ids=["null", "string", "list", "integer", "empty"],
    )
    def test_a_raw_that_is_not_an_object(self, raw):
        userid = sign_in(self.plugin, claims=claims_with(raw=raw))

        assert property_of(userid, "location") == ""

    def test_no_raw_at_all(self):
        userid = sign_in(self.plugin, claims=claims_with(raw=...))

        assert property_of(userid, "location") == ""


class TestMappedValues:
    """What a property map resolves to is written only when it is text."""

    @pytest.fixture(autouse=True)
    def _setup(self, identity_plugin) -> None:
        self.plugin = identity_plugin
        use_map({"location": "location", "address.formatted": "description"})

    @pytest.mark.parametrize("value", NOT_TEXT.values(), ids=NOT_TEXT.keys())
    def test_a_value_that_is_not_text_is_not_stored(self, value):
        """An OIDC ``address`` is an object; writing its ``repr`` into
        somebody's location is worse than writing nothing."""
        claims = claims_with(raw={"location": value})

        userid = sign_in(self.plugin, claims=claims)

        assert property_of(userid, "location") == ""

    @pytest.mark.parametrize("value", NOT_TEXT.values(), ids=NOT_TEXT.keys())
    def test_a_rejected_value_does_not_cost_the_rest(self, value):
        """One bad row must not stop the next one being written."""
        claims = claims_with(
            raw={"location": value, "address": {"formatted": "Brasília, DF"}}
        )

        userid = sign_in(self.plugin, claims=claims)

        assert property_of(userid, "description") == "Brasília, DF"

    def test_a_nested_path_reaches_into_the_payload(self):
        claims = claims_with(raw={"address": {"formatted": "Brasília, DF"}})

        userid = sign_in(self.plugin, claims=claims)

        assert property_of(userid, "description") == "Brasília, DF"

    def test_a_path_through_something_that_is_not_an_object(self):
        """``address`` is a string here, so ``address.formatted`` is nothing."""
        claims = claims_with(raw={"address": "Brasília, DF"})

        userid = sign_in(self.plugin, claims=claims)

        assert property_of(userid, "description") == ""

    @pytest.mark.parametrize("value,expected", NUMBERS.values(), ids=NUMBERS.keys())
    def test_a_number_is_written_as_text(self, value, expected):
        """The Profile path writes ``str(42)``; so does this one."""
        userid = sign_in(self.plugin, claims=claims_with(raw={"location": value}))

        assert property_of(userid, "location") == expected

    @pytest.mark.parametrize("value", AWKWARD_TEXT.values(), ids=AWKWARD_TEXT.keys())
    def test_awkward_text_does_not_stop_the_login(self, value):
        userid = sign_in(self.plugin, claims=claims_with(raw={"location": value}))

        assert isinstance(property_of(userid, "location"), str)

    def test_an_empty_claim_does_not_blank_a_value(self):
        """A provider that stops sending a claim has not cleared it."""
        userid = sign_in(self.plugin)
        assert property_of(userid, "location") == "Brasília"

        sign_in(self.plugin, claims=claims_with(raw={"location": ""}))

        assert property_of(userid, "location") == "Brasília"

    def test_a_blank_property_is_filled_on_a_later_login(self):
        """A claim the provider started sending later still arrives."""
        userid = sign_in(self.plugin, claims=claims_with(raw={}))

        sign_in(self.plugin)

        assert property_of(userid, "location") == "Brasília"


class TestMapsThatNameTheWrongThing:
    """A stored map is not revalidated when the site changes under it.

    A map saved while ``contenttypes`` was installed may name a field of a
    behavior the site no longer has, and a map imported from a profile or
    written straight to the registry may name anything. ``set_providers``
    refuses both, so the provider is handed to the plugin directly: the login
    reads whatever the registry holds, not what the panel would accept today.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, identity_plugin, monkeypatch) -> None:
        self.plugin = identity_plugin
        self.monkeypatch = monkeypatch

    def stored_map(self, propertymap: dict[str, str]) -> None:
        """Make the provider's stored map ``propertymap``, unvalidated.

        :param propertymap: Claim path to user field.
        """
        from pas.plugins.identity.core import controlpanel

        provider = ProviderConfig(
            provider_id=PROVIDER,
            driver_id="oidc-generic",
            title="Dex",
            propertymap=propertymap,
        )
        self.monkeypatch.setattr(
            controlpanel,
            "get_provider",
            lambda provider_id: provider if provider_id == PROVIDER else None,
        )

    def test_a_field_members_do_not_have(self):
        """``phone`` came from a Profile behavior; a member has no such
        property, and the login must not invent one."""
        self.stored_map({"phone_number": "phone", "location": "location"})
        claims = claims_with(
            raw={"phone_number": "+55 61 0000-0000", "location": "Brasília"}
        )

        userid = sign_in(self.plugin, claims=claims)

        member = api.user.get(userid=userid)
        assert member.getProperty("phone", None) is None
        assert member.getProperty("location") == "Brasília"

    @pytest.mark.parametrize(
        "field", ["email", "login", "portrait", "id", "userid", "group_ids"]
    )
    def test_a_field_no_map_may_write(self, field):
        """The guard the panel applies holds at login too: a provider must
        not reach an account's address, login or portrait through a map."""
        self.stored_map({"evil": field})
        claims = claims_with(raw={"evil": "attacker@example.com"})

        userid = sign_in(self.plugin, claims=claims)

        assert property_of(userid, "email") == "erico@plone.org"

    def test_a_property_of_another_type(self):
        """A site may declare a member property that is not text. A map
        aimed at it is refused by the property sheet; the login goes on, and
        so do the rows after it."""
        memberdata = api.portal.get_tool("portal_memberdata")
        memberdata.manage_addProperty("age", 0, "int")
        self.stored_map({"age": "age", "location": "location"})
        claims = claims_with(raw={"age": "forty", "location": "Brasília"})

        userid = sign_in(self.plugin, claims=claims)

        assert property_of(userid, "age") == 0
        assert property_of(userid, "location") == "Brasília"

    def test_an_empty_target(self):
        self.stored_map({"location": ""})

        userid = sign_in(self.plugin)

        assert property_of(userid, "location") == ""

    def test_an_empty_path(self):
        self.stored_map({"": "location"})

        userid = sign_in(self.plugin)

        assert property_of(userid, "location") == ""
