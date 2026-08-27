"""The hard gate: an incomplete profile is the only page its owner gets.

Every test here goes through the real publisher, because the gate *is* a
publisher subscriber and there is nothing to test about it otherwise. A unit
test of ``redirect_target`` would pass with the ZCML deleted.

Two of these matter more than the rest. ``test_a_manager_is_never_held`` and
``test_the_record_turns_it_off`` are the escapes: a required field nobody can
supply would otherwise leave every user in a loop, with the settings that
would undo it on the far side of the gate.
"""

from pas.plugins.identity import PACKAGE_NAME
from pas.plugins.identity.content.completeness import REQUIRED_FIELDS_RECORD
from pas.plugins.identity.content.container import get_container
from pas.plugins.identity.content.gate import ENFORCE_RECORD
from plone import api
from plone.app.testing import applyProfile
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from zope.lifecycleevent import modified

import pytest
import requests
import transaction


#: A user whose profile will be missing something.
USERID = "alice"
PASSWORD = "alice-secret-1"

#: Sent by a browser following a link, and by nothing else here.
BROWSER = {"Accept": "text/html,application/xhtml+xml"}

#: What Volto sends. plone.rest marks these ``IAPIRequest``.
API = {"Accept": "application/json"}


@pytest.fixture
def site(functional):
    """A site with the layer installed, a required field, and one user.

    ``location`` is required rather than ``email`` because ``api.user.create``
    insists on an address, and a profile that cannot be created is a different
    test.

    :param functional: The functional layer.
    :returns: ``(portal, url)``.
    """
    portal = functional["portal"]
    applyProfile(portal, f"{PACKAGE_NAME}.content:default")
    api.portal.set_registry_record(REQUIRED_FIELDS_RECORD, ("email", "location"))
    with api.env.adopt_roles(["Manager"]):
        # Installing the layer does not create the container -- where profiles
        # live is a registry setting a layered profile may still move, so the
        # first login makes it. Nothing has logged in here.
        get_container(create=True)
        api.user.create(username=USERID, email="alice@example.com", password=PASSWORD)
    transaction.commit()
    return portal, portal.absolute_url()


def get(url: str, auth=None, headers=None) -> requests.Response:
    """Fetch a URL without following redirects.

    Following them would turn every assertion below into "did we eventually
    reach something", which is not the question.

    :param url: The URL to fetch.
    :param auth: Credentials, or ``None`` for anonymous.
    :param headers: Request headers.
    :returns: The response.
    """
    return requests.get(
        url,
        auth=auth,
        headers=headers or BROWSER,
        allow_redirects=False,
        timeout=30,
    )


class TestTheGateHolds:
    @pytest.fixture(autouse=True)
    def _setup(self, site) -> None:
        self.portal, self.url = site
        self.user = (USERID, PASSWORD)

    def test_the_profile_is_incomplete_to_begin_with(self):
        """The premise. Without it every other test here passes vacuously."""
        profile = self.portal["identity-profiles"][USERID]

        assert api.content.get_state(obj=profile) == "incomplete"

    def test_a_page_is_answered_with_a_redirect(self):
        response = get(self.url, auth=self.user)

        assert response.status_code == 302

    def test_it_redirects_to_the_edit_form(self):
        response = get(self.url, auth=self.user)

        assert response.headers["Location"].endswith(f"/{USERID}/edit")

    def test_another_page_is_held_too(self):
        """A gate that only catches the front page is not a gate."""
        response = get(f"{self.url}/@@search", auth=self.user)

        assert response.status_code == 302


class TestWhatIsNotHeld:
    @pytest.fixture(autouse=True)
    def _setup(self, site) -> None:
        self.portal, self.url = site
        self.user = (USERID, PASSWORD)

    def test_the_profile_itself_is_reachable(self):
        """The target of the redirect. Gating it is a loop that no amount of
        correct configuration escapes."""
        response = get(f"{self.url}/identity-profiles/{USERID}/edit", auth=self.user)

        assert response.status_code != 302

    def test_signing_out_is_reachable(self):
        """Somebody who would rather leave than fill the form in may."""
        response = get(f"{self.url}/logout", auth=self.user)

        assert "/edit" not in response.headers.get("Location", "")

    def test_an_api_request_passes(self):
        """Volto talks to this site over plone.restapi, and the edit form is
        one of the things it fetches. Redirecting those would break the page
        the user is being sent to."""
        response = get(self.url, auth=self.user, headers=API)

        assert response.status_code == 200

    def test_a_stylesheet_is_not_a_navigation(self):
        """A gate on every request is a gate on every asset."""
        response = get(
            f"{self.url}/++plone++static/plone-compiled.css",
            auth=self.user,
            headers={"Accept": "text/css,*/*;q=0.1"},
        )

        assert response.status_code != 302

    def test_anonymous_is_not_held(self):
        """There is no profile to hold them for, and a redirect here would
        make the site unreadable to the public."""
        response = get(self.url)

        assert response.status_code == 200

    def test_a_complete_profile_is_not_held(self):
        profile = self.portal["identity-profiles"][USERID]
        with api.env.adopt_roles(["Manager"]):
            profile.location = "Oxford"
            modified(profile)
        transaction.commit()

        response = get(self.url, auth=self.user)

        assert response.status_code == 200


class TestTheEscapes:
    """The two things that stop a required field from locking the site."""

    @pytest.fixture(autouse=True)
    def _setup(self, site) -> None:
        self.portal, self.url = site
        self.user = (USERID, PASSWORD)

    def test_a_manager_is_never_held(self):
        """Somebody has to be able to reach the control panel that would undo
        a requirement nobody can satisfy, and it cannot be somebody who first
        has to get past the gate."""
        response = get(self.url, auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD))

        assert response.status_code == 200

    def test_a_manager_with_an_incomplete_profile_is_still_not_held(self):
        """The bypass is on the role, not on having no profile at all."""
        with api.env.adopt_roles(["Manager"]):
            api.user.grant_roles(username=USERID, roles=["Manager"])
        transaction.commit()

        response = get(self.url, auth=self.user)

        assert response.status_code == 200

    def test_the_record_turns_it_off(self):
        api.portal.set_registry_record(ENFORCE_RECORD, False)
        transaction.commit()

        response = get(self.url, auth=self.user)

        assert response.status_code == 200

    def test_it_is_on_by_default(self):
        """Shipping it off would make this the flow the package already had."""
        assert api.portal.get_registry_record(ENFORCE_RECORD) is True
