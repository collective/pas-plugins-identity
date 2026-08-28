"""The second call some providers need before their payload is complete.

GitHub keeps every address an account holds, and their verification state, on
``GET /user/emails`` rather than on ``/user``. A driver performs no I/O, so it
names the endpoint and merges the answer while the flow does the fetching --
which is the part tested here.

The policy worth reading twice is that the call is **best-effort**. It
improves a payload; it is not a precondition for signing in. An operator who
narrowed the scope gets a 403 and a provider having a bad afternoon gets a
5xx, and in both cases the login has to continue with what userinfo gave.
Raising instead would turn a missing address into a failed login.
"""

from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.flows import FlowManager

import pytest


PORTAL_URL = "http://localhost:8080/plone"

GITHUB_PROVIDER = {
    "id": "github",
    "driver": "github",
    "title": "GitHub",
    "enabled": True,
    "config": {
        "client_id": "plone",
        "client_secret": "plone-secret",
        "scope": ("read:user", "user:email"),
    },
}

METADATA = {
    "userinfo_endpoint": "https://api.github.com/user",
    "emails_endpoint": "https://api.github.com/user/emails",
}

#: What `/user` answers for somebody who marked their address private.
USER = {"id": 1234567, "login": "ghost", "name": "Ghost", "email": None}

ADDRESSES = [
    {"email": "old@example.com", "primary": False, "verified": True},
    {"email": "ghost@example.com", "primary": True, "verified": True},
]


class StubResponse:
    """The bit of ``requests.Response`` the enrichment call touches."""

    def __init__(self, payload: object, status_code: int = 200) -> None:
        """Hold a canned answer.

        :param payload: What :meth:`json` returns.
        :param status_code: HTTP status; 400 and up raises.
        """
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        """Raise when the provider answered with an error.

        :raises RuntimeError: When the status is 400 or above.
        """
        if self.status_code >= 400:
            raise RuntimeError(f"answered {self.status_code}")

    def json(self) -> object:
        """Return the canned answer.

        :returns: The payload.
        """
        return self.payload


class StubClient:
    """Enough of the authlib session for :meth:`FlowManager._enrich`."""

    def __init__(self, response: StubResponse | Exception) -> None:
        """Hold what the next ``get`` answers.

        :param response: The canned response, or an exception to raise.
        """
        self.response = response
        self.requested: list[str] = []

    def get(self, url: str, **kwargs: object) -> StubResponse:
        """Record the request and answer it.

        :param url: The endpoint asked for.
        :param kwargs: Ignored.
        :returns: The canned response.
        :raises Exception: When constructed with one.
        """
        self.requested.append(url)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


@pytest.fixture
def manager() -> FlowManager:
    """Return a flow manager bound to an empty session.

    :returns: The manager.
    """
    return FlowManager({}, PORTAL_URL)


@pytest.fixture
def github() -> ProviderConfig:
    """Return the GitHub provider configuration.

    :returns: The provider.
    """
    return ProviderConfig.deserialize(GITHUB_PROVIDER)


class TestTheAddressIsFetched:
    @pytest.fixture(autouse=True)
    def _setup(self, manager, github) -> None:
        self.manager = manager
        self.github = github

    def test_the_emails_endpoint_is_called(self):
        client = StubClient(StubResponse(ADDRESSES))

        self.manager._enrich(client, self.github, METADATA, USER)

        assert client.requested == ["https://api.github.com/user/emails"]

    def test_the_address_reaches_the_payload(self):
        """The whole point: `/user` carried `None` for a private address."""
        client = StubClient(StubResponse(ADDRESSES))

        payload = self.manager._enrich(client, self.github, METADATA, USER)

        assert payload["email"] == "ghost@example.com"

    def test_verification_reaches_the_payload_too(self):
        """`/user` has no `email_verified` key at all, so link-by-verified-
        email could never match a GitHub identity."""
        client = StubClient(StubResponse(ADDRESSES))

        payload = self.manager._enrich(client, self.github, METADATA, USER)

        assert payload["email_verified"] is True

    def test_nothing_else_in_the_payload_is_disturbed(self):
        client = StubClient(StubResponse(ADDRESSES))

        payload = self.manager._enrich(client, self.github, METADATA, USER)

        assert payload["id"] == 1234567
        assert payload["login"] == "ghost"


class TestTheCallIsBestEffort:
    """Every one of these used to be impossible because the call did not
    exist; none of them may now become a failed login."""

    @pytest.fixture(autouse=True)
    def _setup(self, manager, github) -> None:
        self.manager = manager
        self.github = github

    @pytest.mark.parametrize("status", [403, 404, 500, 503], ids=str)
    def test_an_error_status_leaves_the_payload_alone(self, status):
        """403 is the realistic one: an operator narrowed the scope."""
        client = StubClient(StubResponse(ADDRESSES, status_code=status))

        assert self.manager._enrich(client, self.github, METADATA, USER) == USER

    def test_a_transport_failure_leaves_the_payload_alone(self):
        client = StubClient(OSError("connection reset"))

        assert self.manager._enrich(client, self.github, METADATA, USER) == USER

    def test_an_undecodable_body_leaves_the_payload_alone(self):
        client = StubClient(StubResponse(ADDRESSES))
        client.response.json = _raise_value_error

        assert self.manager._enrich(client, self.github, METADATA, USER) == USER


class TestProvidersThatNeedNothing:
    """The other drivers must not gain a network call by being upgraded."""

    @pytest.fixture(autouse=True)
    def _setup(self, manager, github) -> None:
        self.manager = manager
        self.github = github

    def test_no_endpoint_in_the_metadata_means_no_call(self):
        """Which is every provider but GitHub."""
        client = StubClient(StubResponse(ADDRESSES))

        payload = self.manager._enrich(
            client,
            self.github,
            {"userinfo_endpoint": "https://api.github.com/user"},
            USER,
        )

        assert client.requested == []
        assert payload == USER


def _raise_value_error() -> None:
    """Stand in for a body that is not JSON.

    :raises ValueError: Always.
    """
    raise ValueError("not json")
