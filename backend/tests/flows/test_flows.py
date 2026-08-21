"""Unit tests for the authorization-code flow layer (§4.4, S1/S6).

No provider and no portal: the flow manager takes a plain dict as its session
and provider metadata as an argument, which is what lets the whole security
surface be tested without Dex running.
"""

from . import DEX_METADATA
from . import DEX_PROVIDER
from . import PORTAL_URL
from . import REDIRECT_URI
from datetime import timedelta
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.flows import ATTEMPT_TTL
from pas.plugins.identity.core.flows import CODE_CHALLENGE_METHOD
from pas.plugins.identity.core.flows import FlowAttempt
from pas.plugins.identity.core.flows import FlowManager
from pas.plugins.identity.core.flows import SESSION_KEY
from pas.plugins.identity.core.flows import validate_came_from
from pas.plugins.identity.core.interfaces import FlowError
from urllib.parse import parse_qs
from urllib.parse import urlparse

import pytest


@pytest.fixture()
def session() -> dict:
    """Return an empty session mapping."""
    return {}


@pytest.fixture()
def manager(session: dict) -> FlowManager:
    """Return a flow manager bound to an empty session."""
    return FlowManager(session, PORTAL_URL)


@pytest.fixture()
def provider() -> ProviderConfig:
    """Return the Dex provider configuration."""
    return ProviderConfig.deserialize(DEX_PROVIDER)


def _query(url: str) -> dict[str, str]:
    """Return an authorize URL's query parameters.

    :param url: The URL to parse.
    :returns: Single-valued query mapping.
    """
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


class TestCameFromValidation:
    """S6 -- open-redirect protection, in both directions."""

    @pytest.mark.parametrize(
        "came_from",
        [
            "https://evil.example/phish",
            "http://evil.example/phish",
            "//evil.example/phish",
            "http://localhost:8080/other-site/page",
            "http://localhost:9999/plone/page",
            "https://localhost:8080/plone/page",
        ],
    )
    def test_refuses_offsite(self, came_from: str):
        """Anything outside the portal is dropped, not rewritten."""
        assert validate_came_from(came_from, PORTAL_URL) == ""

    @pytest.mark.parametrize(
        "came_from",
        [
            "http://localhost:8080/plone",
            "http://localhost:8080/plone/some/page",
            "/plone/some/page",
            "some/relative/page",
        ],
    )
    def test_allows_in_portal(self, came_from: str):
        """Targets inside the portal survive unchanged."""
        assert validate_came_from(came_from, PORTAL_URL) == came_from

    def test_empty_stays_empty(self):
        """No target is a valid answer."""
        assert validate_came_from("", PORTAL_URL) == ""


class TestStart:
    def test_returns_provider_authorize_endpoint(
        self, manager: FlowManager, provider: ProviderConfig
    ):
        """The user is sent to the provider, via authlib."""
        url = manager.start(provider, REDIRECT_URI, DEX_METADATA)

        assert url.startswith(DEX_METADATA["authorization_endpoint"])

    def test_carries_state(self, manager: FlowManager, provider: ProviderConfig):
        """S1 -- every flow carries a state."""
        url = manager.start(provider, REDIRECT_URI, DEX_METADATA)

        assert _query(url)["state"]

    def test_carries_pkce_challenge(
        self, manager: FlowManager, provider: ProviderConfig
    ):
        """S1 -- PKCE, and never the ``plain`` method."""
        query = _query(manager.start(provider, REDIRECT_URI, DEX_METADATA))

        assert query["code_challenge_method"] == CODE_CHALLENGE_METHOD
        assert query["code_challenge"]

    def test_verifier_never_leaves_the_backend(
        self, manager: FlowManager, provider: ProviderConfig, session: dict
    ):
        """The PKCE verifier is the secret half; only the challenge is sent."""
        url = manager.start(provider, REDIRECT_URI, DEX_METADATA)

        attempt = next(iter(session[SESSION_KEY].values()))
        assert attempt["code_verifier"] not in url

    def test_carries_nonce(self, manager: FlowManager, provider: ProviderConfig):
        """S1 -- the nonce ties the id_token to this attempt."""
        assert _query(manager.start(provider, REDIRECT_URI, DEX_METADATA))["nonce"]

    def test_state_is_unpredictable(
        self, manager: FlowManager, provider: ProviderConfig
    ):
        """Two attempts never share a state."""
        first = _query(manager.start(provider, REDIRECT_URI, DEX_METADATA))["state"]
        second = _query(manager.start(provider, REDIRECT_URI, DEX_METADATA))["state"]

        assert first != second

    def test_attempt_is_stored(
        self, manager: FlowManager, provider: ProviderConfig, session: dict
    ):
        """The attempt is bound to the initiating session (S1)."""
        url = manager.start(provider, REDIRECT_URI, DEX_METADATA)

        state = _query(url)["state"]
        assert state in session[SESSION_KEY]

    def test_came_from_is_validated_at_start(
        self, manager: FlowManager, provider: ProviderConfig, session: dict
    ):
        """A hostile target is dropped before it is ever stored."""
        manager.start(
            provider, REDIRECT_URI, DEX_METADATA, came_from="https://evil.example"
        )

        attempt = next(iter(session[SESSION_KEY].values()))
        assert attempt["came_from"] == ""

    def test_link_for_is_recorded(
        self, manager: FlowManager, provider: ProviderConfig, session: dict
    ):
        """A linking flow remembers whose account it is linking to."""
        manager.start(provider, REDIRECT_URI, DEX_METADATA, link_for="userid-1")

        attempt = next(iter(session[SESSION_KEY].values()))
        assert attempt["link_for"] == "userid-1"

    def test_metadata_without_endpoint_refused(
        self, manager: FlowManager, provider: ProviderConfig
    ):
        """Unusable discovery is an error, not a broken redirect."""
        with pytest.raises(FlowError, match="authorization_endpoint"):
            manager.start(provider, REDIRECT_URI, {"issuer": "http://dex:5556/dex"})


