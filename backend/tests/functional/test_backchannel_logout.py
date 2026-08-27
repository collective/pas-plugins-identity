"""Back-channel logout, from a provider that really sends one.

Everything about logout in ``tests/core/test_logout.py`` is checked against a
token this package minted and a JWKS it stubbed. That proves the rules are
implemented; it cannot prove they are the *right* rules, because the tokens
were built by the same reading of the specification as the code that accepts
them.

So this test never mints a logout token. Keycloak signs a real one, with its
own key, its own claim shapes and its own idea of what belongs in it, and this
package validates it through discovery against Keycloak's published JWKS.

The one piece of stagecraft is where the token is caught. Keycloak posts it to
the client's registered back-channel URL, and that URL has to be reachable
*from the container*. Rather than teach the Plone test server to bind
somewhere a container can see, the test stands up a small listener of its own,
takes the token Keycloak delivers to it, and posts that token at Plone's
endpoint itself. Nothing about the token is changed on the way, which is the
part that matters: what reaches ``@@backchannel-logout`` is exactly what
Keycloak sent.
"""

from bs4 import BeautifulSoup
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
from pas.plugins.identity import PACKAGE_NAME
from pas.plugins.identity.core.controlpanel import CALLBACK_URL_RECORD
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.flows import metadata as flow_metadata
from pas.plugins.identity.core.pas import PLUGIN_ID as CORE_PLUGIN_ID
from pas.plugins.identity.server.pas import PLUGIN_ID as SERVER_PLUGIN_ID
from plone import api
from plone.app.testing import applyProfile
from urllib.parse import parse_qs
from urllib.parse import urljoin
from urllib.parse import urlparse

import pytest
import requests
import threading
import transaction


pytestmark = pytest.mark.docker

#: Where Keycloak sends the browser back. Nothing serves it; the test reads
#: the code straight off the redirect, as the frontend route would.
CALLBACK_URL = "http://localhost:3000/login-identity"

KC_USER = "elena"
KC_PASSWORD = "elena-password"
REALM = "identity-test"


class _Catcher(BaseHTTPRequestHandler):
    """Collects whatever Keycloak posts, and says thank you."""

    def do_POST(self) -> None:
        """Record the form body and answer 200."""
        length = int(self.headers.get("Content-Length", 0))
        self.server.caught.append(self.rfile.read(length).decode("utf-8"))  # type: ignore[attr-defined]
        self.send_response(200)
        self.end_headers()
        self.server.arrived.set()  # type: ignore[attr-defined]

    def log_message(self, *args) -> None:
        """Stay quiet; pytest captures enough already."""


@pytest.fixture
def catcher():
    """Run a listener the Keycloak container can reach.

    Bound to every interface rather than to localhost, because the request
    arrives from inside a container by way of ``host.docker.internal``.

    :returns: The server, with a ``caught`` list of request bodies and an
        ``arrived`` event set when the first one lands.
    """
    server = HTTPServer(("0.0.0.0", 0), _Catcher)  # noqa: S104 - see above
    server.caught = []
    server.arrived = threading.Event()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()


