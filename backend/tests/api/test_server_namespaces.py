"""The ``[server]`` namespaces, on a site where the layer is switched on.

``api.claims`` and ``api.clients`` are importable everywhere -- ``test_facade``
asserts that on a site without the profile -- but they only answer once the
authorization server is installed. This module applies the profile and checks
the answers.
"""

from ..server import PROFILE_ID
from pas.plugins.identity import api
from pas.plugins.identity.server.interfaces import ServerError
from zope.lifecycleevent import modified

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


class TestClaims:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_member) -> None:
        self.portal = portal
        self.userid = make_member("alice")

    def test_the_scopes_are_published(self):
        """What the discovery document advertises as ``scopes_supported``."""
        scopes = api.claims.get_scopes()

        assert "profile" in scopes
        assert "email" in scopes

    def test_a_scope_names_the_claims_it_releases(self):
        """Answerable with no user in hand, which is what lets the consent
        screen tell somebody what they are about to release."""
        assert "email" in api.claims.get_released("email")

    def test_an_unserialized_scope_releases_nothing(self):
        """Empty rather than an error: a client may ask for a scope this
        server carries in the token without releasing a claim for it."""
        assert api.claims.get_released("no-such-scope") == []

    def test_the_claims_carry_the_subject(self):
        """``sub`` is the join key a relying party stores, so it is present
        whatever scope was granted."""
        claims = api.claims.get(self.userid)

        assert claims["sub"] == self.userid

    def test_a_granted_scope_releases_its_claims(self):
        """The ordinary case, asked through the façade.

        ``modified`` because the serializers read catalog metadata rather than
        waking every Profile -- a write that is not reindexed is correct on
        the object and invisible to the claim.
        """
        profile = api.profile.get(self.userid)
        profile.fullname = "Alice Liddell"
        modified(profile)

        claims = api.claims.get(self.userid, "openid profile")

        assert claims["name"] == "Alice Liddell"

    def test_every_declared_scope_is_a_supported_one(self):
        """The declaration cannot advertise what the server will not release.

        Not equality: ``openid`` is supported and declares no claims of its
        own, which is what makes it the scope that only asks for a ``sub``.
        """
        declared = set(api.claims.declared_scopes())
        supported = set(api.claims.get_scopes())

        assert declared <= supported
        assert "openid" in supported - declared


class TestClients:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_no_clients_is_an_empty_list(self):
        """Not ``None``, for the same reason ``provider.get_all`` is not."""
        assert api.clients.get_all() == []

    def test_an_unknown_client_is_none(self):
        """A lookup answers ``None``."""
        assert api.clients.get("no-such-client") is None

    def test_registering_returns_the_client_and_its_secret(self):
        """The one time the secret exists in readable form."""
        client, secret = api.clients.add(
            "demo", title="Demo", redirect_uris=["https://app.example.org/cb"]
        )

        assert client.client_id == "demo"
        assert secret

    def test_the_registered_client_is_found(self):
        """Written through the façade, read back through it."""
        api.clients.add("demo", redirect_uris=["https://app.example.org/cb"])

        assert api.clients.get("demo") is not None

    def test_registering_a_second_time_raises(self):
        """An operation, not a lookup: replacing a registration silently
        would re-point every token already minted for it."""
        api.clients.add("demo", redirect_uris=["https://app.example.org/cb"])

        with pytest.raises(ServerError):
            api.clients.add("demo", redirect_uris=["https://app.example.org/cb"])

    def test_the_secret_authenticates_the_client(self):
        """What the token endpoint asks."""
        _, secret = api.clients.add(
            "demo", redirect_uris=["https://app.example.org/cb"]
        )

        assert api.clients.check("demo", secret) is not None

    def test_a_wrong_secret_does_not(self):
        """``None`` rather than an exception: the token endpoint must not be
        able to tell a caller *why* it failed."""
        api.clients.add("demo", redirect_uris=["https://app.example.org/cb"])

        assert api.clients.check("demo", "not-the-secret") is None

    def test_rotating_invalidates_the_old_secret(self):
        """The point of rotating one."""
        _, old = api.clients.add("demo", redirect_uris=["https://app.example.org/cb"])

        new = api.clients.new_secret("demo")

        assert new != old
        assert api.clients.check("demo", old) is None
        assert api.clients.check("demo", new) is not None

    def test_removing_unregisters_it(self):
        """And the lookup goes back to answering ``None``."""
        api.clients.add("demo", redirect_uris=["https://app.example.org/cb"])

        api.clients.remove("demo")

        assert api.clients.get("demo") is None
