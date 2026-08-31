"""The claims contract.

What this server tells a relying party about a user, and on whose authority.

The tests worth reading twice are the ``email_verified`` ones. That claim is
the one a relying party will auto-link accounts on, and this package's own
core layer refuses to trust a *provider's* assertion of it. Emitting it on
that basis would export the problem rather than solve it, so it is true only
when this site verified the address itself.
"""

from . import PROFILE_ID
from . import USERID
from pas.plugins.identity.core.pas import PLUGIN_ID as CORE_PLUGIN_ID
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from pas.plugins.identity.server.claims import claims_for
from pas.plugins.identity.server.claims import released
from pas.plugins.identity.server.grants.tokens import ISSUER_RECORD
from plone import api
from zope.lifecycleevent import modified

import base64
import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])

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
            "groups",
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
        """Userids are uuid4 hex and mean nothing to a person. The
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
            "http://id.example.org/++api++/@portrait/alice"
        )

    def test_it_is_built_from_the_issuer(self, portrait):
        """Not from the portal URL, which is whatever the request came in on.
        This URL is handed to another site to fetch."""
        api.portal.set_registry_record(ISSUER_RECORD, "http://elsewhere.example.org/")

        assert claims_for(USERID, "profile")["picture"] == (
            "http://elsewhere.example.org/++api++/@portrait/alice"
        )

    def test_absent_without_an_issuer(self, portrait):
        """A relative URL is not something another site can fetch."""
        api.portal.set_registry_record(ISSUER_RECORD, "")

        assert "picture" not in claims_for(USERID, "profile")

    def test_it_is_released_under_the_rest_api_namespace(self, portrait):
        """``@portrait`` is a ``plone.restapi`` service, and ``plone.rest``
        only takes over traversal for a request asking for JSON. Published
        bare, this URL answered 404 for every client that did not claim to
        want a JSON document -- this package's own fetcher among them, and
        any browser rendering the claim in an ``<img>``. Asserted on its own
        because the rest of the URL can be read without noticing that the
        namespace is what makes it resolve.
        """
        assert "/++api++/@portrait/" in claims_for(USERID, "profile")["picture"]

    def test_it_is_not_released_without_the_profile_scope(self, portrait):
        assert "picture" not in claims_for(USERID, "email")


@pytest.mark.portal(profiles=[PROFILE_ID])
class TestPictureOnASiteWithProfiles:
    """The same claim, on a site where the picture is not in memberdata.

    This is the configuration the federation demo runs, and the one that was
    broken: ``portrait_url`` asked ``portal_memberdata`` directly, which is
    the *fallback* store for a user who has a Profile. A user
    with a picture on their Profile got no ``picture`` claim at all -- and an
    omitted claim is indistinguishable downstream from a user who never
    uploaded one, so the relying party had nothing to report either.

    The ``[server]`` layer must not learn which store answered. It asks
    :func:`pas.plugins.identity.core.portraits.has_picture`, and the URL it
    publishes is ``@portrait`` either way.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, user) -> None:
        from pas.plugins.identity.core.subscribers import get_profile
        from plone.namedfile.file import NamedBlobImage

        self.portal = portal
        api.portal.set_registry_record(ISSUER_RECORD, "http://id.example.org")
        # The Profile the ``user`` fixture already minted: adding a user is
        # what creates one, so making a second here is a duplicate id rather
        # than a fixture.
        self.profile = get_profile(USERID)
        self.profile.image = NamedBlobImage(
            data=PNG, contentType="image/png", filename="me.png"
        )

    def test_the_claim_is_released(self):
        """The bug: empty, because only memberdata was consulted."""
        assert claims_for(USERID, "profile")["picture"] == (
            "http://id.example.org/++api++/@portrait/alice"
        )

    def test_it_is_absent_when_the_profile_has_no_picture(self):
        """A Profile is not itself a picture. With neither store holding one
        the claim still has to be omitted."""
        self.profile.image = None

        assert "picture" not in claims_for(USERID, "profile")


