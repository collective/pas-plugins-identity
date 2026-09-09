"""The extension contract: a downstream package adding claims to this server.

The three shipped scopes have their own tests, in ``test_claims.py``. This
module is about the *mechanism* -- that a scope is a registered adapter and
not a row this package holds -- and it asserts the two things a claim table
could never have offered: that a package can add a scope without editing this
one, and that a package can extend a scope this one ships.

The reach tests are the ones worth reading. A new scope has to arrive in four
places at once, and they are computed by four different callers: the discovery
document a client reads, the vocabulary the operator registers a client from,
the consent screen the person agrees on, and the token itself. A scope that
reached only the token would be released without ever being offered, asked for
or consented to.
"""

from . import ISSUER
from . import PROFILE_ID
from . import USERID
from pas.plugins.identity.server.claims import claims_for
from pas.plugins.identity.server.claims import released
from pas.plugins.identity.server.claims import scope_claims
from pas.plugins.identity.server.claims import scopes
from pas.plugins.identity.server.discovery import claims_supported
from pas.plugins.identity.server.discovery import scopes_supported
from pas.plugins.identity.server.grants.tokens import mint_id_token
from pas.plugins.identity.server.interfaces import IScopeSerializer
from pas.plugins.identity.server.serializers import serializer_for
from pas.plugins.identity.server.serializers.profile import ProfileScope
from pas.plugins.identity.server.vocabularies.scopes import SCOPES_VOCABULARY
from plone import api
from plone.base.interfaces import IPloneSiteRoot
from zope.component import getGlobalSiteManager
from zope.component import getUtility
from zope.interface import alsoProvides
from zope.interface import Interface
from zope.interface import noLongerProvides
from zope.interface.verify import verifyObject
from zope.schema.interfaces import IVocabularyFactory

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


def decode_id_token(token: str) -> dict:
    """Decode an ``id_token`` the way a relying party would.

    :param token: The encoded token.
    :returns: The validated claims.
    """
    from joserfc import jwt
    from pas.plugins.identity.server.utils.keys import ALGORITHM
    from pas.plugins.identity.server.utils.keys import key_set

    claims = jwt.decode(token, key_set(), algorithms=[ALGORITHM]).claims
    jwt.JWTClaimsRegistry().validate(claims)
    return dict(claims)


@pytest.fixture
def user(portal):
    """Somebody for a serializer to be asked about."""
    with api.env.adopt_roles(["Manager"]):
        return api.user.create(
            email="alice@example.org",
            username=USERID,
            password="irrelevant-to-claims",
            properties={"fullname": "Alice Liddell"},
        )


class TestTheShippedSerializers:
    """The three this package registers."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    @pytest.mark.parametrize("scope", ["profile", "email", "address"])
    def test_each_scope_has_one(self, scope):
        assert serializer_for(scope) is not None

    @pytest.mark.parametrize("scope", ["profile", "email", "address"])
    def test_each_provides_the_interface(self, scope):
        """Registered against the interface is not the same as satisfying it,
        and a missing ``claims`` would only show up as a scope the consent
        screen renders empty."""
        assert verifyObject(IScopeSerializer, serializer_for(scope))

    def test_openid_has_none(self):
        """It releases nothing of its own, so there is nothing to register.
        ``sub`` is not scope-gated."""
        assert serializer_for("openid") is None

    def test_an_unregistered_scope_has_none(self):
        assert serializer_for("telepathy") is None


class TestANewScope:
    """What a downstream package gets by registering one adapter."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, issuer, user, register_scope) -> None:
        self.portal = portal
        self.register = register_scope
        self.register(
            "phone",
            claims=("phone_number",),
            values={"phone_number": "+44 7700 900000"},
        )

    def test_it_is_advertised_in_the_discovery_document(self):
        assert "phone" in scopes_supported()

    def test_its_claims_are_advertised_too(self):
        """A client reads ``claims_supported`` to know what it might have to
        understand; a claim released but never advertised is a surprise."""
        assert "phone_number" in claims_supported()

    def test_it_is_offered_when_registering_a_client(self):
        """The operator cannot register a client for a scope the form does
        not list, which would leave the add-on's own scope unusable."""
        factory = getUtility(IVocabularyFactory, name=SCOPES_VOCABULARY)

        assert "phone" in [term.value for term in factory(self.portal)]

    def test_the_consent_screen_can_enumerate_it(self):
        """The claim names the person is agreeing to release. A scope whose
        claims cannot be listed asks somebody to consent to an unknown."""
        assert scope_claims("phone") == ("phone_number",)

    def test_it_releases_its_claim(self):
        assert claims_for(USERID, "openid phone")["phone_number"] == "+44 7700 900000"

    def test_it_reaches_an_issued_id_token(self):
        """The end of the line. Everything above is a list the claim has to
        appear on; this is the token a relying party actually reads."""
        token = mint_id_token("app", USERID, scope="openid phone")

        assert decode_id_token(token)["phone_number"] == "+44 7700 900000"

    def test_it_is_not_released_without_its_scope(self):
        assert "phone_number" not in claims_for(USERID, "openid profile")

    def test_the_shipped_scopes_still_work(self):
        """A registration that displaced the three this package ships would
        pass every test above and break every existing client."""
        assert claims_for(USERID, "openid profile")["name"] == "Alice Liddell"


