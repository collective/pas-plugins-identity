"""The sign-in endpoints answer on a site anonymous visitors cannot view.

Four services say "anonymous by design" in their own ZCML comments and were
all declared against ``zope2.View``, which is not that. A closed intranet
takes ``View`` away from ``Anonymous`` at the root, and every one of them
disappeared with it: the login page's provider list, the callback that
finishes a federated sign-in, and both halves of the magic link. The button
that lets a person sign in was served by an endpoint they had to be signed in
to reach, on exactly the kind of site most likely to want federated login.

``zope.Public`` is what says so, and it is not ``zope2.View`` with a friendlier
default. ``AccessControl.security.protectClass`` special-cases the literal
string and calls ``declareObjectPublic()``, so the class carries no role
requirement at all; anything else is looked up as a permission and inherited
from the root. ``plone.restapi`` declares its own ``@login`` the same way,
which is why local login kept working on the sites where this did not.

Through the real publisher on a real site. The registration is the entire
question, and a service constructed in a test answers it whatever the ZCML
says.
"""

from .. import close_the_site
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD

import pytest
import requests
import transaction


@pytest.fixture
def url(functional) -> str:
    """Return the portal URL, having committed the site.

    :param functional: The functional layer.
    :returns: The portal URL as the test server publishes it.
    """
    portal = functional["portal"]
    transaction.commit()
    return portal.absolute_url()


class TestTheProviderListing:
    """``@login-providers``: the data the login page is drawn from."""

    @pytest.fixture(autouse=True)
    def _setup(self, functional, url: str) -> None:
        self.portal = functional["portal"]
        self.url = url

    def get(self, path: str = "", auth=None) -> requests.Response:
        """Ask for the provider listing.

        :param path: Traversal below the endpoint, if any.
        :param auth: Credentials, or ``None`` to ask anonymously.
        :returns: The response.
        """
        return requests.get(
            f"{self.url}/@login-providers{path}",
            headers={"Accept": "application/json"},
            auth=auth,
            timeout=30,
        )

    def test_an_open_site_serves_it_anonymously(self):
        """The control, and it proves nothing on its own: this passed under
        the old permission too. It is here so that a failure below cannot be
        read as a listing that never worked."""
        assert self.get().status_code == 200

    def test_a_closed_site_still_serves_it_anonymously(self):
        """The one that matters. No ``View`` for ``Anonymous``, and the login
        page still gets its buttons."""
        close_the_site(self.portal)

        response = self.get()

        assert response.status_code == 200, response.text

    def test_a_closed_site_still_lists_the_providers(self):
        """A 200 carrying nothing would be the same outage in a nicer suit."""
        close_the_site(self.portal)

        assert "items" in self.get().json()

    def test_a_closed_site_still_starts_a_flow(self):
        """Traversal to one provider is the same registration, and it is the
        half that actually signs somebody in. A 404 for a provider that does
        not exist is the service answering on its own terms; a 401 would be
        the publisher refusing before it was asked."""
        close_the_site(self.portal)

        assert self.get("/nonexistent").status_code == 404

    def test_a_manager_is_unaffected(self):
        """Making an endpoint public takes nothing away from anybody."""
        close_the_site(self.portal)

        assert self.get(auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD)).status_code == 200


#: The other three, with the status each gives when it is reached and asked
#: nothing useful. Every one of them is the service's own answer, which is the
#: point: under ``zope2.View`` a closed site answered all three with 401,
#: before any of this code ran.
#:
#: ``@identity-callback`` refuses an empty body. Both magic-link halves report
#: that no email provider is configured, which is true of this site and is
#: :mod:`~pas.plugins.identity.core.services.magiclink.post`'s own 404.
REACHED = [
    ("@identity-callback", 400),
    ("@magic-link", 404),
    ("@magic-link-confirm", 404),
]


class TestTheOtherSignInEndpoints:
    """The callback and both magic-link halves, on the same closed site."""

    @pytest.fixture(autouse=True)
    def _setup(self, functional, url: str) -> None:
        self.portal = functional["portal"]
        self.url = url

    def post(self, name: str) -> requests.Response:
        """POST an empty document to one endpoint, anonymously.

        :param name: The endpoint name.
        :returns: The response.
        """
        return requests.post(
            f"{self.url}/{name}",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={},
            auth=None,
            timeout=30,
        )

    @pytest.mark.parametrize(("name", "status"), REACHED)
    def test_a_closed_site_still_reaches_it(self, name: str, status: int):
        """Reached and answered, rather than refused at the door."""
        close_the_site(self.portal)

        response = self.post(name)

        assert response.status_code != 401, response.text
        assert response.status_code == status, response.text

    @pytest.mark.parametrize(("name", "status"), REACHED)
    def test_an_open_site_answers_the_same_way(self, name: str, status: int):
        """The control for each: the answer is a property of the service, not
        of the permission map this test is changing."""
        assert self.post(name).status_code == status
