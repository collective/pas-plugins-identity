"""End to end: a real Dex login mints a real Profile.

Everything in ``test_first_login`` fires the events by hand, which is the
right way to test the subscriber and no way at all to prove the subscriber is
*wired*. This drives the whole thing: Dex issues a real authorization code
against a real end-user session, core authenticates it and fires the contract
event, and the subscriber -- which the plugin knows nothing about -- ends up
with a Profile the user can edit and complete.

The sequence the gate asks for, in one test: a fresh Dex user logs in, a
Profile exists and has been reconciled against what the site requires, the
user edits their own Profile, and ``@my-profile`` reflects it.

Dex sends both a name and an address, so the profile it mints is *complete*.
The incomplete half of the flow needs a provider that withholds something,
which cannot be arranged against this one; it is covered in
``test_completeness`` and ``test_first_login`` instead.
"""

from ..conftest import DEX_USER
from pas.plugins.identity.core.catalog import all_brains
from pas.plugins.identity.core.catalog import query_catalog
from plone import api

import pytest
import transaction


pytestmark = pytest.mark.docker


@pytest.fixture
def profile_portal(portal):
    """The functional portal.

    Applied on top of the flow fixture rather than from a layer of its own:
    the functional layer stacks a DemoStorage per test, so the commit below is
    rolled back afterwards and no other functional test sees the extra.

    :param portal: The portal with both Dex clients configured.
    :returns: The Plone site.
    """
    transaction.commit()
    return portal


def fresh(portal):
    """Start a new transaction so the test sees what the server committed.

    The WSGI server runs in its own thread with its own ZODB connection. Until
    the test process begins a new transaction it keeps reading the snapshot it
    opened before the request, and a Profile the login just created reads as
    "the subscriber never ran" -- which is the wrong bug to go looking for.

    :param portal: The Plone site.
    :returns: The Plone site, on a current view of the database.
    """
    transaction.begin()
    return portal


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


@pytest.fixture
def logged_in(api_session, profile_portal, portal_url, dex_login, dex_service):
    """Complete a real Dex login and return the session and userid.

    :param api_session: The JSON session.
    :param profile_portal: The portal with the extra installed.
    :param portal_url: The portal URL.
    :param dex_login: Helper driving Dex's own login form.
    :param dex_service: Ensures Dex is up.
    :returns: Tuple of the authenticated session and the canonical userid.
    """
    query = dex_login(start(api_session, portal_url))
    response = finish(api_session, portal_url, query)
    response.raise_for_status()

    token = response.json()["token"]
    api_session.headers.update({"Authorization": f"Bearer {token}"})

    fresh(profile_portal)
    brains = all_brains(query_catalog())
    assert brains, "the login did not mint a Profile"
    return api_session, brains[0].userid


class TestFirstLoginMintsAProfile:
    @pytest.fixture(autouse=True)
    def _setup(
        self, api_session, portal_url, profile_portal, logged_in, dex_login
    ) -> None:
        self.dex_login = dex_login
        self.api_session = api_session
        self.portal_url = portal_url
        self.profile_portal = profile_portal
        self.logged_in = logged_in

    def test_profile_exists(self):
        """Core fired the event; the extra acted on it."""
        _, userid = self.logged_in

        assert query_catalog().unrestrictedSearchResults(userid=userid)

    def test_the_login_is_recorded(self):
        """From Dex's own claims: it sends no username, so this is the email."""
        _, userid = self.logged_in
        brain = query_catalog().unrestrictedSearchResults(userid=userid)[0]

        assert brain.login == DEX_USER["email"]

    def test_it_arrives_complete(self):
        """Because Dex supplies everything this site requires.

        This asserted ``incomplete``, and had done since before there was a
        transition to leave that state with. ``cac5a34`` gave the workflow
        something that fires ``complete``, and from then on a Dex login --
        which sends both a name and an address -- produced a complete profile
        and this test was red. Nothing noticed: it is docker-marked, the
        suite it belongs to has never run in CI, and the two sessions since
        did not run it locally.

        What the flow proves is that reconciliation runs at first login, and
        that is what is asserted. A provider that withholds a field, which is
        the case the gate exists for, is covered where it can be arranged --
        ``test_completeness`` and ``test_first_login``.
        """
        _, userid = self.logged_in
        brain = query_catalog().unrestrictedSearchResults(userid=userid)[0]

        assert brain.review_state == "complete"

    def test_claims_from_dex_were_synced(self):
        """The real id_token's claims, not a fixture's."""
        _, userid = self.logged_in
        brain = query_catalog().unrestrictedSearchResults(userid=userid)[0]

        assert brain.email == DEX_USER["email"]

    def test_my_profile_reports_it(self):
        """Through the service Volto actually calls, which is what routes the
        browser after a login."""
        session, _ = self.logged_in

        body = session.get(f"{self.portal_url}/@my-profile", timeout=30).json()

        assert body["review_state"] == "complete"
        assert body["profile"]


class TestTheUserCompletesIt:
    @pytest.fixture(autouse=True)
    def _setup(
        self, api_session, portal_url, profile_portal, logged_in, dex_login
    ) -> None:
        self.dex_login = dex_login
        self.api_session = api_session
        self.portal_url = portal_url
        self.profile_portal = profile_portal
        self.logged_in = logged_in

    def test_user_may_edit_their_own_profile(self):
        """The self-Editor local role, over HTTP as the user themselves."""
        session, _ = self.logged_in
        url = session.get(f"{self.portal_url}/@my-profile", timeout=30).json()[
            "profile"
        ]

        response = session.patch(url, json={"fullname": "Erico Andrei"}, timeout=30)

        assert response.status_code in (200, 204)

    def test_the_edit_is_visible_to_pas(self):
        """An edit nobody can read back is not an edit."""
        session, userid = self.logged_in
        url = session.get(f"{self.portal_url}/@my-profile", timeout=30).json()[
            "profile"
        ]
        session.patch(url, json={"fullname": "Erico Andrei"}, timeout=30)

        fresh(self.profile_portal)
        assert api.user.get(userid=userid).getProperty("fullname") == "Erico Andrei"

    def test_transition_to_complete_is_reflected(self):
        """The last step of the gate's sequence."""
        session, _ = self.logged_in
        url = session.get(f"{self.portal_url}/@my-profile", timeout=30).json()[
            "profile"
        ]

        session.post(
            f"{url}/@workflow/complete", json={}, timeout=30
        ).raise_for_status()

        body = session.get(f"{self.portal_url}/@my-profile", timeout=30).json()
        assert body["review_state"] == "complete"

    def test_a_second_login_does_not_undo_the_edit(self, dex_login):
        """Against a real provider that keeps sending its own name."""
        session, userid = self.logged_in
        url = session.get(f"{self.portal_url}/@my-profile", timeout=30).json()[
            "profile"
        ]
        session.patch(url, json={"fullname": "Erico Andrei"}, timeout=30)

        finish(
            self.api_session,
            self.portal_url,
            self.dex_login(start(self.api_session, self.portal_url)),
        )

        fresh(self.profile_portal)
        assert api.user.get(userid=userid).getProperty("fullname") == "Erico Andrei"
