"""Functional tests that the services are actually published.

Everything else about these services is tested by constructing them directly,
which is fast and precise but proves nothing about the ZCML. These tests go
through the real publisher: they catch a wrong ``name``, a missing browser
layer, a permission that refuses anonymous, and a method mismatch -- none of
which a direct call would notice.
"""

from . import CALLBACK_URL
from . import DEX_PROVIDER
from pas.plugins.identity.core.catalog import GROUP_PORTAL_TYPE
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.container import get_container
from pas.plugins.identity.core.container import GROUP
from pas.plugins.identity.core.controlpanel import CALLBACK_URL_RECORD
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from plone import api
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.namedfile.file import NamedBlobImage

import pytest
import requests
import transaction


#: The Profile the principal services answer about.
USERID = "alice"

#: The smallest valid PNG, so a test never carries a binary fixture file.
PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00"
    b"\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\n"
    b"IDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00"
    b"\x00IEND\xaeB`\x82"
)


@pytest.fixture
def site(functional):
    """Return the portal from the functional layer, with a provider set up."""
    portal = functional["portal"]
    set_providers([ProviderConfig.deserialize(DEX_PROVIDER)])
    api.portal.set_registry_record(CALLBACK_URL_RECORD, CALLBACK_URL)
    transaction.commit()
    return portal


@pytest.fixture
def url(site) -> str:
    """Return the portal URL as served by the test WSGI server.

    :param site: The portal.
    :returns: The URL.
    """
    return site.absolute_url()


class TestPublished:
    @pytest.fixture(autouse=True)
    def _setup(self, url: str) -> None:
        self.url = url

    def test_listing_is_reachable_anonymously(self):
        """The login page is rendered before anyone has logged in."""
        response = requests.get(
            f"{self.url}/@login-providers",
            headers={"Accept": "application/json"},
            timeout=30,
        )

        assert response.status_code == 200
        assert [item["id"] for item in response.json()["items"]] == ["dex"]

    def test_listing_is_json(self):
        """It is a REST service, not a page."""
        response = requests.get(
            f"{self.url}/@login-providers",
            headers={"Accept": "application/json"},
            timeout=30,
        )

        assert response.headers["Content-Type"].startswith("application/json")

    def test_provider_segment_is_traversed(self):
        """``@login-providers/<id>`` reaches the start branch rather than
        404ing on the extra path segment."""
        response = requests.get(
            f"{self.url}/@login-providers/nope",
            headers={"Accept": "application/json"},
            timeout=30,
        )

        assert response.status_code == 404
        assert response.json()["error"]["type"] == "Unknown provider"

    def test_callback_is_reachable_anonymously(self):
        """Nobody is logged in yet: that is the point of the callback."""
        response = requests.post(
            f"{self.url}/@identity-callback",
            headers={"Accept": "application/json"},
            json={"provider": "dex", "code": "c", "state": "nope"},
            timeout=30,
        )

        assert response.status_code == 401
        assert response.json()["error"]["type"] == "Authentication failed"

    def test_callback_validates_its_body(self):
        """And it is really our service answering, not a generic error page."""
        response = requests.post(
            f"{self.url}/@identity-callback",
            headers={"Accept": "application/json"},
            json={},
            timeout=30,
        )

        assert response.status_code == 400
        assert response.json()["error"]["type"] == "Missing parameters"

    def test_callback_rejects_get(self):
        """Registered for POST only; a GET must not fall through to the
        listing service or to a view."""
        response = requests.get(
            f"{self.url}/@identity-callback",
            headers={"Accept": "application/json"},
            timeout=30,
        )

        assert response.status_code in (404, 405)

    def test_identities_is_reachable(self):
        """``@identities`` is published, and refuses anonymous with JSON
        rather than bouncing to a login form."""
        response = requests.get(
            f"{self.url}/@identities",
            headers={"Accept": "application/json"},
            timeout=30,
        )

        assert response.status_code == 401
        assert response.json()["error"]["type"] == "Not authenticated"

    def test_identities_accepts_post(self):
        """The POST factory is registered under the same name."""
        response = requests.post(
            f"{self.url}/@identities",
            headers={"Accept": "application/json"},
            json={"provider": "dex"},
            timeout=30,
        )

        assert response.status_code == 401

    def test_identities_accepts_delete_with_two_segments(self):
        """DELETE traverses ``<provider>/<subject>`` rather than 404ing on
        the extra path segments."""
        response = requests.delete(
            f"{self.url}/@identities/dex/some-subject",
            headers={"Accept": "application/json"},
            timeout=30,
        )

        assert response.status_code == 401
        assert response.json()["error"]["type"] == "Not authenticated"

    def test_audit_log_is_reachable(self):
        """``@audit-log`` is published and refuses anonymous with JSON."""
        response = requests.get(
            f"{self.url}/@audit-log",
            headers={"Accept": "application/json"},
            timeout=30,
        )

        assert response.status_code == 401
        assert response.json()["error"]["type"] == "Not authenticated"

    def test_magic_link_endpoints_are_reachable(self):
        """Both halves of the magic-link flow are published for POST."""
        send = requests.post(
            f"{self.url}/@magic-link",
            headers={"Accept": "application/json"},
            json={},
            timeout=30,
        )
        confirm = requests.post(
            f"{self.url}/@magic-link-confirm",
            headers={"Accept": "application/json"},
            json={},
            timeout=30,
        )

        # No email provider is configured in this fixture, so both answer 404
        # from our own service rather than from the publisher.
        for response in (send, confirm):
            assert response.status_code == 404
            assert response.json()["error"]["type"] == "Unknown provider"

    def test_control_panel_endpoints_are_published(self):
        """Both control-panel reads are registered, and refuse anonymous with
        JSON rather than a login form."""
        for name in ("@identity-drivers", "@identity-providers"):
            response = requests.get(
                f"{self.url}/{name}",
                headers={"Accept": "application/json"},
                timeout=30,
            )
            assert response.status_code == 401, name
            assert response.json()["error"]["type"] == "Not authenticated"

    def test_provider_write_verbs_are_published(self):
        """POST, PATCH and DELETE all resolve to our services."""
        headers = {"Accept": "application/json"}
        assert (
            requests.post(
                f"{self.url}/@identity-providers", headers=headers, json={}, timeout=30
            ).status_code
            == 401
        )
        assert (
            requests.patch(
                f"{self.url}/@identity-providers/dex",
                headers=headers,
                json={},
                timeout=30,
            ).status_code
            == 401
        )
        assert (
            requests.delete(
                f"{self.url}/@identity-providers/dex", headers=headers, timeout=30
            ).status_code
            == 401
        )

    def test_test_connection_action_traverses(self):
        """``<id>/test-connection`` reaches the POST service rather than
        404ing on the extra segments."""
        response = requests.post(
            f"{self.url}/@identity-providers/dex/test-connection",
            headers={"Accept": "application/json"},
            json={},
            timeout=30,
        )

        assert response.status_code == 401
        assert response.json()["error"]["type"] == "Not authenticated"


