from . import PROFILE_ID
from pas.plugins.identity.server.controlpanel.clients import authenticate
from pas.plugins.identity.server.controlpanel.clients import ClientConfig
from pas.plugins.identity.server.controlpanel.clients import get_client
from pas.plugins.identity.server.controlpanel.clients import get_clients
from pas.plugins.identity.server.controlpanel.clients import hash_secret
from pas.plugins.identity.server.controlpanel.clients import new_secret
from pas.plugins.identity.server.controlpanel.clients import PUBLIC_AUTH_METHOD
from pas.plugins.identity.server.controlpanel.clients import remove_client
from pas.plugins.identity.server.controlpanel.clients import rotate_secret
from pas.plugins.identity.server.controlpanel.clients import set_clients
from pas.plugins.identity.server.controlpanel.clients import verify_secret
from pas.plugins.identity.server.interfaces import ServerError

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


class TestHashing:
    def test_a_secret_verifies_against_its_own_hash(self):
        """The only property that actually matters."""
        secret = new_secret()

        assert verify_secret(secret, hash_secret(secret))

    def test_a_different_secret_does_not(self):
        """The other half of it."""
        assert not verify_secret("wrong", hash_secret(new_secret()))

    def test_the_same_secret_hashes_differently_every_time(self):
        """Salted. Two clients given the same secret must not look alike in
        the registry."""
        secret = new_secret()

        assert hash_secret(secret) != hash_secret(secret)

    def test_the_hash_does_not_contain_the_secret(self):
        """Stated because it is the whole point of storing a hash."""
        secret = new_secret()

        assert secret not in hash_secret(secret)

    def test_parameters_are_read_from_the_stored_value(self):
        """So hashes written before a cost change keep verifying."""
        stored = hash_secret("s3cret")
        scheme, n, r, p, _salt, _hash = stored.split("$")

        assert scheme == "scrypt"
        assert (int(n), int(r), int(p)) == (2**14, 8, 1)

    @pytest.mark.parametrize(
        "stored",
        [
            "",
            "not-a-hash",
            "bcrypt$1$2$3$ab$cd",
            "scrypt$notanint$8$1$ab$cd",
            "scrypt$16384$8$1$nothex$cd",
        ],
    )
    def test_a_malformed_hash_is_false_not_an_exception(self, stored):
        """This runs on the token endpoint. A raised error would be a
        distinguishable answer, which is the thing being avoided."""
        assert verify_secret("anything", stored) is False

    def test_a_none_hash_is_false_not_an_exception(self):
        """A client record hand-edited to drop the field."""
        assert verify_secret("anything", None) is False


class TestSecrets:
    def test_secrets_are_unique(self):
        """A generator that repeats would hand two clients each other's
        credentials."""
        assert len({new_secret() for _ in range(50)}) == 50

    def test_secrets_are_url_safe(self):
        """They travel in form posts and headers."""
        secret = new_secret()

        assert secret.isascii()
        assert " " not in secret


class TestRedirectURIs:
    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.client = ClientConfig(
            client_id="app",
            redirect_uris=["https://app.example.org/callback"],
        )

    def test_the_registered_uri_matches(self):
        """The baseline."""
        assert self.client.check_redirect_uri("https://app.example.org/callback")

    @pytest.mark.parametrize(
        "uri",
        [
            "https://app.example.org/callback/",
            "https://app.example.org/callback?next=/",
            "https://app.example.org/callback/../evil",
            "https://app.example.org/callbackevil",
            "https://evil.example.org/callback",
            "http://app.example.org/callback",
            "HTTPS://APP.EXAMPLE.ORG/callback",
            "",
        ],
    )
    def test_anything_else_does_not(self, uri):
        """Matching is exact. Every one of these has been somebody's open
        redirect: a trailing slash, an added query, a prefix match, a scheme
        downgrade, a case fold."""
        assert not self.client.check_redirect_uri(uri)

    def test_a_client_with_no_uris_matches_nothing(self):
        """Including the empty string, which is what a missing parameter
        arrives as."""
        bare = ClientConfig(client_id="bare")

        assert not bare.check_redirect_uri("")