class TestOverridingAShippedScope:
    """Subclass, call ``super()``, register: the ``plone.restapi`` shape."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, user, register_scope) -> None:
        self.portal = portal

        class ProfileWithBadges(ProfileScope):
            """A policy package adding one claim to a scope it did not write."""

            claims = (*ProfileScope.claims, "badges")

            def __call__(self, user):
                claims = super().__call__(user)
                claims["badges"] = ["contributor"]
                return claims

        self.override = register_scope("profile", factory=ProfileWithBadges)

    def test_the_added_claim_is_released(self):
        assert claims_for(USERID, "openid profile")["badges"] == ["contributor"]

    def test_the_inherited_claims_survive(self):
        """``super()`` composition is the whole point: an override that
        replaced the shipped claims would silently stop releasing ``name``
        to every relying party already relying on it."""
        claims = claims_for(USERID, "openid profile")

        assert claims["name"] == "Alice Liddell"
        assert claims["preferred_username"] == USERID

    def test_the_declaration_grows_with_it(self):
        assert "badges" in scope_claims("profile")
        assert "name" in scope_claims("profile")

    def test_the_added_claim_is_advertised(self):
        assert "badges" in claims_supported()

    def test_no_new_scope_appeared(self):
        """Replacing a scope's serializer changes what that scope releases,
        not which scopes exist."""
        assert scopes_supported().count("profile") == 1


class TestOverridingForABrowserLayer:
    """The route the how-to guide tells a policy package to take.

    Registering for a layer of your own is more specific than the
    ``IBrowserRequest`` this package registers for, so the lookup finds yours
    first and no ``overrides.zcml`` is needed. That is the documented
    mechanism, so it is asserted here rather than assumed: a guide describing
    a registration that does not win would be found by whoever followed it.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, user) -> None:
        self.portal = portal
        self.request = portal.REQUEST

        class IPolicyLayer(Interface):
            """A downstream package's browser layer."""

        class ProfileForThisSite(ProfileScope):
            claims = (*ProfileScope.claims, "badges")

            def __call__(self, user):
                claims = super().__call__(user)
                claims["badges"] = ["contributor"]
                return claims

        gsm = getGlobalSiteManager()
        gsm.registerAdapter(
            ProfileForThisSite,
            (IPloneSiteRoot, IPolicyLayer),
            IScopeSerializer,
            name="profile",
        )
        self.layer_interface = IPolicyLayer
        yield
        noLongerProvides(self.request, IPolicyLayer)
        gsm.unregisterAdapter(
            ProfileForThisSite,
            (IPloneSiteRoot, IPolicyLayer),
            IScopeSerializer,
            name="profile",
        )

    def test_the_shipped_one_answers_without_the_layer(self):
        """The registration exists throughout; only the request decides."""
        assert "badges" not in claims_for(USERID, "openid profile")

    def test_the_layer_registration_wins_when_the_request_has_it(self):
        alsoProvides(self.request, self.layer_interface)

        assert claims_for(USERID, "openid profile")["badges"] == ["contributor"]

    def test_the_inherited_claims_come_with_it(self):
        alsoProvides(self.request, self.layer_interface)

        assert claims_for(USERID, "openid profile")["name"] == "Alice Liddell"

    def test_the_declaration_follows_the_layer_too(self):
        """The consent screen and the discovery document read the declaration
        through the same lookup, so they must see the override as well."""
        alsoProvides(self.request, self.layer_interface)

        assert "badges" in scope_claims("profile")


