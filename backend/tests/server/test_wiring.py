"""Functional tests that the authorization server's endpoints are published.

Everything else about these endpoints is tested by constructing the views
directly, which is fast and precise but proves nothing about the ZCML. These
go through the real publisher, and they are the only tests that would catch a
wrong ``name``, a permission that refuses anonymous, or -- the one that
matters most here -- a browser layer that leaves the endpoints unreachable in
a site that did apply the profile, or reachable in one that did not.
"""

from pas.plugins.identity import PACKAGE_NAME
from pas.plugins.identity.server.clients import add_client
from pas.plugins.identity.server.tokens import ISSUER_RECORD
from plone import api
from plone.app.testing import applyProfile
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD

import pytest
import requests
import transaction


REDIRECT = "https://app.example.org/cb"
ISSUER = "https://id.example.org"


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

    def test_authorize_issues_a_code_to_an_authenticated_user(self):
        """The success path end to end: a real session, a real redirect."""
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
