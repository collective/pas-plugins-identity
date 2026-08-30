"""The authorization server's admin API.

``@identity-providers`` manages who this site lets people log in *with*; this
is the other direction. The tests that matter most are about the secret,
because its handling is the opposite of the provider API's and the difference
is easy to "fix" into a bug: a provider's secret is masked and echoed back
unchanged, while a client's is hashed at rest and exists exactly once, in the
response that mints it.
"""

from . import PROFILE_ID
from . import REDIRECT
from pas.plugins.identity.server.controlpanel.clients import get_client
from pas.plugins.identity.server.controlpanel.clients import verify_secret
from pas.plugins.identity.server.services.clients.delete import ClientsDelete
from pas.plugins.identity.server.services.clients.get import ClientsGet
from pas.plugins.identity.server.services.clients.patch import ClientsPatch
from pas.plugins.identity.server.services.clients.post import ClientsPost
from pas.plugins.identity.server.services.keys import KeysGet
from pas.plugins.identity.server.services.keys import KeysPost
from pas.plugins.identity.server.utils.keys import get_keys
from plone import api
from plone.app.testing import logout

import json
import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


@pytest.fixture
def manager(portal):
    """Run the tests as somebody who may manage the site."""
    with api.env.adopt_roles(["Manager"]):
        yield


def call(service_class, portal, *segments, body=None):
    """Drive a service and return ``(status, payload)``.

    :param service_class: The service to construct.
    :param portal: The Plone site.
    :param segments: Path segments after the endpoint name.
    :param body: JSON body to send, if any.
    :returns: Status code and the reply.
    """
    request = portal.REQUEST
    request.form.clear()
    if body is not None:
        request.set("BODY", json.dumps(body).encode("utf-8"))
        request._body = json.dumps(body).encode("utf-8")
    service = service_class(portal, request)
    for segment in segments:
        service.publishTraverse(request, segment)
    payload = service.reply()
    return request.response.getStatus(), payload


@pytest.fixture
def registered(portal, manager, add_client):
    """One confidential client already in the registry."""
    client, secret = add_client(
        "app",
        title="Example App",
        redirect_uris=[REDIRECT],
        grant_types=["authorization_code"],
        scope="openid profile",
        public=False,
    )
    return client, secret


