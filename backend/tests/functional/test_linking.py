"""Linking a second identity, against a real provider.

Same shape as the login flow test -- real Dex, real codes -- but the flow is
started from ``@identities`` by an already-authenticated user, and finishes by
attaching a second identity rather than minting an account.
"""

from .conftest import CALLBACK_URL
from pas.plugins.identity.core.pas import PLUGIN_ID
from plone import api
from urllib.parse import parse_qs
from urllib.parse import urlparse

import pytest
import requests
import transaction


pytestmark = pytest.mark.docker


def login_via_dex(api_session, portal_url: str, dex_login) -> str:
    """Complete an ordinary login and return the resulting token.

    :param api_session: The JSON session, which keeps the flow cookie.
    :param portal_url: The portal URL.
    :param dex_login: The Dex form-driving helper.
    :returns: A ``jwt_auth`` token.
    """
    started = api_session.get(f"{portal_url}/@login-providers/dex", timeout=30)
    query = dex_login(started.json()["authorize_url"])
    finished = api_session.post(
        f"{portal_url}/@identity-callback",
        json={"provider": "dex", "code": query["code"], "state": query["state"]},
        timeout=30,
    )
    return finished.json()["token"]


@pytest.fixture
def authenticated(api_session, portal_url, dex_login):
    """Log in through Dex and return a session carrying the token."""
    token = login_via_dex(api_session, portal_url, dex_login)
    api_session.headers.update({"Authorization": f"Bearer {token}"})
    return api_session


def identity_store():
    """Return the identity store, synced with the server thread's writes.

    :returns: The plugin's identity store.
    """
    transaction.begin()
    return api.portal.get_tool("acl_users")[PLUGIN_ID].store


class TestLinkingASecondProvider:
    @pytest.fixture(autouse=True)
    def _setup(self, api_session, portal_url, dex_login, authenticated) -> None:
        self.api_session = api_session
        self.portal_url = portal_url
        self.dex_login = dex_login
        self.authenticated = authenticated

    def test_starts_from_identities(self):
        """An self.authenticated user asks to link, and gets an authorize URL."""
        response = self.authenticated.post(
            f"{self.portal_url}/@identities",
            json={"provider": "dex-second"},
            timeout=30,
        )

        assert response.status_code == 200
        assert response.json()["authorize_url"].startswith("http")

    def test_both_identities_resolve_to_one_userid(self):
        """Link provider B, and A and B are the same human."""
        started = self.authenticated.post(
            f"{self.portal_url}/@identities",
            json={"provider": "dex-second"},
            timeout=30,
        )
        query = self.dex_login(started.json()["authorize_url"])

        finished = self.authenticated.post(
            f"{self.portal_url}/@identity-callback",
            json={
                "provider": "dex-second",
                "code": query["code"],
                "state": query["state"],
            },
            timeout=30,
        )

        assert finished.status_code == 200
        store = identity_store()
        owners = list(store._by_userid)
        assert len(owners) == 1
        assert len(store.identities_for(owners[0])) == 2

    def test_listing_shows_both(self):
        """And the user can see both in @identities."""
        started = self.authenticated.post(
            f"{self.portal_url}/@identities",
            json={"provider": "dex-second"},
            timeout=30,
        )
        query = self.dex_login(started.json()["authorize_url"])
        self.authenticated.post(
            f"{self.portal_url}/@identity-callback",
            json={
                "provider": "dex-second",
                "code": query["code"],
                "state": query["state"],
            },
            timeout=30,
        )

        listing = self.authenticated.get(f"{self.portal_url}/@identities", timeout=30)

        assert sorted(i["provider"] for i in listing.json()["items"]) == [
            "dex",
            "dex-second",
        ]


class TestLinkingSecurity:
    @pytest.fixture(autouse=True)
    def _setup(self, api_session, portal_url, dex_login, authenticated) -> None:
        self.api_session = api_session
        self.portal_url = portal_url
        self.dex_login = dex_login
        self.authenticated = authenticated

    def test_another_session_cannot_complete_the_link(self):
        """The flow must be finished by the session that started it.

        The attacker here has the code, the state *and* the flow cookie, and
        is still refused, because they are not the user the attempt was
        started for. That is the property the ``link_for`` check buys.
        """
        started = self.authenticated.post(
            f"{self.portal_url}/@identities",
            json={"provider": "dex-second"},
            timeout=30,
        )
        query = self.dex_login(started.json()["authorize_url"])

        # Same cookies, no token: an anonymous browser holding the flow state.
        anonymous = requests.Session()
        anonymous.headers.update({"Accept": "application/json"})
        anonymous.cookies.update(self.authenticated.cookies)
        response = anonymous.post(
            f"{self.portal_url}/@identity-callback",
            json={
                "provider": "dex-second",
                "code": query["code"],
                "state": query["state"],
            },
            timeout=30,
        )

        assert response.status_code == 403
        assert response.json()["error"]["type"] == "Link refused"

    def test_callback_url_is_the_configured_one(self):
        """The linking flow uses the same registered redirect URI, so Dex
        does not have to know about a second route."""
        started = self.authenticated.post(
            f"{self.portal_url}/@identities",
            json={"provider": "dex-second"},
            timeout=30,
        )

        query = parse_qs(urlparse(started.json()["authorize_url"]).query)
        assert query["redirect_uri"] == [CALLBACK_URL]


class TestAnonymousLinking:
    """Starting a link needs a session, so this one never logs in."""

    @pytest.fixture(autouse=True)
    def _setup(self, api_session, portal_url) -> None:
        self.api_session = api_session
        self.portal_url = portal_url

    def test_anonymous_cannot_start_a_link(self):
        """A linking flow may not be started without a session."""
        response = self.api_session.post(
            f"{self.portal_url}/@identities",
            json={"provider": "dex-second"},
            timeout=30,
        )

        assert response.status_code == 401
