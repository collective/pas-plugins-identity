"""Asking the consent question somewhere else.

The decision stays at ``@@oauth-authorize`` whatever renders the question --
that is the point of the design and the thing these tests are here to hold
still. What changes is where the browser is sent to be asked, and what a
frontend can find out about the request once it lands there.
"""

from . import PROFILE_ID
from pas.plugins.identity.server.browser.authorize import AuthorizeView
from pas.plugins.identity.server.consent_screen import consent_screen_url
from pas.plugins.identity.server.consent_screen import CONSENT_URL_RECORD
from pas.plugins.identity.server.services.consent.get import ConsentGet
from plone import api
from plone.app.testing import logout
from urllib.parse import parse_qs
from urllib.parse import urlparse

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])

REDIRECT = "https://app.example.org/cb"
SCREEN = "https://id.example.org/oauth-consent"


@pytest.fixture
def client(portal, add_client):
    """A confidential client with two scopes to ask for."""
    client, _secret = add_client(
        "app",
        title="Example App",
        redirect_uris=[REDIRECT],
        grant_types=["authorization_code"],
        scope="openid profile",
        public=False,
    )
    return client


@pytest.fixture
def request_params() -> dict:
    """A valid authorization request, as a relying party would send it."""
    return {
        "response_type": "code",
        "client_id": "app",
        "redirect_uri": REDIRECT,
        "scope": "openid profile",
        "state": "xyz",
    }


def authorize(portal, **params):
    """Drive the authorization endpoint.

    :param portal: The Plone site.
    :param params: Request parameters.
    :returns: Status, the Location header, and the body.
    """
    request = portal.REQUEST
    request.form.clear()
    request.form.update(params)
    body = AuthorizeView(portal, request)()
    return (
        request.response.getStatus(),
        request.response.getHeader("Location"),
        body,
    )


def amend(**changes) -> None:
    """Change the registered client and store it back.

    The registry is the record; a client read out of it is a copy, so a
    change made only on the copy is a test that proves nothing.

    :param changes: Attributes to set on the one registered client.
    """
    from pas.plugins.identity.server.clients import get_clients
    from pas.plugins.identity.server.clients import set_clients

    clients = get_clients()
    for name, value in changes.items():
        setattr(clients[0], name, value)
    set_clients(clients)


def describe(portal, **params):
    """Drive ``@oauth-consent``.

    :param portal: The Plone site.
    :param params: Query parameters.
    :returns: The reply body.
    """
    request = portal.REQUEST
    request.form.clear()
    request.form.update(params)
    return ConsentGet(portal, request).reply()


class TestWhereTheQuestionIsAsked:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, client, request_params) -> None:
        self.portal = portal
        self.client = client
        self.params = request_params

    def test_the_server_asks_it_itself_by_default(self):
        """An authorization server has to work before anybody has built a
        frontend for it, and a Plone site without one still has users."""
        assert consent_screen_url() == ""

        status, location, body = authorize(self.portal, **self.params)

        assert status == 200
        assert location is None
        assert "use your account" in body

    def test_a_configured_screen_gets_the_browser_instead(self):
        api.portal.set_registry_record(CONSENT_URL_RECORD, SCREEN)

        status, location, body = authorize(self.portal, **self.params)

        assert status == 302
        assert location.startswith(f"{SCREEN}?")
        assert body == ""

    def test_the_request_travels_with_it(self):
        """Unchanged and complete: the screen hands it straight back, and a
        request that lost a parameter on the way is a different request."""
        api.portal.set_registry_record(CONSENT_URL_RECORD, SCREEN)

        _status, location, _body = authorize(self.portal, **self.params)

        carried = {k: v[0] for k, v in parse_qs(urlparse(location).query).items()}
        assert carried == self.params

    def test_an_absent_parameter_stays_absent(self):
        """An empty ``code_challenge`` is not the same request as no
        ``code_challenge``, and PKCE turns on that difference."""
        api.portal.set_registry_record(CONSENT_URL_RECORD, SCREEN)

        _status, location, _body = authorize(self.portal, **self.params)

        assert "code_challenge" not in urlparse(location).query

    def test_a_trailing_slash_does_not_become_a_double_one(self):
        api.portal.set_registry_record(CONSENT_URL_RECORD, f"{SCREEN}/")

        _status, location, _body = authorize(self.portal, **self.params)

        assert location.startswith(f"{SCREEN}?")

    def test_nothing_is_issued_on_the_way(self):
        """The screen renders a question. Anything issued before it is
        answered would be an authorization nobody agreed to."""
        api.portal.set_registry_record(CONSENT_URL_RECORD, SCREEN)

        _status, location, _body = authorize(self.portal, **self.params)

        assert "code=" not in location

    def test_a_request_already_agreed_to_never_reaches_it(self):
        """Consent that is already recorded is the case the screen exists to
        avoid: the user is not asked again."""
        api.portal.set_registry_record(CONSENT_URL_RECORD, SCREEN)
        plugin = api.portal.get_tool("acl_users")["identity_server"]
        plugin.consent.record(api.user.get_current().getId(), "app", "openid profile")

        _status, location, _body = authorize(self.portal, **self.params)

        assert location.startswith(REDIRECT)


