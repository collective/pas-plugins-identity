"""Functional tests that the authorization server's endpoints are published.

Everything else about these endpoints is tested by constructing the views
directly, which is fast and precise but proves nothing about the ZCML. These
go through the real publisher, and they are the only tests that would catch a
wrong ``name``, a permission that refuses anonymous, or -- the one that
matters most here -- a browser layer that leaves the endpoints unreachable in
a site that did apply the profile, or reachable in one that did not.
"""

from . import ISSUER
from . import REDIRECT
from . import SERVICE_USER
from bs4 import BeautifulSoup
from pas.plugins.identity import PACKAGE_NAME
from pas.plugins.identity.server.controlpanel.clients import add_client
from pas.plugins.identity.server.grants.tokens import ISSUER_RECORD
from pas.plugins.identity.server.grants.tokens import mint_access_token
from pas.plugins.identity.server.pas import PLUGIN_ID
from plone import api
from plone.app.testing import applyProfile
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from urllib.parse import parse_qs
from urllib.parse import unquote
from urllib.parse import urlparse

import pytest
import requests
import transaction


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
    applyProfile(portal, f"{PACKAGE_NAME}.server:default")
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
    applyProfile(portal, f"{PACKAGE_NAME}.server:default")
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

    def test_an_anonymous_browser_is_sent_to_log_in(self):
        """A relying party sends a browser here and that browser may have no
        Plone session, which is the normal case rather than an error. This is
        the test that proves the challenge machinery actually engages: the
        view raises Unauthorized and Plone turns it into a redirect."""
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
        assert "came_from" in response.headers["Location"]

    def test_the_whole_request_survives_the_login_redirect(self):
        """The authorization request *is* its query string. If `came_from`
        carried only the path, the user would log in and resume a request
        with no client and no PKCE challenge."""
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

        came_from = unquote(
            parse_qs(urlparse(response.headers["Location"]).query)["came_from"][0]
        )

        assert "client_id=app" in came_from
        assert "state=xyzzy" in came_from
        assert came_from.startswith("/"), "came_from must be a local URL"

    def test_prompt_none_is_still_reported_to_the_client(self):
        """The client asked us not to interact, so the refusal goes back to
        it rather than to a login form."""
        response = requests.get(
            f"{self.url}/@@oauth-authorize",
            params={
                "response_type": "code",
                "client_id": "app",
                "redirect_uri": REDIRECT,
                "prompt": "none",
            },
            allow_redirects=False,
            timeout=30,
        )

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

    def test_the_admin_api_is_absent(self):
        """A site that never switched the server on has no clients to manage
        and should not publish an API implying otherwise."""
        response = requests.get(
            f"{self.url}/@identity-clients",
            headers=JSON,
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD),
            timeout=30,
        )

        assert response.status_code == 404

    def test_the_keys_api_is_absent(self):
        response = requests.get(
            f"{self.url}/@identity-keys",
            headers=JSON,
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD),
            timeout=30,
        )

        assert response.status_code == 404


class TestTheAdminAPIIsPublished:
    """Through the publisher, because the guard's shape matters: a caller
    without the permission must get a JSON refusal, not the login page that
    an anonymous request to a protected view now produces."""

    @pytest.fixture(autouse=True)
    def _setup(self, url: str) -> None:
        self.url = url

    def test_a_manager_can_read_the_registry(self):
        response = requests.get(
            f"{self.url}/@identity-clients",
            headers=JSON,
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD),
            timeout=30,
        )

        assert response.status_code == 200
        assert response.json()["items"][0]["client_id"] == "app"

    def test_an_anonymous_caller_gets_json_not_a_login_page(self):
        """The reason these services are registered for View and guard
        internally. A redirect here would hand an API client an HTML form."""
        response = requests.get(
            f"{self.url}/@identity-clients",
            headers=JSON,
            allow_redirects=False,
            timeout=30,
        )

        assert response.status_code == 401
        assert response.headers["Content-Type"].startswith("application/json")

    def test_the_key_ring_is_readable(self):
        response = requests.get(
            f"{self.url}/@identity-keys",
            headers=JSON,
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD),
            timeout=30,
        )

        assert response.status_code == 200
        assert response.json()["items_total"] == 1


class TestTheConsentAndGrantServicesArePublished:
    """``@oauth-consent`` and ``@oauth-grants``.

    Both were thoroughly tested by constructing the service and never once
    reached through the publisher. They are the two endpoints a *person*
    drives rather than a machine -- the screen that asks whether to hand an
    application their account, and the screen that takes it back -- so a
    registration mistake in either is one a relying party would never report.

    ``@oauth-grants`` is addressed by client id in a path segment on the
    DELETE, which is exactly the shape a direct call cannot check.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, server_site, url: str) -> None:
        self.url = url
        self.admin = (SITE_OWNER_NAME, SITE_OWNER_PASSWORD)
        # An agreement to withdraw. Recorded for the Zope root user, which is
        # who the requests below authenticate as.
        server_site.acl_users[PLUGIN_ID].consent.record(
            SITE_OWNER_NAME, "app", "openid"
        )
        transaction.commit()

    def test_consent_describes_a_request(self):
        """The screen's data comes from here; Volto draws it."""
        response = requests.get(
            f"{self.url}/@oauth-consent",
            params={
                "client_id": "app",
                "redirect_uri": REDIRECT,
                "response_type": "code",
                "scope": "openid",
            },
            headers=JSON,
            auth=self.admin,
            timeout=30,
        )

        assert response.status_code == 200
        assert response.json()["client"]["title"] == "app"

    def test_consent_refuses_anonymous_as_json(self):
        """Nobody can agree to anything before they have signed in, and the
        refusal has to be a body rather than a login form."""
        response = requests.get(
            f"{self.url}/@oauth-consent",
            params={"client_id": "app"},
            headers=JSON,
            allow_redirects=False,
            timeout=30,
        )

        assert response.status_code == 401
        assert response.headers["Content-Type"].startswith("application/json")

    def test_grants_are_listed(self):
        response = requests.get(
            f"{self.url}/@oauth-grants", headers=JSON, auth=self.admin, timeout=30
        )

        assert response.status_code == 200
        assert "items" in response.json()

    def test_grants_refuses_anonymous_as_json(self):
        response = requests.get(
            f"{self.url}/@oauth-grants",
            headers=JSON,
            allow_redirects=False,
            timeout=30,
        )

        assert response.status_code == 401
        assert response.headers["Content-Type"].startswith("application/json")

    def test_withdrawing_traverses_the_client_segment(self):
        """``DELETE @oauth-grants/<client_id>``.

        The agreement is recorded first so this withdraws something real: a
        DELETE against a client the caller never authorized answers 404
        whether traversal worked or not, which is the one status that cannot
        tell a reached service from an unreached one.
        """
        response = requests.delete(
            f"{self.url}/@oauth-grants/app", headers=JSON, auth=self.admin, timeout=30
        )

        assert response.status_code == 200
        assert response.json()["client_id"] == "app"

    def test_withdrawing_needs_exactly_one_segment(self):
        """The refusal is the service's own, which is what makes it evidence
        that the segments reached it rather than the publisher."""
        response = requests.delete(
            f"{self.url}/@oauth-grants/app/extra",
            headers=JSON,
            auth=self.admin,
            timeout=30,
        )

        assert response.status_code == 400
        assert response.json()["error"]["type"] == "Bad request"
