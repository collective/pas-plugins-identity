"""An identity provider does not release claims about an unfinished profile.

Found by Érico signing in to the demo's relying party with a GitHub account
that keeps its address private. He was never shown the profile form: the
callback navigates straight to the authorization URL, and every route a
federated sign-in touches -- ``/login``, the callback, ``/oauth-consent``, and
``@@oauth-authorize`` itself -- is on the gate's exemption list, for good
reasons that together add up to no enforcement at all. He completed the whole
federation with a profile that had no email, and the relying party received an
account with none either.

So the insistence lives where it belongs: the authorization endpoint refuses
to proceed until the profile carries what the site requires. The relying party
cannot enforce this and should not have to; the provider is the only party
that knows what it requires.

Asked through ``IProfileSupport`` rather than by importing the ``[content]``
layer, which the import-linter contract forbids -- so these tests also cover
the case that made the contract worth having: a site with the server layer and
without the content layer, where the utility is absent and nothing is
enforced.
"""

from pas.plugins.identity import PACKAGE_NAME
from pas.plugins.identity.content.completeness import REQUIRED_FIELDS_RECORD
from pas.plugins.identity.content.container import get_container
from pas.plugins.identity.content.gate import ENFORCE_RECORD
from pas.plugins.identity.server.clients import add_client
from plone import api
from plone.app.testing import applyProfile
from urllib.parse import parse_qs
from urllib.parse import urlparse

import pytest
import requests
import transaction


USERID = "alice"
PASSWORD = "alice-secret-1"
CLIENT_ID = "demo-rp"
REDIRECT = "https://app.example.org/cb"

BROWSER = {"Accept": "text/html"}


def authorize_url(base: str, **extra) -> str:
    """Build an authorization request.

    :param base: The portal URL.
    :param extra: Parameters to add or override.
    :returns: The URL.
    """
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT,
        "scope": "openid email",
        "state": "xyz",
        # A public client must use PKCE, and that check runs before this one:
        # a malformed request is still answered as a malformed request rather
        # than being sent to a profile form.
        "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
        "code_challenge_method": "S256",
        **extra,
    }
    query = "&".join(
        f"{k}={requests.utils.quote(str(v), safe='')}" for k, v in params.items()
    )
    return f"{base}/@@oauth-authorize?{query}"


@pytest.fixture
def site(functional):
    """A provider with both layers, a client, and a user missing a field.

    ``location`` is required rather than ``email`` because ``api.user.create``
    insists on an address; a profile that cannot be created is a different
    test.

    :param functional: The functional layer.
    :returns: ``(portal, url)``.
    """
    portal = functional["portal"]
    applyProfile(portal, f"{PACKAGE_NAME}.content:default")
    applyProfile(portal, f"{PACKAGE_NAME}.server:default")
    api.portal.set_registry_record(REQUIRED_FIELDS_RECORD, ("email", "location"))
    with api.env.adopt_roles(["Manager"]):
        get_container(create=True)
        api.user.create(
            username=USERID,
            email="alice@example.com",
            password=PASSWORD,
            properties={"fullname": "Alice Liddell"},
        )
        add_client(
            CLIENT_ID,
            title="Demo",
            redirect_uris=[REDIRECT],
            grant_types=["authorization_code"],
            scope="openid email",
            public=True,
        )
    transaction.commit()
    return portal, portal.absolute_url()


def get(url: str, auth=None) -> requests.Response:
    """Fetch a URL without following redirects.

    :param url: The URL.
    :param auth: Credentials.
    :returns: The response.
    """
    return requests.get(
        url, auth=auth, headers=BROWSER, allow_redirects=False, timeout=30
    )


class TestAnUnfinishedProfile:
    @pytest.fixture(autouse=True)
    def _setup(self, site) -> None:
        self.portal, self.url = site
        self.user = (USERID, PASSWORD)

    def test_the_profile_is_incomplete_to_begin_with(self):
        """The premise, without which everything below passes vacuously."""
        profile = self.portal["identity-profiles"][USERID]

        assert api.content.get_state(obj=profile) == "incomplete"

    def test_the_request_is_paused_at_the_profile(self):
        response = get(authorize_url(self.url), auth=self.user)
        location = response.headers.get("Location", "")

        assert response.status_code == 302
        assert f"/identity-profiles/{USERID}/edit" in location

    def test_the_client_is_told_nothing_yet(self):
        """Paused, not refused. The client hears from us when the browser
        comes back, exactly as it does while the user signs in."""
        response = get(authorize_url(self.url), auth=self.user)

        assert not response.headers.get("Location", "").startswith(REDIRECT)

    def test_the_whole_request_travels_with_them(self):
        """A parameter dropped here is a different request on the way back,
        and PKCE turns on exactly that difference."""
        response = get(authorize_url(self.url), auth=self.user)
        location = response.headers["Location"]
        carried = parse_qs(urlparse(location).query)["return_url"][0]
        params = parse_qs(urlparse(carried).query)

        assert params["client_id"] == [CLIENT_ID]
        assert params["redirect_uri"] == [REDIRECT]
        assert params["state"] == ["xyz"]
        assert params["code_challenge"] == [
            "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
        ]

    def test_prompt_none_is_refused_to_the_client_instead(self):
        """``prompt=none`` says the user must not be interacted with, and
        sending them to a form is interaction. The specification has a code
        for exactly this."""
        response = get(authorize_url(self.url, prompt="none"), auth=self.user)
        location = response.headers["Location"]

        assert location.startswith(REDIRECT)
        assert parse_qs(urlparse(location).query)["error"] == ["interaction_required"]


class TestAFinishedProfile:
    @pytest.fixture(autouse=True)
    def _setup(self, site) -> None:
        self.portal, self.url = site
        self.user = (USERID, PASSWORD)
        profile = self.portal["identity-profiles"][USERID]
        with api.env.adopt_roles(["Manager"]):
            profile.location = "Oxford"
            from zope.lifecycleevent import modified

            modified(profile)
        transaction.commit()

    def test_it_reaches_consent_as_before(self):
        """The control. A gate that never lets anybody through would pass
        every test in the class above."""
        response = get(authorize_url(self.url), auth=self.user)
        location = response.headers.get("Location", "")

        assert "/edit" not in location


class TestWhenNothingIsBeingEnforced:
    @pytest.fixture(autouse=True)
    def _setup(self, site) -> None:
        self.portal, self.url = site
        self.user = (USERID, PASSWORD)
        api.portal.set_registry_record(ENFORCE_RECORD, False)
        transaction.commit()

    def test_the_authorization_proceeds(self):
        """A site that turned the gate off has said an incomplete profile is
        a suggestion. An endpoint that refused anyway would not be one."""
        response = get(authorize_url(self.url), auth=self.user)

        assert "/edit" not in response.headers.get("Location", "")
