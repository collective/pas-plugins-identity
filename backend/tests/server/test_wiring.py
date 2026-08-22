"""Functional tests that the authorization server's endpoints are published.

Everything else about these endpoints is tested by constructing the views
directly, which is fast and precise but proves nothing about the ZCML. These
go through the real publisher, and they are the only tests that would catch a
wrong ``name``, a permission that refuses anonymous, or -- the one that
matters most here -- a browser layer that leaves the endpoints unreachable in
a site that did apply the profile, or reachable in one that did not.
"""

from bs4 import BeautifulSoup
from pas.plugins.identity import PACKAGE_NAME
from pas.plugins.identity.server.clients import add_client
from pas.plugins.identity.server.tokens import ISSUER_RECORD
from pas.plugins.identity.server.tokens import mint_access_token
from plone import api
from plone.app.testing import applyProfile
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD

import pytest
import requests
import transaction


REDIRECT = "https://app.example.org/cb"
ISSUER = "https://id.example.org"

#: The Plone user a client-credentials token acts as, in the Bearer tests.
SERVICE_USER = "svc-indexer"

#: plone.restapi does not traverse an ``@endpoint`` without it.
JSON = {"Accept": "application/json"}


def _fields(html: str) -> dict[str, str]:
    """Return the hidden inputs of the consent form.

    Parsed out of the rendered page rather than rebuilt from what the test
    sent, so a field the template forgets to carry is a failure here instead
    of a passing test that posts it anyway.

    :param html: The consent page.
    :returns: Mapping of field name to value.
    """
    form = BeautifulSoup(html, "html.parser").find("form")
    return {
        field["name"]: field.get("value", "")
        for field in form.find_all("input", attrs={"type": "hidden"})
    }


@pytest.fixture
def server_site(functional):
    """A site with the authorization server switched on and a client set up.

    :param functional: The functional layer.
    :returns: The portal.
    """
    portal = functional["portal"]
    applyProfile(portal, f"{PACKAGE_NAME}:server")
    api.portal.set_registry_record(ISSUER_RECORD, ISSUER)
    add_client(
        "app",
        redirect_uris=[REDIRECT],
        grant_types=["authorization_code"],
        public=False,
    )
    transaction.commit()
    return portal


@pytest.fixture
def url(server_site) -> str:
    """Return the portal URL as served by the test WSGI server."""
    return server_site.absolute_url()


@pytest.fixture
def service_site(functional):
    """A site set up for the client-credentials grant and Bearer tokens.

    :param functional: The functional layer.
    :returns: Mapping of the portal, its URL and the client secret. The
        secret has to be carried out of the fixture because registration is
        the only moment it exists.
    """
    portal = functional["portal"]
    applyProfile(portal, f"{PACKAGE_NAME}:server")
    api.portal.set_registry_record(ISSUER_RECORD, ISSUER)
    with api.env.adopt_roles(["Manager"]):
        api.user.create(
            email="svc@example.org",
            username=SERVICE_USER,
            password="not-used-by-this-grant",
        )
    _client, secret = add_client(
        "svc",
        grant_types=["client_credentials"],
        public=False,
        service_user=SERVICE_USER,
    )
    transaction.commit()
    return {"portal": portal, "url": portal.absolute_url(), "secret": secret}


