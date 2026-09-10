"""``my-profile`` as a component on a content request.

The gate asks this question on every navigation, and a navigation to a content
route is already a content request. What is asserted here is the mechanism
rather than the answer -- ``test_myprofile.py`` covers what the body says.

Two of these are about traps rather than features. The ``@id`` has to be the
site's, because the endpoint exists nowhere else; and the component has to be
absent for an anonymous caller, because Volto's ``apiExpanders`` cannot be told
to skip one and will ask on every page of a public site.
"""

from pas.plugins.identity.core.services.myprofile import profile_state
from plone import api
from plone.app.testing import logout
from plone.app.testing import TEST_USER_ID
from plone.restapi.interfaces import IExpandableElement
from plone.restapi.interfaces import ISerializeToJson
from zope.component import getAdapters
from zope.component import getMultiAdapter

import pytest


@pytest.fixture
def page(portal):
    """A piece of content to make the request against.

    Not the site root: the whole point of the component is that it rides on a
    request for some page, and a test that only ever asked the root could not
    catch an ``@id`` built from the wrong context.

    :param portal: The Plone site.
    :returns: A Document.
    """
    with api.env.adopt_roles(["Manager"]):
        return api.content.create(
            container=portal, type="Document", id="a-page", title="A page"
        )


class TestTheRegistration:
    """That the component is reached at all, not merely that it works."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, page) -> None:
        self.portal = portal
        self.request = request_
        self.page = page

    def names(self) -> list[str]:
        """Return the component names registered for this content.

        :returns: Every expandable element's name.
        """
        return [
            name
            for name, _component in getAdapters(
                (self.page, self.request), IExpandableElement
            )
        ]

    def test_it_is_registered_for_content(self):
        """Constructing the class proves nothing about whether a content
        request ever finds it."""
        assert "my-profile" in self.names()

    def test_it_reaches_a_serialized_page(self):
        """The end of the line: what Volto actually receives."""
        body = getMultiAdapter((self.page, self.request), ISerializeToJson)()

        assert "my-profile" in body["@components"]


class TestOnAContentRequest:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, page) -> None:
        self.portal = portal
        self.request = request_
        self.page = page

    def component(self) -> dict:
        """Serialize the page and return the component.

        :returns: The ``my-profile`` component.
        """
        body = getMultiAdapter((self.page, self.request), ISerializeToJson)()
        return body["@components"]["my-profile"]

    def test_unexpanded_it_costs_a_url(self):
        """The contract every other component follows."""
        component = self.component()

        assert component["@id"].endswith("/@my-profile")
        assert "review_state" not in component

    def test_the_url_is_the_site_s_own(self):
        """The trap. The endpoint is registered for the site root, so an
        ``@id`` built from the page would be a 404 on every page but the front
        one -- and it would look right in a payload."""
        assert self.component()["@id"] == f"{self.portal.absolute_url()}/@my-profile"

    def test_expanded_it_carries_the_answer(self):
        self.request.form["expand"] = "my-profile"

        component = self.component()

        assert component["userid"] == TEST_USER_ID
        assert "review_state" in component
        assert "missing" in component
        assert "emails" in component

    def test_the_expansion_is_the_endpoint_s_own_answer(self):
        """Two renderings of one question must not be able to differ."""
        self.request.form["expand"] = "my-profile"

        assert self.component() == profile_state(
            TEST_USER_ID, self.portal.absolute_url()
        )


class TestAnonymous:
    """The component is absent, not an ``@id``.

    Volto sends ``?expand=my-profile`` on anonymous content requests too --
    ``apiExpanders`` has no per-entry way to say authenticated-only. So this is
    what keeps a public site's payload the same as it was before the component
    existed, and keeps an anonymous visitor from being handed a URL that can
    only answer 401.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, page) -> None:
        self.portal = portal
        self.request = request_
        self.page = page

    def body(self) -> dict:
        """Serialize the page as an anonymous caller would receive it.

        :returns: The serialized content.
        """
        logout()
        return getMultiAdapter((self.page, self.request), ISerializeToJson)()

    def test_the_component_is_absent(self):
        assert "my-profile" not in self.body()["@components"]

    def test_it_stays_absent_when_asked_for(self):
        """Asking is exactly what Volto does, on every page."""
        self.request.form["expand"] = "my-profile"

        assert "my-profile" not in self.body()["@components"]

    def test_the_rest_of_the_page_is_unaffected(self):
        """Absent means absent from one key, not a broken serialization."""
        body = self.body()

        assert body["@id"].endswith("/a-page")
        assert "@components" in body
