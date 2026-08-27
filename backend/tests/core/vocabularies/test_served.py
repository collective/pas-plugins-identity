"""Functional tests that the vocabularies are actually served.

Both vocabulary tests next door assert that the utility is registered and
that it lists the right terms, which is precise and proves nothing about
whether a browser can reach it. The control panel's two mapping widgets read
these by name through ``@vocabularies``, and the failure mode when that does
not resolve is not an error: it is an empty picker, on a form that otherwise
looks fine.

So these go through the real publisher.
"""

from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD

import pytest
import requests
import transaction


#: The vocabularies the provider form reads, and what each one is a picker
#: for. Parametrized rather than written twice: the wiring is identical and
#: the second one was added for the group map.
SERVED = [
    "pas.plugins.identity.UserFields",
    "pas.plugins.identity.Groups",
]


@pytest.fixture
def url(functional) -> str:
    """Return the portal URL as served by the test WSGI server.

    :param functional: The functional layer.
    :returns: The URL.
    """
    portal = functional["portal"]
    transaction.commit()
    return portal.absolute_url()


class TestVocabulariesArePublished:
    @pytest.fixture(autouse=True)
    def _setup(self, url: str) -> None:
        self.url = url

    def get(self, name: str, anonymous: bool = False) -> requests.Response:
        """Fetch one vocabulary through ``@vocabularies``.

        :param name: The vocabulary name.
        :param anonymous: Whether to omit credentials.
        :returns: The response.
        """
        return requests.get(
            f"{self.url}/@vocabularies/{name}",
            headers={"Accept": "application/json"},
            auth=None if anonymous else (SITE_OWNER_NAME, SITE_OWNER_PASSWORD),
            timeout=30,
        )

    @pytest.mark.parametrize("name", SERVED)
    def test_it_resolves(self, name: str):
        """A name that does not resolve gives the widget an empty picker
        rather than an error, which is why this is worth a test."""
        response = self.get(name)

        assert response.status_code == 200
        assert response.json()["@id"].endswith(f"@vocabularies/{name}")

    @pytest.mark.parametrize("name", SERVED)
    def test_it_answers_with_terms(self, name: str):
        """Both have terms on a bare site: Plone ships member fields, and it
        ships groups."""
        items = self.get(name).json()["items"]

        assert items
        assert {"title", "token"} <= set(items[0])

    def test_the_groups_vocabulary_lists_a_real_group(self):
        """`Administrators` exists on every Plone site, so this does not need
        a group of its own to be meaningful."""
        tokens = [item["token"] for item in self.get(SERVED[1]).json()["items"]]

        assert "Administrators" in tokens

    def test_the_groups_vocabulary_omits_the_virtual_group(self):
        """Nobody is explicitly a member of `AuthenticatedUsers`, so mapping a
        provider group onto it would store a membership that means nothing --
        while granting everything it grants to everyone who signs in."""
        tokens = [item["token"] for item in self.get(SERVED[1]).json()["items"]]

        assert "AuthenticatedUsers" not in tokens

    @pytest.mark.parametrize("name", SERVED)
    def test_it_is_not_served_anonymously(self, name: str):
        """Both describe the shape of the site's user records, and `Groups`
        lists every group by id and title.

        `plone.restapi` serves a vocabulary under `zope2.View` unless it is
        named in `plone.app.content.browser.vocabulary.PERMISSIONS`, so this
        is not the default and would silently stop being true if the
        registration went away.
        """
        assert self.get(name, anonymous=True).status_code == 401