class TestPermissions:
    """None of this is readable, let alone writable, without Manage portal."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, add_client) -> None:
        self.portal = portal
        with api.env.adopt_roles(["Manager"]):
            add_client("app", redirect_uris=[REDIRECT], public=False)

    def test_anonymous_is_refused(self):
        logout()

        status, payload = call(ClientsGet, self.portal)

        assert status == 401
        assert payload["error"]["type"] == "Not authenticated"

    def test_an_ordinary_user_is_refused(self):
        """A client registration names who may obtain tokens for this site's
        users. It is not ordinary-member reading."""
        status, payload = call(ClientsGet, self.portal)

        assert status == 403
        assert payload["error"]["type"] == "Not allowed"

    def test_a_manager_is_allowed(self, manager):
        status, _payload = call(ClientsGet, self.portal)

        assert status == 200

    @pytest.mark.parametrize(
        ("service", "segments"),
        [
            (ClientsGet, ()),
            (ClientsPost, ()),
            (ClientsPatch, ("app",)),
            (ClientsDelete, ("app",)),
            (KeysGet, ()),
            (KeysPost, ("rotate",)),
        ],
    )
    def test_every_verb_is_guarded(self, service, segments):
        """Driven off a list rather than spot-checked. The guard on the write
        verbs matters more than on the read ones, and it was the read ones a
        hand-written test happened to cover."""
        status, payload = call(service, self.portal, *segments, body={})

        assert status == 403
        assert payload["error"]["type"] == "Not allowed"

    @pytest.mark.parametrize(
        ("service", "segments"),
        [
            (ClientsPost, ()),
            (ClientsPatch, ("app",)),
            (ClientsDelete, ("app",)),
            (KeysPost, ("rotate",)),
        ],
    )
    def test_no_write_happens_when_refused(self, service, segments):
        """A guard that returns the right status after doing the work is not
        a guard."""
        before = len(get_keys()), get_client("app").title

        call(service, self.portal, *segments, body={"title": "changed"})

        assert (len(get_keys()), get_client("app").title) == before


class TestReading:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, manager, registered) -> None:
        self.portal = portal
        self.client, self.secret = registered

    def test_it_lists_the_registry(self):
        _status, payload = call(ClientsGet, self.portal)

        assert payload["items_total"] == 1
        assert payload["items"][0]["client_id"] == "app"

    def test_it_reads_one(self):
        _status, payload = call(ClientsGet, self.portal, "app")

        assert payload["title"] == "Example App"

    def test_an_unknown_client_is_a_404(self):
        status, _payload = call(ClientsGet, self.portal, "nobody")

        assert status == 404

    def test_the_secret_hash_never_leaves(self):
        """Not a secret, but publishing one invites an offline attack on a
        value the site owner cannot rotate without breaking the client."""
        _status, payload = call(ClientsGet, self.portal, "app")

        assert "secret_hash" not in payload
        assert "secret" not in payload


class TestRegistering:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, manager) -> None:
        self.portal = portal

    def test_it_creates_a_client(self):
        status, _payload = call(
            ClientsPost,
            self.portal,
            body={"client_id": "new", "redirect_uris": [REDIRECT]},
        )

        assert status == 201
        assert get_client("new") is not None

    def test_the_secret_comes_back_once(self):
        _status, payload = call(
            ClientsPost,
            self.portal,
            body={"client_id": "new", "redirect_uris": [REDIRECT]},
        )

        assert verify_secret(payload["secret"], get_client("new").secret_hash)

    def test_the_response_says_it_will_not_be_shown_again(self):
        """An operator who does not know that loses it and files a bug."""
        _status, payload = call(
            ClientsPost,
            self.portal,
            body={"client_id": "new", "redirect_uris": [REDIRECT]},
        )

        assert "only time" in payload["notice"]

    def test_reading_it_back_does_not_include_the_secret(self):
        call(
            ClientsPost,
            self.portal,
            body={"client_id": "new", "redirect_uris": [REDIRECT]},
        )

        _status, payload = call(ClientsGet, self.portal, "new")

        assert "secret" not in payload

    def test_a_public_client_gets_no_secret(self):
        _status, payload = call(
            ClientsPost,
            self.portal,
            body={"client_id": "spa", "redirect_uris": [REDIRECT], "public": True},
        )

        assert payload["public"] is True
        assert "secret" not in payload

    def test_a_duplicate_id_is_refused(self):
        """Reusing an id would silently re-point every token minted for it."""
        call(
            ClientsPost,
            self.portal,
            body={"client_id": "new", "redirect_uris": [REDIRECT]},
        )

        status, _payload = call(
            ClientsPost,
            self.portal,
            body={"client_id": "new", "redirect_uris": [REDIRECT]},
        )

        assert status == 409

    def test_a_missing_client_id_is_refused(self):
        status, _payload = call(ClientsPost, self.portal, body={"title": "No id"})

        assert status == 400

    def test_a_code_client_without_a_redirect_uri_is_refused(self):
        """It could never complete a flow, and the failure would surface much
        later at /authorize looking like a client bug."""
        status, payload = call(ClientsPost, self.portal, body={"client_id": "broken"})

        assert status == 400
        assert "redirect_uri" in payload["error"]["message"]

    def test_a_client_credentials_client_needs_no_redirect_uri(self):
        status, _payload = call(
            ClientsPost,
            self.portal,
            body={"client_id": "svc", "grant_types": ["client_credentials"]},
        )

        assert status == 201


class TestRotatingASecret:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, manager, registered) -> None:
        self.portal = portal
        self.client, self.secret = registered

    def test_it_mints_a_different_secret(self):
        _status, payload = call(ClientsPost, self.portal, "app", "rotate-secret")

        assert payload["secret"] != self.secret

    def test_the_old_secret_stops_verifying(self):
        call(ClientsPost, self.portal, "app", "rotate-secret")

        assert not verify_secret(self.secret, get_client("app").secret_hash)

    def test_an_unknown_client_is_a_404(self):
        status, _payload = call(ClientsPost, self.portal, "nobody", "rotate-secret")

        assert status == 404

    def test_a_public_client_has_nothing_to_rotate(self, add_client):
        add_client("spa", redirect_uris=[REDIRECT], public=True)

        status, _payload = call(ClientsPost, self.portal, "spa", "rotate-secret")

        assert status == 400

    def test_an_unknown_action_is_refused(self):
        status, _payload = call(ClientsPost, self.portal, "app", "explode")

        assert status == 400


class TestAmending:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, manager, registered) -> None:
        self.portal = portal

    def test_it_updates_a_field(self):
        _status, payload = call(
            ClientsPatch, self.portal, "app", body={"title": "Renamed"}
        )

        assert payload["title"] == "Renamed"
        assert get_client("app").title == "Renamed"

    def test_it_can_disable_a_client(self):
        """Which is this server's revocation lever: the Bearer plugin checks
        the audience against the registry on every request."""
        call(ClientsPatch, self.portal, "app", body={"enabled": False})

        assert get_client("app").enabled is False

    def test_the_client_id_cannot_be_changed(self):
        """Renaming would orphan every token already minted for it."""
        status, payload = call(
            ClientsPatch, self.portal, "app", body={"client_id": "renamed"}
        )

        assert status == 400
        assert "client_id" in payload["error"]["message"]

    def test_the_auth_method_cannot_be_changed(self):
        """Turning a confidential client public would leave a stored secret
        hash that nothing checks."""
        status, _payload = call(
            ClientsPatch, self.portal, "app", body={"auth_method": "none"}
        )

        assert status == 400

    def test_an_unknown_field_is_refused_not_ignored(self):
        """Silently ignoring one is how an operator comes to believe they
        changed something they did not."""
        status, _payload = call(
            ClientsPatch, self.portal, "app", body={"nonsense": True}
        )

        assert status == 400

    def test_an_unknown_client_is_a_404(self):
        status, _payload = call(
            ClientsPatch, self.portal, "nobody", body={"title": "x"}
        )

        assert status == 404

    def test_a_missing_id_is_refused(self):
        status, _payload = call(ClientsPatch, self.portal, body={"title": "x"})

        assert status == 400


class TestUnregistering:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, manager, registered) -> None:
        self.portal = portal

    def test_it_removes_the_client(self):
        status, payload = call(ClientsDelete, self.portal, "app")

        assert status == 204
        assert payload is None
        assert get_client("app") is None

    def test_an_unknown_client_is_a_404(self):
        status, _payload = call(ClientsDelete, self.portal, "nobody")

        assert status == 404

    def test_a_missing_id_is_refused(self):
        status, _payload = call(ClientsDelete, self.portal)

        assert status == 400


class TestTheKeyRing:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, manager) -> None:
        self.portal = portal

    def test_it_describes_the_ring(self):
        _status, payload = call(KeysGet, self.portal)

        assert payload["items_total"] == 1
        assert payload["algorithm"] == "RS256"

    def test_the_newest_key_is_the_active_one(self):
        _status, payload = call(KeysGet, self.portal)

        assert payload["items"][0]["active"] is True

    def test_no_key_material_is_returned(self):
        """Not even the public halves. Those are already at the JWKS, and a
        second copy is one for somebody to fetch out of step with the
        first."""
        _status, payload = call(KeysGet, self.portal)

        rendered = json.dumps(payload)
        assert '"n":' not in rendered
        assert '"d":' not in rendered
        assert set(payload["items"][0]) == {"kid", "active"}

    def test_it_points_at_the_jwks(self):
        _status, payload = call(KeysGet, self.portal)

        assert payload["jwks_uri"].endswith("/@@oauth-jwks")

    def test_rotating_adds_a_key(self):
        _status, payload = call(KeysPost, self.portal, "rotate")

        assert payload["items_total"] == 2

    def test_rotating_keeps_the_old_key_for_verification(self):
        """Tokens minted before the rotation must keep verifying until they
        expire, and they find their key by kid."""
        _status, before = call(KeysGet, self.portal)
        old_kid = before["items"][0]["kid"]

        _status, after = call(KeysPost, self.portal, "rotate")

        assert old_kid in {key["kid"] for key in after["items"]}
        assert after["items"][0]["kid"] != old_kid

    def test_the_ring_is_bounded(self):
        """Rotating past the bound does invalidate tokens still in flight.
        That is a decision, and the response reports the bound so an operator
        can see it rather than discover it."""
        for _ in range(5):
            call(KeysPost, self.portal, "rotate")

        _status, payload = call(KeysGet, self.portal)

        assert payload["items_total"] == payload["ring_size"] == len(get_keys())

    def test_an_unknown_action_is_refused(self):
        status, _payload = call(KeysPost, self.portal, "detonate")

        assert status == 400
