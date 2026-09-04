"""The scopes vocabulary is actually reachable over ``@vocabularies``.

The test next door asserts the utility is registered and lists the right
terms, which is precise and proves nothing about whether a browser can reach
it. The client panel's scope field is a ``Choice`` over a *named* vocabulary,
which ``plone.restapi`` serializes as a URL rather than as inline terms -- so
unlike ``grant_types``, whose terms travel with the schema, this one costs a
request. The failure mode when that request does not resolve is not an error:
it is an empty picker on a form that otherwise looks fine, and an operator
concluding this server supports no scopes.

So this goes through the real publisher.
"""

from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD

import pytest
import requests
import transaction


#: The vocabulary the client panel reads.
SERVED = "pas.plugins.identity.Scopes"


@pytest.fixture
def url(functional) -> str:
    """Return the portal URL as served by the test WSGI server.

    :param functional: The functional layer.
    :returns: The URL.
    """
    portal = functional["portal"]
    transaction.commit()
    return portal.absolute_url()


class TestTheScopesVocabularyIsPublished:
    @pytest.fixture(autouse=True)
    def _setup(self, url: str) -> None:
        self.url = url

    def get(self, anonymous: bool = False) -> requests.Response:
        """Fetch the vocabulary through ``@vocabularies``.

        :param anonymous: Whether to omit credentials.
        :returns: The response.
        """
        return requests.get(
            f"{self.url}/@vocabularies/{SERVED}",
            headers={"Accept": "application/json"},
            auth=None if anonymous else (SITE_OWNER_NAME, SITE_OWNER_PASSWORD),
            timeout=30,
        )

    def test_it_resolves(self):
        response = self.get()

        assert response.status_code == 200
        assert response.json()["@id"].endswith(f"@vocabularies/{SERVED}")

    def test_it_answers_with_the_advertised_scopes(self):
        """The same four the discovery document publishes, which is the whole
        point of computing them in one place."""
        tokens = [item["token"] for item in self.get().json()["items"]]

        assert tokens == ["openid", "address", "email", "profile"]

    def test_it_is_served_without_the_server_profile(self):
        """The utility is registered in ZCML rather than by the profile, and
        this layer has never applied ``pas.plugins.identity.server:default``.
        A panel that could not populate its picker until the server was
        switched on would be a chicken-and-egg on the page that switches it
        on."""
        assert self.get().status_code == 200

    def test_it_is_served_anonymously(self):
        """Deliberately, unlike the two in ``core``: those describe the shape
        of the site's user records and are protected in
        ``plone.app.content.browser.vocabulary.PERMISSIONS``. This one is the
        same list the discovery document publishes to the whole internet, so
        protecting it would guard nothing while making the panel's picker
        depend on who is looking."""
        assert self.get(anonymous=True).status_code == 200
