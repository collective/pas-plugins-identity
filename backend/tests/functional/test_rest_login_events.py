"""A password login through ``@login`` is a login of the person who logged in.

``on_logged_in`` mints and reconciles a local account's Profile, and relies on
``IUserLoggedInEvent`` naming that account. ``plone.restapi``'s ``@login`` does
not fire the event itself: it runs Plone's post-login work,
``portal_membership.loginUser()``, which names the security manager's user. That
is the right user only because the JWT plugin's ``extractCredentials`` reads the
``login`` and ``password`` from a JSON body, so the publisher has already
authenticated the request before the service runs.

Issue #113 reported the opposite, from a measuring harness that called the
service as ``Anonymous User``. A real request is never in that state, and these
pin the behaviour that proves it: through the real publisher, with the
``Content-Type`` Volto's API helper sends, which that extractor matches exactly.
"""

from plone import api
from Products.PluggableAuthService.interfaces.events import IUserLoggedInEvent
from zope.component import adapter
from zope.component import getGlobalSiteManager

import pytest
import requests
import transaction


USERNAME = "local"
PASSWORD = "s3cret-Passw0rd"


@pytest.fixture
def seen():
    """Record the id of every principal a login event names.

    Registered globally, which reaches the test server: it runs in this
    process.

    :returns: The list the ids accumulate in.
    """
    principals: list[str | None] = []

    @adapter(IUserLoggedInEvent)
    def record(event):
        principals.append(getattr(event.principal, "getId", lambda: None)())

    gsm = getGlobalSiteManager()
    gsm.registerHandler(record)
    yield principals
    gsm.unregisterHandler(record)


class TestAPasswordLogin:
    @pytest.fixture(autouse=True)
    def _setup(self, functional, seen) -> None:
        self.portal = functional["portal"]
        self.seen = seen
        with api.env.adopt_roles(["Manager"]):
            api.user.create(
                email="local@example.com", username=USERNAME, password=PASSWORD
            )
        transaction.commit()
        self.url = self.portal.absolute_url()

    def login(self) -> requests.Response:
        """Sign in the way Volto does.

        :returns: The response.
        """
        return requests.post(
            f"{self.url}/@login",
            json={"login": USERNAME, "password": PASSWORD},
            headers={"Accept": "application/json"},
            timeout=30,
        )

    def test_the_event_names_who_logged_in(self):
        response = self.login()

        assert response.status_code == 200, response.text
        assert self.seen == [USERNAME]

    def test_the_login_time_is_recorded(self):
        """Plone's own half of the same call: ``setLoginTimes`` asks the same
        security manager, and an anonymous one records nothing."""
        self.login()

        transaction.begin()
        member = api.user.get(username=USERNAME)
        assert member.getProperty("login_time").year() > 2000