class TestPublicClients:
    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.public = ClientConfig(client_id="spa", auth_method=PUBLIC_AUTH_METHOD)
        self.confidential = ClientConfig(
            client_id="svc",
            auth_method="client_secret_post",
            secret_hash=hash_secret("s3cret"),
        )

    def test_a_public_client_is_public(self):
        assert self.public.is_public

    def test_a_confidential_client_is_not(self):
        assert not self.confidential.is_public

    def test_pkce_is_required_for_a_public_client(self):
        """It has no secret, so the exchange itself has to prove possession."""
        assert self.public.requires_pkce

    def test_pkce_is_not_forced_for_a_confidential_one(self):
        """It authenticates at the token endpoint, which already proves
        possession."""
        assert not self.confidential.requires_pkce

    def test_a_public_client_rejects_every_secret(self):
        """It has none, so presenting one is wrong rather than unchecked."""
        assert not self.public.check_secret("")
        assert not self.public.check_secret("anything")

    def test_a_confidential_client_checks_its_secret(self):
        assert self.confidential.check_secret("s3cret")
        assert not self.confidential.check_secret("wrong")

    def test_a_confidential_client_with_no_stored_hash_rejects(self):
        """A half-written record must not become a client anybody can be."""
        broken = ClientConfig(client_id="broken", auth_method="client_secret_post")

        assert not broken.check_secret("")


class TestSerialization:
    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.client = ClientConfig(
            client_id="app",
            title="The App",
            redirect_uris=["https://app.example.org/cb"],
            grant_types=["authorization_code", "refresh_token"],
            scope="openid profile",
            auth_method="client_secret_post",
            secret_hash=hash_secret("s3cret"),
        )

    def test_the_hash_is_left_out_by_default(self):
        """A hash is not a secret, but publishing one invites an offline
        attack on a value the site owner cannot rotate silently."""
        assert "secret_hash" not in self.client.serialize()

    def test_the_hash_is_included_for_storage(self):
        """Otherwise a round-trip through the registry would forget it."""
        assert self.client.serialize(include_hash=True)["secret_hash"]

    def test_a_round_trip_preserves_everything(self):
        restored = ClientConfig.deserialize(self.client.serialize(include_hash=True))

        assert restored.serialize(include_hash=True) == self.client.serialize(
            include_hash=True
        )

    def test_a_round_trip_preserves_the_secret(self):
        """The stored hash still verifies afterwards, which is what a
        round-trip is for."""
        restored = ClientConfig.deserialize(self.client.serialize(include_hash=True))

        assert restored.check_secret("s3cret")

    def test_defaults_fill_in_for_a_sparse_record(self):
        """Hand-written GenericSetup XML will not carry every key."""
        sparse = ClientConfig.deserialize({"client_id": "minimal"})

        assert sparse.grant_types == ["authorization_code"]
        assert sparse.is_public
        assert sparse.enabled

    def test_repr_names_the_client_and_its_kind(self):
        assert repr(self.client) == "<ClientConfig app (confidential)>"

    def test_repr_of_a_public_client_says_so(self):
        assert repr(ClientConfig(client_id="spa")) == "<ClientConfig spa (public)>"


class TestScopes:
    def test_scopes_split_on_whitespace(self):
        client = ClientConfig(client_id="app", scope="openid profile email")

        assert client.scopes() == {"openid", "profile", "email"}

    def test_no_scope_is_an_empty_set(self):
        assert ClientConfig(client_id="app").scopes() == set()

    def test_a_registered_grant_is_allowed(self):
        client = ClientConfig(client_id="app", grant_types=["client_credentials"])

        assert client.allows_grant("client_credentials")

    def test_an_unregistered_grant_is_not(self):
        """A client registered for one grant must not reach another."""
        client = ClientConfig(client_id="app", grant_types=["client_credentials"])

        assert not client.allows_grant("authorization_code")


class TestStorage:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_an_unconfigured_site_has_no_clients(self):
        """And answers with a list, not None."""
        assert get_clients() == []

    def test_an_unknown_client_is_none(self):
        assert get_client("nobody") is None

    def test_a_stored_client_comes_back(self):
        set_clients([ClientConfig(client_id="app", title="The App")])

        assert get_client("app").title == "The App"

    def test_storing_replaces_rather_than_appends(self):
        set_clients([ClientConfig(client_id="a")])
        set_clients([ClientConfig(client_id="b")])

        assert [c.client_id for c in get_clients()] == ["b"]

    def test_order_is_preserved(self):
        """The control panel lists them in the order the site owner put
        them."""
        set_clients([ClientConfig(client_id=name) for name in ("c", "a", "b")])

        assert [c.client_id for c in get_clients()] == ["c", "a", "b"]