class TestReservedClaims:
    """What a serializer may not say, however it is registered."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, issuer, user, register_scope) -> None:
        self.portal = portal
        register_scope(
            "impostor",
            claims=("sub",),
            values={"sub": "somebody-else", "iss": "https://evil.example.org"},
        )

    def test_sub_is_this_servers_own(self):
        """The join every relying party stores. A serializer able to move it
        would re-identify a user at every RP at once, with nothing to migrate
        back from."""
        assert claims_for(USERID, "openid impostor")["sub"] == USERID

    def test_a_reserved_claim_is_dropped_rather_than_honoured(self):
        assert claims_for(USERID, "openid impostor").get("iss") != (
            "https://evil.example.org"
        )

    def test_the_token_still_carries_this_servers_issuer(self):
        """``mint_id_token`` sets ``iss`` after the claims either way, so this
        is belt and braces -- and the braces are what stops ``sub`` moving,
        which nothing downstream of here would catch."""
        claims = decode_id_token(mint_id_token("app", USERID, scope="openid impostor"))

        assert claims["iss"] == ISSUER
        assert claims["sub"] == USERID


class TestTheAbsenceRule:
    """A claim with no value is absent, and ``False`` is a value."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, user, register_scope) -> None:
        self.portal = portal
        register_scope(
            "sparse",
            claims=("blank", "nothing", "empty_list", "flag", "zero"),
            values={
                "blank": "",
                "nothing": None,
                "empty_list": [],
                "flag": False,
                "zero": 0,
            },
        )
        self.claims = claims_for(USERID, "openid sparse")

    @pytest.mark.parametrize("claim", ["blank", "nothing", "empty_list"])
    def test_a_value_this_server_does_not_have_is_omitted(self, claim):
        """Rather than sent blank, so a relying party can tell "we do not
        know" from "it is empty"."""
        assert claim not in self.claims

    def test_false_is_released(self):
        """The rule is absence, not falsehood. ``email_verified`` is the
        claim that depends on it: dropped, "this site checked and the address
        is unverified" would arrive as "this site said nothing"."""
        assert self.claims["flag"] is False

    def test_zero_is_released(self):
        assert self.claims["zero"] == 0

    def test_every_serializer_gets_the_rule_for_free(self):
        """It is applied by ``claims_for`` rather than by each serializer, so
        a downstream author cannot forget it."""
        assert set(self.claims) == {"sub", "flag", "zero"}


class TestAnUnnamedRegistration:
    """A serializer registered with no name is a mistake, not a scope."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, user, register_scope) -> None:
        self.portal = portal
        register_scope("", claims=("leaked",), values={"leaked": "not released"})

    def test_it_is_not_a_scope(self):
        """No client can ask for a scope called ``""``, so honouring it would
        release a claim through a door nobody can knock on."""
        assert "" not in scopes()

    def test_its_claims_are_not_advertised(self):
        assert "leaked" not in claims_supported()

    def test_it_releases_nothing(self):
        assert "leaked" not in claims_for(USERID, "openid profile email address")


class TestReleasedAcrossScopes:
    """``released`` answers for a whole scope string."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, register_scope) -> None:
        self.portal = portal
        register_scope("phone", claims=("phone_number",))

    def test_a_registered_scope_contributes(self):
        assert "phone_number" in released("openid phone")

    def test_scopes_combine(self):
        names = released("openid profile phone")

        assert "name" in names
        assert "phone_number" in names

    def test_a_repeated_scope_does_not_repeat_its_claims(self):
        assert released("phone phone") == released("phone")