class TestPublished:
    @pytest.fixture(autouse=True)
    def _setup(self, url: str) -> None:
        self.url = url

    def test_authorize_is_reachable_anonymously(self):
        """A relying party sends a browser here, and that browser may have no
        Plone session at all. The endpoint has to answer, not 401."""
        response = requests.get(
            f"{self.url}/@@oauth-authorize",
            params={
                "response_type": "code",
                "client_id": "app",
                "redirect_uri": REDIRECT,
                "state": "xyzzy",
            },
            allow_redirects=False,
            timeout=30,
        )

        assert response.status_code == 302
        assert response.headers["Location"].startswith(REDIRECT)
        assert "error=login_required" in response.headers["Location"]

    def test_authorize_refuses_an_unregistered_redirect_uri_in_place(self):
        """Through the publisher, because this is the open-redirect
        boundary and a misregistration would be invisible otherwise."""
        response = requests.get(
            f"{self.url}/@@oauth-authorize",
            params={
                "response_type": "code",
                "client_id": "app",
                "redirect_uri": "https://evil.example.org/cb",
            },
            allow_redirects=False,
            timeout=30,
        )

        assert response.status_code == 400
        assert "Location" not in response.headers

    def test_authorize_asks_an_authenticated_user_first(self):
        """A real session gets the consent screen, not a code. Through the
        publisher because the template only compiles here: a page template is
        cooked on first render, so a broken one is invisible to every test
        that constructs the view and reads the redirect."""
        response = requests.get(
            f"{self.url}/@@oauth-authorize",
            params={
                "response_type": "code",
                "client_id": "app",
                "redirect_uri": REDIRECT,
                "state": "xyzzy",
            },
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD),
            allow_redirects=False,
            timeout=30,
        )

        assert response.status_code == 200
        assert "<form" in response.text

    def test_consenting_issues_a_code(self):
        """The success path end to end: a real session, a real form, a real
        CSRF token, a real redirect."""
        browser = requests.Session()
        browser.auth = (SITE_OWNER_NAME, SITE_OWNER_PASSWORD)
        form = browser.get(
            f"{self.url}/@@oauth-authorize",
            params={
                "response_type": "code",
                "client_id": "app",
                "redirect_uri": REDIRECT,
                "state": "xyzzy",
            },
            timeout=30,
        )

        response = browser.post(
            f"{self.url}/@@oauth-authorize",
            data={**_fields(form.text), "consent": "allow"},
            allow_redirects=False,
            timeout=30,
        )

        assert response.status_code == 302
        assert "code=" in response.headers["Location"]
        assert "state=xyzzy" in response.headers["Location"]

    def test_token_is_reachable_anonymously(self):
        """The caller is a server holding client credentials, not a Plone
        user; authentication happens inside against the client registry."""
        response = requests.post(
            f"{self.url}/@@oauth-token",
            data={
                "grant_type": "authorization_code",
                "code": "never-issued",
                "redirect_uri": REDIRECT,
                "client_id": "app",
                "client_secret": "wrong",
            },
            timeout=30,
        )

        assert response.status_code == 401
        assert response.json()["error"] == "invalid_client"

    def test_token_accepts_form_encoding(self):
        """The reason these are browser views and not restapi services: an
        OAuth client posts a form, never a JSON body."""
        response = requests.post(
            f"{self.url}/@@oauth-token",
            data={"grant_type": "password", "client_id": "app"},
            timeout=30,
        )

        assert response.headers["Content-Type"].startswith("application/json")
        assert response.json()["error"] == "unsupported_grant_type"

    def test_token_refuses_get(self):
        response = requests.get(f"{self.url}/@@oauth-token", timeout=30)

        assert response.status_code == 405


class TestBearerAuthentication:
    """The token doing what it was issued for, through the real publisher.

    Everything else about the Bearer plugin is tested by handing it
    credentials directly, which proves the checks and proves nothing about
    the wiring. These go through PAS's own extraction chain -- which is where
    the plugin's marker gets overwritten with its plugin id, and where Plone's
    ``jwt_auth`` is reading the same header at the same time.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, service_site) -> None:
        self.url = service_site["url"]
        self.secret = service_site["secret"]
        self.token = mint_access_token("svc", SERVICE_USER)[0]

    def test_a_token_authenticates_its_subject(self):
        response = requests.get(
            f"{self.url}/@users/{SERVICE_USER}",
            headers={**JSON, "Authorization": f"Bearer {self.token}"},
            timeout=30,
        )

        assert response.status_code == 200
        assert response.json()["id"] == SERVICE_USER

    def test_without_the_token_the_same_request_is_anonymous(self):
        """The control. Without it the test above proves only that the URL
        is readable, not that the token did anything."""
        response = requests.get(
            f"{self.url}/@users/{SERVICE_USER}", headers=JSON, timeout=30
        )

        assert response.status_code == 401

    def test_a_garbage_token_does_not_authenticate(self):
        response = requests.get(
            f"{self.url}/@users/{SERVICE_USER}",
            headers={**JSON, "Authorization": "Bearer not-a-jwt"},
            timeout=30,
        )

        assert response.status_code == 401

    def test_the_client_credentials_grant_yields_a_usable_token(self):
        """The whole of S1d in one test: a server with a client secret and no
        human anywhere gets a token, and that token is a session."""
        minted = requests.post(
            f"{self.url}/@@oauth-token",
            data={
                "grant_type": "client_credentials",
                "client_id": "svc",
                "client_secret": self.secret,
            },
            timeout=30,
        )
        token = minted.json()["access_token"]

        response = requests.get(
            f"{self.url}/@users/{SERVICE_USER}",
            headers={**JSON, "Authorization": f"Bearer {token}"},
            timeout=30,
        )

        assert minted.status_code == 200
        assert response.status_code == 200
        assert response.json()["id"] == SERVICE_USER


class TestNotPublishedWithoutTheProfile:
    """The browser layer is what keeps these endpoints out of a site that
    never switched the server on, which is the whole reason they are bound to
    one. A site without the profile must not publish an /authorize at all."""

    @pytest.fixture(autouse=True)
    def _setup(self, functional) -> None:
        self.url = functional["portal"].absolute_url()

    def test_authorize_is_absent(self):
        response = requests.get(
            f"{self.url}/@@oauth-authorize",
            allow_redirects=False,
            timeout=30,
        )

        assert response.status_code == 404

    def test_token_is_absent(self):
        response = requests.post(f"{self.url}/@@oauth-token", timeout=30)

        assert response.status_code == 404