class TestDescribingTheRequest:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, client, request_params) -> None:
        self.portal = portal
        self.client = client
        self.params = request_params

    def test_it_names_the_client_the_user_is_deciding_about(self):
        assert describe(self.portal, **self.params)["client"] == {
            "id": "app",
            "title": "Example App",
        }

    def test_a_client_with_no_title_is_named_by_its_id(self):
        """Still something the user has to be able to identify, and the id is
        what the operator typed."""
        amend(title="")

        assert describe(self.portal, **self.params)["client"]["title"] == "app"

    def test_it_names_who_would_be_agreeing(self):
        """The browser may hold a session the user forgot about, and agreeing
        on behalf of the wrong account is the mistake this screen exists to
        make visible."""
        body = describe(self.portal, **self.params)

        assert body["user"]["id"] == api.user.get_current().getId()

    def test_it_lists_the_scopes_in_the_order_they_were_asked_for(self):
        body = describe(self.portal, **self.params)

        assert [scope["id"] for scope in body["scopes"]] == ["openid", "profile"]

    def test_it_says_what_each_scope_actually_releases(self):
        """ "profile" means nothing to the person being asked; the list of
        claims is the real question."""
        body = describe(self.portal, **self.params)

        profile = next(s for s in body["scopes"] if s["id"] == "profile")
        assert "preferred_username" in profile["claims"]

    def test_a_scope_that_releases_nothing_is_still_listed(self):
        """``openid`` asks for an identity and gates no claim of its own. A
        screen that dropped it would be describing a different request."""
        body = describe(self.portal, **self.params)

        assert body["scopes"][0] == {"id": "openid", "claims": []}

    def test_it_carries_the_request_back_for_the_answer(self):
        body = describe(self.portal, **self.params)

        assert body["params"] == self.params
        assert body["authorize_url"].endswith("/@@oauth-authorize")

    def test_it_carries_a_token_the_answer_will_be_checked_against(self):
        """A forged consent POST is an attempt to authorize a client on
        somebody else's behalf."""
        assert describe(self.portal, **self.params)["authenticator"]

    def test_it_records_nothing(self):
        """Reading the question must not answer it."""
        plugin = api.portal.get_tool("acl_users")["identity_server"]
        describe(self.portal, **self.params)

        assert (
            plugin.consent.granted(
                api.user.get_current().getId(), "app", "openid profile"
            )
            is False
        )


class TestWhatItRefusesToDescribe:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, client, request_params) -> None:
        self.portal = portal
        self.client = client
        self.params = request_params

    def test_an_unknown_client(self):
        """Otherwise this is a page on the site's own domain asking somebody
        to hand their account to an application nobody registered."""
        body = describe(self.portal, **{**self.params, "client_id": "evil"})

        assert body["error"]["type"] == "Unknown client"

    def test_a_disabled_one(self):
        amend(enabled=False)

        body = describe(self.portal, **self.params)

        assert body["error"]["type"] == "Unknown client"

    def test_a_redirect_uri_that_does_not_match(self):
        """The same refusal the authorization endpoint makes, for the same
        reason: this request has no destination the server trusts."""
        body = describe(
            self.portal, **{**self.params, "redirect_uri": "https://evil/cb"}
        )

        assert body["error"]["type"] == "Unregistered redirect URI"

    def test_an_anonymous_caller(self):
        """The authorization endpoint sends them to log in first, so this is
        a screen somebody opened directly."""
        logout()

        body = describe(self.portal, **self.params)

        assert body["error"]["type"] == "Not authenticated"
