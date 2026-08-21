"""The Gate 1 check: a browser-less code flow against a real provider (C2).

Everything here is real. Dex runs in Docker, issues a real authorization code
against a real end-user session, signs a real ``id_token``, and the test ends
holding a ``jwt_auth`` token that fetches ``@site`` as the authenticated user.
Nothing is stubbed -- which is the whole point, because every other test in
this suite stubs the provider's two network calls.
"""

from ..conftest import DEX_USER
from pas.plugins.identity.core.pas import PLUGIN_ID
from plone import api

import pytest
import transaction


pytestmark = pytest.mark.docker


def start(api_session, portal_url: str) -> str:
    """Ask the backend where to send the browser.

    :param api_session: The JSON session, which keeps the flow cookie.
    :param portal_url: The portal URL.
    :returns: The authorize URL.
    """
    response = api_session.get(f"{portal_url}/@login-providers/dex", timeout=30)
    response.raise_for_status()
    return response.json()["authorize_url"]


def finish(api_session, portal_url: str, query: dict):
    """POST the provider's code and state back to the backend.

    :param api_session: The JSON session, carrying the flow cookie.
    :param portal_url: The portal URL.
    :param query: The callback query parameters.
    :returns: The HTTP response.
    """
    return api_session.post(
        f"{portal_url}/@identity-callback",
        json={"provider": "dex", "code": query["code"], "state": query["state"]},
        timeout=30,
    )


class TestCodeFlow:
    def test_providers_are_listed(self, api_session, portal_url):
        """The login page offers the providers that are actually configured."""
        response = api_session.get(f"{portal_url}/@login-providers", timeout=30)

        assert [item["id"] for item in response.json()["items"]] == [
            "dex",
            "dex-second",
        ]

    def test_authorize_url_points_at_dex(self, api_session, portal_url, dex_service):
        """The authorize endpoint comes from Dex's own discovery document."""
        assert start(api_session, portal_url).startswith(f"{dex_service}/auth")

    def test_full_round_trip_yields_a_token(self, api_session, portal_url, dex_login):
        """Fetch providers, follow the redirect, log in at Dex, come back."""
        query = dex_login(start(api_session, portal_url))

        response = finish(api_session, portal_url, query)

        assert response.status_code == 200
        assert response.json()["token"]

    def test_token_authenticates_against_site(self, api_session, portal_url, dex_login):
        """The Gate 1 check proper: the token GETs @site as the user."""
        query = dex_login(start(api_session, portal_url))
        token = finish(api_session, portal_url, query).json()["token"]

        import requests

        response = requests.get(
            f"{portal_url}/@site",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
            },
            timeout=30,
        )

        assert response.status_code == 200

    def test_identity_is_persisted_with_a_uuid_userid(
        self, api_session, portal_url, dex_login, portal
    ):
        """D10/I1 -- the userid is minted, never derived from Dex's subject."""
        query = dex_login(start(api_session, portal_url))
        finish(api_session, portal_url, query)

        store = identity_store()
        owners = userids(store)

        assert len(owners) == 1
        userid = owners[0]
        assert len(userid) == 32
        assert set(userid) <= set("0123456789abcdef")
        # The subject Dex issued must not be recoverable from the userid.
        subject = store.identities_for(userid)[0].subject
        assert subject and subject not in userid

    def test_claims_come_from_dex(self, api_session, portal_url, dex_login, portal):
        """The stored claims are the ones the provider actually asserted."""
        query = dex_login(start(api_session, portal_url))
        finish(api_session, portal_url, query)

        store = identity_store()
        userid = next(iter(userids(store)))
        record = store.identities_for(userid)[0]
        assert record.claims["email"] == DEX_USER["email"]
        assert record.claims["email_verified"] is True

    def test_second_login_is_the_same_user(
        self, api_session, portal_url, dex_login, portal
    ):
        """A returning human keeps their userid, and gains no second account."""
        finish(api_session, portal_url, dex_login(start(api_session, portal_url)))
        first = set(userids(identity_store()))

        finish(api_session, portal_url, dex_login(start(api_session, portal_url)))

        assert set(userids(identity_store())) == first
        assert len(first) == 1


class TestS1NegativesAgainstDex:
    """The refusals, against codes a real provider really issued."""

    def test_replayed_code_is_refused(self, api_session, portal_url, dex_login):
        """S1 -- the attempt is single-use even with a genuine code."""
        query = dex_login(start(api_session, portal_url))
        assert finish(api_session, portal_url, query).status_code == 200

        assert finish(api_session, portal_url, query).status_code == 401

    def test_tampered_state_is_refused(self, api_session, portal_url, dex_login):
        """S1 -- the state has to be the one this session started with."""
        query = dex_login(start(api_session, portal_url))
        query["state"] = "not-the-state-we-issued"

        assert finish(api_session, portal_url, query).status_code == 401

    def test_code_without_the_flow_cookie_is_refused(
        self, api_session, portal_url, dex_login
    ):
        """S1 -- the callback is bound to the browser that started the flow,
        so a genuine code presented by anyone else is worthless."""
        query = dex_login(start(api_session, portal_url))
        api_session.cookies.clear()

        assert finish(api_session, portal_url, query).status_code == 401


def identity_store():
    """Return the identity store, synced with the server thread's writes.

    The WSGI server runs on its own ZODB connection, so the test process does
    not see what a request committed until its own connection is refreshed --
    without this the store reads as empty and the test looks like a failure to
    persist rather than a failure to sync.

    :returns: The plugin's identity store.
    """
    transaction.begin()
    return api.portal.get_tool("acl_users")[PLUGIN_ID].store


def userids(store) -> list[str]:
    """Return every userid the store knows about.

    :param store: The identity store.
    :returns: The userids.
    """
    return list(store._by_userid)
