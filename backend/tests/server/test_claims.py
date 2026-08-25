"""The claims contract.

What this server tells a relying party about a user, and on whose authority.

The tests worth reading twice are the ``email_verified`` ones. That claim is
the one a relying party will auto-link accounts on, and this package's own
core layer refuses to trust a *provider's* assertion of it. Emitting it on
that basis would export the problem rather than solve it, so it is true only
when this site verified the address itself.
"""

from ..profile import PROFILE_ID as PROFILE_LAYER_ID
from . import PROFILE_ID
from pas.plugins.identity.core.pas import PLUGIN_ID as CORE_PLUGIN_ID
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from pas.plugins.identity.server.claims import claims_for
from pas.plugins.identity.server.claims import released
from pas.plugins.identity.server.tokens import ISSUER_RECORD
from plone import api

import base64
import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])

USERID = "alice"
ADDRESS = "alice@example.org"

#: The smallest valid PNG, so a test never carries a binary fixture file.
PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00"
    b"\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\n"
    b"IDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00"
    b"\x00IEND\xaeB`\x82"
)


@pytest.fixture
def user(portal):
    """A user with every mappable property filled in."""
    with api.env.adopt_roles(["Manager"]):
        member = api.user.create(
            email=ADDRESS,
            username=USERID,
            password="irrelevant-to-claims",
            properties={
                "fullname": "Alice Liddell",
                "home_page": "https://alice.example.org",
                "location": "Oxford",
                "description": "Curious.",
            },
        )
    return member


@pytest.fixture
def verified(portal, user):
    """Record that this site verified Alice's address with a magic link."""
    store = portal.acl_users[CORE_PLUGIN_ID].store
    store.add(EMAIL_PROVIDER, ADDRESS, USERID, {})
    return store


@pytest.fixture
def portrait(portal, user):
    """Store a portrait for Alice.

    :param portal: The Plone site.
    :param user: The member it belongs to.
    :returns: The userid.
    """
    from pas.plugins.identity.core.portraits import store

    # A one-pixel PNG: the smallest thing ``scale_image`` will accept.
    data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8"
        "BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    with api.env.adopt_roles(["Manager"]):
        store(USERID, data)
    return USERID


class TestScopeRelease:
    """Which claims a scope releases, with no user in sight."""

    def test_openid_alone_releases_nothing(self):
        """`sub` is not scope-gated, so the scope that asks for an identity
        releases no claims of its own."""
        assert released("openid") == []

    def test_profile_releases_the_profile_claims(self):
        assert released("profile") == [
            "name",
            "preferred_username",
            "website",
            "picture",
            "description",
        ]

    def test_email_releases_the_address_and_its_status(self):
        assert released("email") == ["email", "email_verified"]

    def test_scopes_combine(self):
        assert "name" in released("openid profile email")
        assert "email" in released("openid profile email")

    def test_an_unknown_scope_releases_nothing(self):
        """Quietly, not with an exception: the authorization endpoint already
        refused any scope the client is not registered for, so an unknown one
        here means a site removed a scope after a token was issued."""
        assert released("openid telepathy") == []

    def test_claims_are_not_repeated(self):
        """Two scopes releasing the same claim must not emit it twice."""
        assert released("profile profile") == released("profile")


class TestClaims:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, user) -> None:
        self.portal = portal

    def test_sub_is_always_present(self):
        """Even with no scope at all: a token that says nothing about who it
        speaks for is not an identity token."""
        assert claims_for(USERID) == {"sub": USERID}

    def test_no_scope_releases_no_personal_data(self):
        assert "email" not in claims_for(USERID)
        assert "name" not in claims_for(USERID)

    def test_the_profile_scope_maps_plone_properties(self):
        claims = claims_for(USERID, "profile")

        assert claims["name"] == "Alice Liddell"
        assert claims["website"] == "https://alice.example.org"

    def test_preferred_username_is_the_login_not_the_userid(self):
        """Userids are uuid4 hex (D10) and mean nothing to a person. The
        login is what they typed."""
        assert claims_for(USERID, "profile")["preferred_username"] == USERID

    def test_the_email_scope_releases_the_address(self):
        assert claims_for(USERID, "email")["email"] == ADDRESS

    def test_the_address_scope_uses_the_formatted_member(self):
        """Plone's `location` is one free-text line, which is what OIDC's
        `formatted` is for. Splitting it into street and locality would be
        guessing."""
        assert claims_for(USERID, "address")["address"] == {"formatted": "Oxford"}

    def test_the_biography_rides_on_the_profile_scope(self):
        """OIDC has no registered claim for a free-text biography, and this
        one is released under ``profile`` rather than a private scope of its
        own: a relying party that does not know the name ignores it."""
        assert claims_for(USERID, "profile")["description"] == "Curious."

    def test_the_biography_needs_that_scope_like_any_other_claim(self):
        assert "description" not in claims_for(USERID, "openid email address")

    def test_an_empty_property_is_omitted_not_blank(self):
        """OIDC asks that a claim with no value be absent, so a relying party
        can tell "we do not know" from "it is blank"."""
        with api.env.adopt_roles(["Manager"]):
            api.user.get(userid=USERID).setMemberProperties({"home_page": ""})

        assert "website" not in claims_for(USERID, "profile")