class TestRegistering:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, add_client) -> None:
        self.portal = portal
        self.add_client = add_client

    def test_a_confidential_client_gets_a_secret(self):
        _client, secret = self.add_client("svc", public=False)

        assert secret

    def test_the_secret_verifies_once_stored(self):
        """The whole registration is pointless if the minted secret is not
        the one the stored hash answers to."""
        _client, secret = self.add_client("svc", public=False)

        assert get_client("svc").check_secret(secret)

    def test_the_secret_is_not_recoverable(self):
        """It is returned once and hashed on the way in."""
        _client, secret = self.add_client("svc", public=False)

        assert secret not in str(get_client("svc").serialize(include_hash=True))

    def test_a_public_client_gets_no_secret(self):
        _client, secret = self.add_client("spa", public=True)

        assert secret == ""
        assert get_client("spa").is_public

    def test_registering_keeps_the_existing_clients(self):
        self.add_client("first")
        self.add_client("second")

        assert [c.client_id for c in get_clients()] == ["first", "second"]

    def test_a_duplicate_id_is_refused(self):
        """Silently replacing one would re-point every token minted for it."""
        self.add_client("app")

        with pytest.raises(ServerError, match="already registered"):
            self.add_client("app")

    def test_a_refused_duplicate_changes_nothing(self):
        _client, secret = self.add_client("app", public=False)

        with pytest.raises(ServerError):
            self.add_client("app")

        assert get_client("app").check_secret(secret)


class TestRotating:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, add_client) -> None:
        self.portal = portal
        self.add_client = add_client

    def test_the_new_secret_works(self):
        self.add_client("svc", public=False)

        rotated = rotate_secret("svc")

        assert get_client("svc").check_secret(rotated)

    def test_the_old_secret_stops_working(self):
        """Which is what rotation is for."""
        _client, original = self.add_client("svc", public=False)

        rotate_secret("svc")

        assert not get_client("svc").check_secret(original)

    def test_rotating_leaves_the_rest_of_the_record_alone(self):
        self.add_client("svc", title="Service", redirect_uris=["https://a/cb"])

        rotate_secret("svc")

        client = get_client("svc")
        assert client.title == "Service"
        assert client.redirect_uris == ["https://a/cb"]

    def test_rotating_leaves_other_clients_alone(self):
        _client, other = self.add_client("other", public=False)
        self.add_client("svc", public=False)

        rotate_secret("svc")

        assert get_client("other").check_secret(other)

    def test_rotating_an_unknown_client_is_refused(self):
        with pytest.raises(ServerError, match="not registered"):
            rotate_secret("nobody")

    def test_rotating_a_public_client_is_refused(self):
        """Rather than quietly giving it a secret it will never send."""
        self.add_client("spa", public=True)

        with pytest.raises(ServerError, match="public"):
            rotate_secret("spa")


class TestRemoving:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, add_client) -> None:
        self.portal = portal
        self.add_client = add_client

    def test_a_removed_client_is_gone(self):
        self.add_client("app")

        remove_client("app")

        assert get_client("app") is None

    def test_removing_leaves_the_others(self):
        self.add_client("keep")
        self.add_client("drop")

        remove_client("drop")

        assert [c.client_id for c in get_clients()] == ["keep"]

    def test_removing_an_unknown_client_is_refused(self):
        """Loudly, so a typo in a deployment script is not mistaken for a
        successful cleanup."""
        with pytest.raises(ServerError, match="not registered"):
            remove_client("nobody")


class TestAuthenticating:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, add_client) -> None:
        self.portal = portal
        self.add_client = add_client

    def test_the_right_secret_authenticates(self):
        _client, secret = self.add_client("svc", public=False)

        assert authenticate("svc", secret).client_id == "svc"

    def test_the_wrong_secret_does_not(self):
        self.add_client("svc", public=False)

        assert authenticate("svc", "wrong") is None

    def test_an_unknown_client_does_not(self):
        assert authenticate("nobody", "anything") is None

    def test_a_public_client_cannot_authenticate_this_way(self):
        """It has no secret; letting it through on an empty one would make
        every public client impersonatable."""
        self.add_client("spa", public=True)

        assert authenticate("spa", "") is None

    def test_a_disabled_client_does_not(self):
        """Disabling has to stop tokens, not merely hide the client."""
        _client, secret = self.add_client("svc", public=False)
        clients = get_clients()
        clients[0].enabled = False
        set_clients(clients)

        assert authenticate("svc", secret) is None