class TestGroups:
    """The one claim here that is authorization data rather than display data.

    It rides on ``profile`` deliberately -- see the module docstring of
    :mod:`pas.plugins.identity.server.claims` -- which means every relying
    party granted a display scope receives it. What the server controls is
    what goes in it.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, user) -> None:
        self.portal = portal

    def test_a_user_in_no_group_gets_no_claim(self):
        """Omitted rather than sent as an empty list.

        Every principal is in ``AuthenticatedUsers``, so without the filter
        this would be the one claim that is never absent.
        """
        assert "groups" not in claims_for(USERID, "openid profile")

    def test_it_carries_the_groups_the_user_is_in(self):
        with api.env.adopt_roles(["Manager"]):
            api.group.create(groupname="editors", title="Editors")
            api.group.add_user(groupname="editors", username=USERID)

        assert claims_for(USERID, "openid profile")["groups"] == ["editors"]

    def test_authenticatedusers_is_never_released(self):
        """PAS's virtual group says nothing about anybody, and a relying party
        that mapped it would grant its local counterpart to every federated
        user."""
        with api.env.adopt_roles(["Manager"]):
            api.group.create(groupname="editors", title="Editors")
            api.group.add_user(groupname="editors", username=USERID)

        assert (
            "AuthenticatedUsers" not in claims_for(USERID, "openid profile")["groups"]
        )

    def test_it_is_sorted(self):
        """A claim that reorders between two logins reads as a change to
        anything diffing tokens."""
        with api.env.adopt_roles(["Manager"]):
            for name in ("reviewers", "authors", "editors"):
                api.group.create(groupname=name)
                api.group.add_user(groupname=name, username=USERID)

        assert claims_for(USERID, "openid profile")["groups"] == [
            "authors",
            "editors",
            "reviewers",
        ]

    def test_it_is_not_released_without_the_profile_scope(self):
        with api.env.adopt_roles(["Manager"]):
            api.group.create(groupname="editors", title="Editors")
            api.group.add_user(groupname="editors", username=USERID)

        assert "groups" not in claims_for(USERID, "openid email")


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
        `email_verified` when there is no `email`, so it is not sent.

        The address is cleared through the profile's own list rather than by
        writing an empty ``email``: that field is derived from the list, so
        an empty write is an instruction about nothing and is ignored.
        """
        from pas.plugins.identity.core.subscribers import get_profile
        from zope.lifecycleevent import modified

        with api.env.adopt_roles(["Manager"]):
            # Both stores. A profile carrying no address does not erase what
            # ``portal_memberdata`` holds -- an empty profile field is left
            # out of the sheet rather than shadowing the sheet below it --
            # so clearing one of the two leaves the claim answerable.
            profile = get_profile(USERID)
            if profile is not None:
                profile.emails = ()
                modified(profile)
            api.user.get(userid=USERID).setMemberProperties({"email": ""})

        assert "email_verified" not in claims_for(USERID, "email")

    def test_it_is_not_released_without_the_email_scope(self):
        assert "email_verified" not in claims_for(USERID, "profile")


@pytest.mark.portal(profiles=[PROFILE_ID])
class TestClaimsOnASiteWithProfiles:
    """The two claims that went missing in the federation demo.

    This is the configuration the demo runs, and until now only ``picture``
    was covered in it -- ``name`` and ``email`` were tested for a user with no
    Profile, where they come from ``portal_memberdata`` and nothing is in
    front of them.

    Give the user a Profile and the profile plugin serves the sheet. A Profile
    that does not carry a field used to answer for it anyway, with an empty
    string, and :func:`claims_for` omits an empty value -- so the ``id_token``
    went out with neither claim for a user whose account plainly had both, and
    the relying party seeded an account with no name and no address. Nothing
    downstream can tell that apart from a user who never supplied one.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
        from pas.plugins.identity.core.subscribers import get_container

        self.portal = portal
        api.portal.set_registry_record(ISSUER_RECORD, "http://id.example.org")
        # Built the long way round rather than through ``api.user.create``,
        # because the two halves have to be assembled in this order: an
        # account whose values are in ``portal_memberdata``, and *then* a
        # Profile minted carrying neither. That is an account older than this
        # add-on signing in for the first time, and it is what a provider
        # withholding an address leaves behind.
        acl_users = api.portal.get_tool("acl_users")
        acl_users.source_users.addUser(USERID, USERID, "irrelevant-to-claims")
        api.user.get(userid=USERID).setMemberProperties({
            "fullname": "Alice Liddell",
            "email": ADDRESS,
            "home_page": "https://alice.example.org",
            "location": "Oxford",
            "description": "Curious.",
        })
        with api.env.adopt_roles(["Manager"]):
            self.profile = api.content.create(
                container=get_container(create=True),
                type=PROFILE_PORTAL_TYPE,
                id=USERID,
                userid=USERID,
                login=USERID,
            )

    def test_the_name_is_still_released(self):
        assert claims_for(USERID, "openid profile")["name"] == "Alice Liddell"

    def test_the_address_is_still_released(self):
        assert claims_for(USERID, "openid email")["email"] == ADDRESS

    def test_the_profile_wins_when_it_carries_the_field(self):
        """Falling back must not outrank a Profile that has an answer."""
        with api.env.adopt_roles(["Manager"]):
            self.profile.fullname = "Alice On Her Profile"
            modified(self.profile)

        assert claims_for(USERID, "openid profile")["name"] == "Alice On Her Profile"

    def test_a_claim_nobody_has_a_value_for_is_still_omitted(self):
        """Inheriting a value is not inventing one.

        Cleared in `portal_memberdata` as well, so neither store has an
        answer and the claim has to stay absent rather than going out empty.
        """
        with api.env.adopt_roles(["Manager"]):
            api.user.get(userid=USERID).setMemberProperties({"location": ""})

        assert "address" not in claims_for(USERID, "openid address")