class TestPicture:
    """The claim that carries a portrait across two sites.

    A relying party cannot read this site's portrait storage, so the only way
    an avatar reaches one is as a URL it can fetch. ``picture`` is the
    registered claim for it and belongs to the ``profile`` scope, alongside
    ``name`` -- there is nothing to opt into separately."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, user) -> None:
        self.portal = portal
        api.portal.set_registry_record(ISSUER_RECORD, "http://id.example.org")

    def test_absent_when_the_user_has_no_portrait(self):
        """Plone's own ``getPersonalPortrait`` falls back to a default image.
        Publishing that would tell a relying party that every user uploaded
        the same photograph."""
        assert "picture" not in claims_for(USERID, "profile")

    def test_present_once_a_portrait_is_stored(self, portrait):
        assert claims_for(USERID, "profile")["picture"] == (
            "http://id.example.org/@portrait/alice"
        )

    def test_it_is_built_from_the_issuer(self, portrait):
        """Not from the portal URL, which is whatever the request came in on.
        This URL is handed to another site to fetch."""
        api.portal.set_registry_record(ISSUER_RECORD, "http://elsewhere.example.org/")

        assert claims_for(USERID, "profile")["picture"] == (
            "http://elsewhere.example.org/@portrait/alice"
        )

    def test_absent_without_an_issuer(self, portrait):
        """A relative URL is not something another site can fetch."""
        api.portal.set_registry_record(ISSUER_RECORD, "")

        assert "picture" not in claims_for(USERID, "profile")

    def test_it_is_not_released_without_the_profile_scope(self, portrait):
        assert "picture" not in claims_for(USERID, "email")


@pytest.mark.portal(profiles=[PROFILE_ID, PROFILE_LAYER_ID])
class TestPictureOnASiteWithProfiles:
    """The same claim, on a site where the picture is not in memberdata.

    This is the configuration the federation demo runs, and the one that was
    broken: ``portrait_url`` asked ``portal_memberdata`` directly, which is
    the *fallback* store once the ``[profile]`` layer is installed. A user
    with a picture on their Profile got no ``picture`` claim at all -- and an
    omitted claim is indistinguishable downstream from a user who never
    uploaded one, so the relying party had nothing to report either.

    The ``[server]`` layer must not learn which store answered. It asks
    :func:`pas.plugins.identity.core.portraits.has_picture`, and the URL it
    publishes is ``@portrait`` either way.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, user) -> None:
        from pas.plugins.identity.profile.catalog import PROFILE_PORTAL_TYPE
        from pas.plugins.identity.profile.subscribers import get_container
        from plone.namedfile.file import NamedBlobImage

        self.portal = portal
        api.portal.set_registry_record(ISSUER_RECORD, "http://id.example.org")
        with api.env.adopt_roles(["Manager"]):
            self.profile = api.content.create(
                container=get_container(create=True),
                type=PROFILE_PORTAL_TYPE,
                id=USERID,
                userid=USERID,
                login=ADDRESS,
                email=ADDRESS,
            )
        self.profile.image = NamedBlobImage(
            data=PNG, contentType="image/png", filename="me.png"
        )

    def test_the_claim_is_released(self):
        """The bug: empty, because only memberdata was consulted."""
        assert claims_for(USERID, "profile")["picture"] == (
            "http://id.example.org/@portrait/alice"
        )

    def test_it_is_absent_when_the_profile_has_no_picture(self):
        """A Profile is not itself a picture. With neither store holding one
        the claim still has to be omitted."""
        self.profile.image = None

        assert "picture" not in claims_for(USERID, "profile")


class TestEmailVerified:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, user) -> None:
        self.portal = portal

    def test_false_when_this_site_never_verified_it(self):
        """The default. An address that arrived in a provider's claims is not
        verified by this server, whatever the provider said about it."""
        assert claims_for(USERID, "email")["email_verified"] is False

    def test_true_after_a_magic_link(self, verified):
        """A magic link is this site proving the address itself, which is the
        only evidence this server will pass on."""
        assert claims_for(USERID, "email")["email_verified"] is True

    def test_another_users_verification_does_not_count(self, verified):
        """The record is keyed by address, so a check that only asked "is
        this address verified" would hand Alice's proof to anybody who put
        her address in their profile."""
        with api.env.adopt_roles(["Manager"]):
            api.user.create(
                email=ADDRESS,
                username="mallory",
                password="irrelevant-to-claims",
            )

        assert claims_for("mallory", "email")["email_verified"] is False

    def test_it_is_absent_without_an_address(self):
        """A claim about nothing. OIDC readers differ on what to do with
        `email_verified` when there is no `email`, so it is not sent."""
        with api.env.adopt_roles(["Manager"]):
            api.user.get(userid=USERID).setMemberProperties({"email": ""})

        assert "email_verified" not in claims_for(USERID, "email")

    def test_it_is_not_released_without_the_email_scope(self):
        assert "email_verified" not in claims_for(USERID, "profile")