class TestStatePopping:
    """S1 -- the state must be present, unexpired and unused."""

    @pytest.fixture()
    def state(self, manager: FlowManager, provider: ProviderConfig) -> str:
        """Start a flow and return its state."""
        return _query(manager.start(provider, REDIRECT_URI, DEX_METADATA))["state"]

    def test_pop_returns_attempt(self, manager: FlowManager, state: str):
        """A genuine callback finds its attempt."""
        attempt = manager.pop(state)

        assert attempt.state == state
        assert attempt.provider_id == "dex"

    def test_unknown_state_refused(self, manager: FlowManager, state: str):
        """A forged state matches nothing."""
        with pytest.raises(FlowError):
            manager.pop("not-a-real-state")

    def test_replay_refused(self, manager: FlowManager, state: str):
        """An attempt is single-use, so the second callback fails."""
        manager.pop(state)

        with pytest.raises(FlowError):
            manager.pop(state)

    def test_expired_state_refused(
        self, manager: FlowManager, session: dict, state: str
    ):
        """An attempt left overnight is not honoured."""
        stored = session[SESSION_KEY][state]
        stale = FlowAttempt.deserialize(stored)
        stale.created = stale.created - ATTEMPT_TTL - timedelta(seconds=1)
        session[SESSION_KEY][state] = stale.serialize()

        with pytest.raises(FlowError):
            manager.pop(state)

    def test_expired_attempts_are_swept(
        self, manager: FlowManager, session: dict, state: str
    ):
        """Dead attempts do not accumulate in the session."""
        stored = session[SESSION_KEY][state]
        stale = FlowAttempt.deserialize(stored)
        stale.created = stale.created - ATTEMPT_TTL - timedelta(seconds=1)
        session[SESSION_KEY][state] = stale.serialize()

        with pytest.raises(FlowError):
            manager.pop(state)

        assert session[SESSION_KEY] == {}

    def test_errors_do_not_distinguish_causes(
        self, manager: FlowManager, session: dict, state: str
    ):
        """Unknown, expired and replayed all read the same, so a caller
        cannot probe which states exist."""
        manager.pop(state)
        with pytest.raises(FlowError) as replayed:
            manager.pop(state)
        with pytest.raises(FlowError) as unknown:
            manager.pop("never-existed")

        assert str(replayed.value) == str(unknown.value)

    def test_sibling_attempts_survive(
        self, manager: FlowManager, provider: ProviderConfig, state: str
    ):
        """Finishing one flow does not disturb another tab's."""
        other = _query(manager.start(provider, REDIRECT_URI, DEX_METADATA))["state"]

        manager.pop(state)

        assert manager.pop(other).state == other


class TestProviderBinding:
    """A code issued for one provider is never redeemed at another."""

    def test_mismatched_provider_refused(
        self, manager: FlowManager, provider: ProviderConfig
    ):
        """The attempt names its provider, and finish() checks it."""
        url = manager.start(provider, REDIRECT_URI, DEX_METADATA)
        state = _query(url)["state"]
        other = ProviderConfig.deserialize({**DEX_PROVIDER, "id": "other-dex"})

        with pytest.raises(FlowError, match="does not match"):
            manager.finish(other, REDIRECT_URI, DEX_METADATA, state, "some-code")

    def test_missing_token_endpoint_refused(
        self, manager: FlowManager, provider: ProviderConfig
    ):
        """Unusable discovery fails before any network call."""
        url = manager.start(provider, REDIRECT_URI, DEX_METADATA)
        state = _query(url)["state"]
        metadata = {k: v for k, v in DEX_METADATA.items() if k != "token_endpoint"}

        with pytest.raises(FlowError, match="token_endpoint"):
            manager.finish(provider, REDIRECT_URI, metadata, state, "some-code")

    def test_finish_consumes_the_attempt(
        self, manager: FlowManager, provider: ProviderConfig, session: dict
    ):
        """Even a failed finish burns the state, so it cannot be retried."""
        url = manager.start(provider, REDIRECT_URI, DEX_METADATA)
        state = _query(url)["state"]
        metadata = {k: v for k, v in DEX_METADATA.items() if k != "token_endpoint"}

        with pytest.raises(FlowError):
            manager.finish(provider, REDIRECT_URI, metadata, state, "some-code")

        assert state not in session[SESSION_KEY]


class TestFlowAttempt:
    def test_round_trips_through_session(self):
        """Serialization loses nothing the callback needs."""
        attempt = FlowAttempt(
            state="s",
            provider_id="dex",
            code_verifier="v",
            nonce="n",
            came_from="/plone/page",
            link_for="userid-1",
        )

        restored = FlowAttempt.deserialize(attempt.serialize())

        assert restored.state == "s"
        assert restored.code_verifier == "v"
        assert restored.nonce == "n"
        assert restored.came_from == "/plone/page"
        assert restored.link_for == "userid-1"
        assert restored.created == attempt.created

    def test_fresh_attempt_is_not_expired(self):
        """A just-created attempt is usable."""
        assert FlowAttempt("s", "dex", "v", "n").expired is False

    def test_old_attempt_is_expired(self):
        """One past the TTL is not."""
        attempt = FlowAttempt("s", "dex", "v", "n")
        attempt.created = attempt.created - ATTEMPT_TTL - timedelta(seconds=1)

        assert attempt.expired is True

    def test_ttl_is_short(self):
        """A stolen state should be useless quickly."""
        assert timedelta(minutes=15) >= ATTEMPT_TTL