@pytest.fixture
def principals(site):
    """Create one Profile and one Group for the principal services to answer about.

    The three services below read principals rather than configuration, so
    unlike the rest of this module they need something to read. The container
    is created here the way a first login would: ``tests/core/conftest.py``
    does it for the modules that use a ``portal`` fixture, and this one runs
    on the functional layer.

    :param site: The Plone site.
    :returns: The Profile's userid.
    """
    with api.env.adopt_roles(["Manager"]):
        container = get_container(create=True)
        api.content.create(
            container=container,
            type=PROFILE_PORTAL_TYPE,
            id=USERID,
            userid=USERID,
            login=f"{USERID}@example.org",
            fullname="Alice Example",
            image=NamedBlobImage(data=PNG, contentType="image/png", filename="me.png"),
        )
        api.content.create(
            container=get_container(create=True, kind=GROUP),
            type=GROUP_PORTAL_TYPE,
            id="editors",
            group_id="editors",
            title="Editors",
        )
    transaction.commit()
    return USERID


class TestThePrincipalServicesArePublished:
    """``@group-members``, ``@portrait`` and ``@user-account``.

    These three were the gap this class was written to close: each is
    thoroughly tested by constructing the service directly, and until now no
    test had ever reached one through the publisher. A direct call cannot see
    a wrong ``name``, a missing browser layer, or a traversal that drops the
    path segment carrying the principal's id -- and every one of these three
    services is addressed *by* that segment.

    ``@portrait`` is the one that most needed it. The ``[server]`` layer
    publishes its URL as the OIDC ``picture`` claim, so the caller is a
    relying party with no Plone session at all.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, url: str, principals: str) -> None:
        self.url = url
        self.userid = principals
        self.headers = {"Accept": "application/json"}
        self.admin = (SITE_OWNER_NAME, SITE_OWNER_PASSWORD)

    def test_portrait_is_served_to_a_relying_party(self):
        """No session and no credentials, because an OIDC client fetching a
        picture claim has neither. A 404 here means the claim this package
        publishes points at nothing."""
        response = requests.get(
            f"{self.url}/@portrait/{self.userid}", headers=self.headers, timeout=30
        )

        assert response.status_code == 200
        assert response.content == PNG

    def test_portrait_is_served_as_the_image_it_is(self):
        """Not as JSON. A relying party puts this URL in an ``img`` tag."""
        response = requests.get(
            f"{self.url}/@portrait/{self.userid}", headers=self.headers, timeout=30
        )

        assert response.headers["Content-Type"].startswith("image/png")

    def test_portrait_traverses_the_userid_segment(self):
        """The id is a path segment rather than a query parameter, so a
        service registered without traversal would answer the same thing
        whatever came after the slash."""
        response = requests.get(
            f"{self.url}/@portrait/nobody-at-all", headers=self.headers, timeout=30
        )

        assert response.status_code == 404

    def test_user_account_is_published(self):
        """Reached as a manager, which is what the service asks for."""
        response = requests.get(
            f"{self.url}/@user-account/{self.userid}",
            headers=self.headers,
            auth=self.admin,
            timeout=30,
        )

        assert response.status_code == 200
        assert response.json()["userid"] == self.userid

    def test_user_account_refuses_anonymous_as_json(self):
        """The permission is ``zope2.View`` and the real check is inside the
        service, precisely so an anonymous caller gets a JSON body instead of
        a login form. That only holds if the service is reached at all."""
        response = requests.get(
            f"{self.url}/@user-account/{self.userid}", headers=self.headers, timeout=30
        )

        assert response.status_code == 401
        assert response.headers["Content-Type"].startswith("application/json")

    def test_group_members_is_published(self):
        response = requests.get(
            f"{self.url}/@group-members/editors",
            headers=self.headers,
            auth=self.admin,
            timeout=30,
        )

        assert response.status_code == 200
        assert "items" in response.json()

    def test_group_members_refuses_anonymous_as_json(self):
        """Same shape as ``@user-account``: authenticated-only, refused in
        the service rather than by the publisher."""
        response = requests.get(
            f"{self.url}/@group-members/editors", headers=self.headers, timeout=30
        )

        assert response.status_code == 401
        assert response.headers["Content-Type"].startswith("application/json")