@pytest.fixture
def admin(keycloak_service: str):
    """Return a helper for Keycloak's admin API.

    :param keycloak_service: The realm issuer URL.
    :returns: Callable taking a path, method and payload.
    """
    base = keycloak_service.split("/realms/")[0]
    token = requests.post(
        f"{base}/realms/master/protocol/openid-connect/token",
        data={
            "client_id": "admin-cli",
            "username": "admin",
            "password": "admin",
            "grant_type": "password",
        },
        timeout=30,
    ).json()["access_token"]

    def call(path: str, method: str = "GET", payload=None):
        """Call Keycloak's admin API.

        :param path: Path under the realm.
        :param method: HTTP method.
        :param payload: JSON body, if any.
        :returns: The decoded answer, or ``None`` for an empty one.
        """
        response = requests.request(
            method,
            f"{base}/admin/realms/{REALM}{path}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json() if response.content else None

    return call


@pytest.fixture
def portal(functional, keycloak):
    """A site with Keycloak configured, and the server layer installed too.

    The server layer is here because half of what a logout has to reach is
    the refresh tokens *this* site issued: the point of the event seam is
    that a logout upstream ends the sessions downstream.
    """
    site = functional["portal"]
    applyProfile(site, f"{PACKAGE_NAME}.server:default")
    set_providers([ProviderConfig.deserialize(keycloak)])
    api.portal.set_registry_record(CALLBACK_URL_RECORD, CALLBACK_URL)
    transaction.commit()
    # A previous module may have primed discovery against Dex or a stub.
    flow_metadata.forget()
    yield site
    set_providers([])
    transaction.commit()
    flow_metadata.forget()


@pytest.fixture
def signed_in(portal, admin, catcher):
    """Log Elena in through the real flow, and return her Plone userid.

    Driving Keycloak's own login form rather than its password grant: the
    session the logout later ends has to be one a browser established, which
    is the case a back-channel logout exists for.

    :returns: The Plone userid Keycloak's subject resolved to.
    """
    url = portal.absolute_url()
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})

    start = session.get(f"{url}/@login-providers/keycloak", timeout=30)
    start.raise_for_status()

    # A separate session for the provider half. The one above asks Plone for
    # JSON, and sending `Accept: application/json` to a login page gets
    # something other than a login page.
    browser = requests.Session()
    page = browser.get(start.json()["authorize_url"], timeout=30)
    page.raise_for_status()
    form = BeautifulSoup(page.text, "html.parser").find("form")
    assert form is not None, f"No login form; Keycloak answered:\n{page.text[:400]}"

    # Keycloak's session cookies are `SameSite=None`, which the cookie
    # specification requires to imply `Secure` -- so `requests` stores them
    # and then declines to send them back over plain HTTP, and Keycloak
    # answers the login form with "Cookie not found". A real deployment is
    # behind TLS and never meets this; putting TLS into the test stack to
    # satisfy a cookie flag would be a lot of machinery for no extra
    # evidence, so the flag is dropped here instead.
    for cookie in browser.cookies:
        cookie.secure = False

    answer = browser.post(
        urljoin(page.url, form["action"]),
        data={"username": KC_USER, "password": KC_PASSWORD},
        allow_redirects=False,
        timeout=30,
    )
    location = answer.headers.get("Location", "")
    assert location.startswith(CALLBACK_URL), (
        f"Keycloak answered {answer.status_code} and redirected to "
        f"{location!r}, not the callback. Body:\n{answer.text[:400]}"
    )
    query = {k: v[0] for k, v in parse_qs(urlparse(location).query).items()}

    finished = session.post(
        f"{url}/@identity-callback",
        json={
            "provider": "keycloak",
            "code": query["code"],
            "state": query["state"],
        },
        timeout=30,
    )
    finished.raise_for_status()

    # The login happened in the server's thread and committed there. Without
    # this the connection under the test still sees the state it started
    # with, and the identity looks as though it was never recorded.
    transaction.begin()
    store = portal.acl_users[CORE_PLUGIN_ID].store
    linked = [
        (userid, record)
        for userid in store.userids()
        for record in store.identities_for(userid)
        if record.provider == "keycloak"
    ]
    assert linked, "the login did not record a keycloak identity"
    return linked[0][0]


@pytest.fixture
def logout_token(portal, admin, catcher, signed_in) -> str:
    """Make Keycloak send a logout token, and return the one it sent.

    :returns: The encoded logout token, exactly as Keycloak posted it.
    """
    client = admin("/clients?clientId=plone")[0]
    client["attributes"]["backchannel.logout.url"] = (
        f"http://host.docker.internal:{catcher.server_address[1]}/logout"
    )
    admin(f"/clients/{client['id']}", "PUT", client)

    user = admin(f"/users?username={KC_USER}")[0]
    admin(f"/users/{user['id']}/logout", "POST", {})

    # Waited on rather than polled: the delivery is a request from another
    # process, so there is nothing to poll *for* except the event the
    # listener already sets when it hands one over.
    assert catcher.arrived.wait(60), "Keycloak sent no logout token"
    return parse_qs(catcher.caught[0])["logout_token"][0]


class TestARealProvidersLogoutToken:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, signed_in, logout_token) -> None:
        self.portal = portal
        self.url = portal.absolute_url()
        self.userid = signed_in
        self.token = logout_token

    def post(self, token: str):
        """Deliver a logout token to the endpoint, as a provider would.

        :param token: The encoded token.
        :returns: The HTTP response.
        """
        return requests.post(
            f"{self.url}/@@backchannel-logout",
            data={"logout_token": token},
            timeout=30,
        )

    def test_the_endpoint_accepts_it(self):
        """The whole point of this module. The token was signed by Keycloak,
        with Keycloak's key and Keycloak's idea of the claim shapes, and it
        is validated through discovery against Keycloak's published JWKS."""
        assert self.post(self.token).status_code == 200

    def test_a_replay_of_the_same_token_is_refused(self):
        """Through a real token, so the `jti` being refused is Keycloak's
        rather than one this test chose."""
        self.post(self.token)

        second = self.post(self.token)

        assert second.status_code == 400
        assert "replayed" in second.json()["error_description"]

    def test_it_revokes_the_refresh_tokens_this_site_issued(self):
        """The event seam, end to end and across two layers: Keycloak ends
        the session upstream, core receives it, and the [server] layer
        revokes the tokens it issued downstream."""
        transaction.begin()
        refresh = self.portal.acl_users[SERVER_PLUGIN_ID].refresh
        refresh.issue("some-client", self.userid, "openid")
        transaction.commit()

        self.post(self.token)

        transaction.begin()
        assert self.portal.acl_users[SERVER_PLUGIN_ID].refresh.count() == 0

    def test_a_token_from_the_wrong_issuer_is_refused(self):
        """Keycloak's signature is not a licence to log anybody out: the
        issuer still has to be a provider this site configured."""
        set_providers([])
        transaction.commit()

        try:
            assert self.post(self.token).status_code == 400
        finally:
            transaction.begin()

    def test_the_jti_is_recorded(self):
        self.post(self.token)

        transaction.begin()
        plugin = self.portal.acl_users[CORE_PLUGIN_ID]
        assert plugin.logout_jtis.count() >= 1
