"""Functional tests that the services are actually published.

Everything else about these services is tested by constructing them directly,
which is fast and precise but proves nothing about the ZCML. These tests go
through the real publisher: they catch a wrong ``name``, a missing browser
layer, a permission that refuses anonymous, and a method mismatch -- none of
which a direct call would notice.
"""

from . import CALLBACK_URL
from . import DEX_PROVIDER
from pas.plugins.identity.core.controlpanel import CALLBACK_URL_RECORD
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from plone import api

import pytest
import requests
import transaction


@pytest.fixture()
def site(functional):
    """Return the portal from the functional layer, with a provider set up."""
    portal = functional["portal"]
    set_providers([ProviderConfig.deserialize(DEX_PROVIDER)])
    api.portal.set_registry_record(CALLBACK_URL_RECORD, CALLBACK_URL)
    transaction.commit()
    return portal


@pytest.fixture()
def url(site) -> str:
    """Return the portal URL as served by the test WSGI server."""
    return site.absolute_url()


class TestPublished:
    def test_listing_is_reachable_anonymously(self, url: str):
        """The login page is rendered before anyone has logged in."""
        response = requests.get(
            f"{url}/@login-providers",
            headers={"Accept": "application/json"},
            timeout=30,
        )

        assert response.status_code == 200
        assert [item["id"] for item in response.json()["items"]] == ["dex"]

    def test_listing_is_json(self, url: str):
        """It is a REST service, not a page."""
        response = requests.get(
            f"{url}/@login-providers",
            headers={"Accept": "application/json"},
            timeout=30,
        )

        assert response.headers["Content-Type"].startswith("application/json")

    def test_provider_segment_is_traversed(self, url: str):
        """``@login-providers/<id>`` reaches the start branch rather than
        404ing on the extra path segment."""
        response = requests.get(
            f"{url}/@login-providers/nope",
            headers={"Accept": "application/json"},
            timeout=30,
        )

        assert response.status_code == 404
        assert response.json()["error"]["type"] == "Unknown provider"

    def test_callback_is_reachable_anonymously(self, url: str):
        """Nobody is logged in yet: that is the point of the callback."""
        response = requests.post(
            f"{url}/@identity-callback",
            headers={"Accept": "application/json"},
            json={"provider": "dex", "code": "c", "state": "nope"},
            timeout=30,
        )

        assert response.status_code == 401
        assert response.json()["error"]["type"] == "Authentication failed"

    def test_callback_validates_its_body(self, url: str):
        """And it is really our service answering, not a generic error page."""
        response = requests.post(
            f"{url}/@identity-callback",
            headers={"Accept": "application/json"},
            json={},
            timeout=30,
        )

        assert response.status_code == 400
        assert response.json()["error"]["type"] == "Missing parameters"

    def test_callback_rejects_get(self, url: str):
        """Registered for POST only; a GET must not fall through to the
        listing service or to a view."""
        response = requests.get(
            f"{url}/@identity-callback",
            headers={"Accept": "application/json"},
            timeout=30,
        )

        assert response.status_code in (404, 405)

    def test_identities_is_reachable(self, url: str):
        """``@identities`` is published, and refuses anonymous with JSON
        rather than bouncing to a login form."""
        response = requests.get(
            f"{url}/@identities",
            headers={"Accept": "application/json"},
            timeout=30,
        )

        assert response.status_code == 401
        assert response.json()["error"]["type"] == "Not authenticated"

    def test_identities_accepts_post(self, url: str):
        """The POST factory is registered under the same name."""
        response = requests.post(
            f"{url}/@identities",
            headers={"Accept": "application/json"},
            json={"provider": "dex"},
            timeout=30,
        )

        assert response.status_code == 401

    def test_identities_accepts_delete_with_two_segments(self, url: str):
        """DELETE traverses ``<provider>/<subject>`` rather than 404ing on
        the extra path segments."""
        response = requests.delete(
            f"{url}/@identities/dex/some-subject",
            headers={"Accept": "application/json"},
            timeout=30,
        )

        assert response.status_code == 401
        assert response.json()["error"]["type"] == "Not authenticated"

    def test_audit_log_is_reachable(self, url: str):
        """``@audit-log`` is published and refuses anonymous with JSON."""
        response = requests.get(
            f"{url}/@audit-log",
            headers={"Accept": "application/json"},
            timeout=30,
        )

        assert response.status_code == 401
        assert response.json()["error"]["type"] == "Not authenticated"

    def test_magic_link_endpoints_are_reachable(self, url: str):
        """Both halves of the magic-link flow are published for POST."""
        send = requests.post(
            f"{url}/@magic-link",
            headers={"Accept": "application/json"},
            json={},
            timeout=30,
        )
        confirm = requests.post(
            f"{url}/@magic-link-confirm",
            headers={"Accept": "application/json"},
            json={},
            timeout=30,
        )

        # No email provider is configured in this fixture, so both answer 404
        # from our own service rather than from the publisher.
        for response in (send, confirm):
            assert response.status_code == 404
            assert response.json()["error"]["type"] == "Unknown provider"
