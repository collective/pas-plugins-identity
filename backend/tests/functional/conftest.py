"""Fixtures for the end-to-end flow tests against a real provider."""

from ..conftest import DEX_USER
from bs4 import BeautifulSoup
from pas.plugins.identity.core.controlpanel import CALLBACK_URL_RECORD
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.flows import metadata as flow_metadata
from plone import api
from urllib.parse import parse_qs
from urllib.parse import urljoin
from urllib.parse import urlparse

import pytest
import requests
import transaction


#: The redirect URI registered with Dex. It stands in for the Volto route:
#: nothing serves it, and nothing needs to -- the test reads the code and
#: state straight off the redirect the way the frontend would.
CALLBACK_URL = "http://localhost:3000/login-identity"


@pytest.fixture
def second_provider(dex) -> dict:
    """Return a second provider record, Dex's other static client.

    One issuer, two clients: the identity key is ``(provider_id, subject)``,
    so two provider ids against the same Dex is enough to exercise linking.
    """
    return {
        **dex,
        "id": "dex-second",
        "title": "Dex (second)",
        "config": {
            **dex["config"],
            "client_id": "plone-second",
            "client_secret": "plone-second-secret",
        },
    }


@pytest.fixture
def portal(functional, dex, second_provider):
    """Return the portal with both Dex clients configured as providers."""
    site = functional["portal"]
    set_providers([
        ProviderConfig.deserialize(dex),
        ProviderConfig.deserialize(second_provider),
    ])
    api.portal.set_registry_record(CALLBACK_URL_RECORD, CALLBACK_URL)
    transaction.commit()
    # Discovery is cached per issuer for the process; a previous test module
    # may have primed it against a stub.
    flow_metadata.forget()
    yield site
    set_providers([])
    transaction.commit()
    flow_metadata.forget()


@pytest.fixture
def api_session(portal):
    """Return a requests session speaking JSON to the portal.

    Cookies persist across calls, which is the point: the flow cookie set when
    the flow starts has to come back on the callback.
    """
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    yield session
    session.close()


@pytest.fixture
def portal_url(portal) -> str:
    """Return the portal URL as served by the test WSGI server."""
    return portal.absolute_url()


@pytest.fixture
def dex_login():
    """Return a helper that logs in at Dex and returns the callback query.

    Drives the provider's own HTML login form, so the authorization code is
    one a real provider issued to a real end-user session -- not a fixture.

    :returns: Callable taking the authorize URL and returning the parsed query
        string of the redirect back to the callback URL.
    """

    def login(authorize_url: str) -> dict[str, str]:
        """Complete Dex's login form and follow the redirect back.

        :param authorize_url: Where the backend told us to send the browser.
        :returns: Single-valued mapping of the callback query parameters.
        :raises AssertionError: When Dex does not redirect straight back to
            the callback URL.
        """
        browser = requests.Session()
        page = browser.get(authorize_url, timeout=30)
        page.raise_for_status()

        form = BeautifulSoup(page.text, "html.parser").find("form")
        action = urljoin(page.url, form["action"])
        response = browser.post(
            action,
            data={"login": DEX_USER["email"], "password": DEX_USER["password"]},
            allow_redirects=False,
            timeout=30,
        )

        # Dex is configured with skipApprovalScreen, so a successful login
        # redirects straight to the callback. Asserting that rather than
        # following an arbitrary chain keeps the helper honest: if a Dex
        # upgrade inserts a step, this fails loudly instead of silently
        # following it somewhere unexpected.
        location = response.headers.get("Location")
        assert location, f"Dex did not redirect; it answered {response.status_code}"
        target = urljoin(response.url, location)
        assert target.startswith(CALLBACK_URL), (
            f"Dex redirected to {target}, not to the callback URL"
        )
        return {k: v[0] for k, v in parse_qs(urlparse(target).query).items()}

    return login
