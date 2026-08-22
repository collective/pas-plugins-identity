"""Unit tests for the authorization-code flow layer.

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


def _query(url: str) -> dict[str, str]:
    """Return an authorize URL's query parameters.

    :param url: The URL to parse.
    :returns: Single-valued query mapping.
    """
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


class TestCameFromValidation:
    """Open-redirect protection, in both directions."""

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
    @pytest.fixture(autouse=True)
    def _setup(
        self, manager: FlowManager, provider: ProviderConfig, session: dict
    ) -> None:
        self.manager = manager
        self.provider = provider
        self.session = session

    def start(self, **kwargs) -> str:
        """Start a flow against the Dex provider.

        :param kwargs: Extra arguments for :meth:`FlowManager.start`.
        :returns: The authorize URL.
        """
        return self.manager.start(self.provider, REDIRECT_URI, DEX_METADATA, **kwargs)

    def stored(self) -> dict:
        """Return the single stored attempt.

        :returns: The serialized attempt.
        """
        return next(iter(self.session[SESSION_KEY].values()))

    def test_returns_provider_authorize_endpoint(self):
        """The user is sent to the provider, via authlib."""
        assert self.start().startswith(DEX_METADATA["authorization_endpoint"])

    def test_carries_state(self):
        """Every flow carries a state."""
        assert _query(self.start())["state"]

    def test_carries_pkce_challenge(self):
        """PKCE, and never the ``plain`` method."""
        query = _query(self.start())

        assert query["code_challenge_method"] == CODE_CHALLENGE_METHOD
        assert query["code_challenge"]

    def test_verifier_never_leaves_the_backend(self):
        """The PKCE verifier is the secret half; only the challenge is sent."""
        url = self.start()

        assert self.stored()["code_verifier"] not in url

    def test_carries_nonce(self):
        """The nonce ties the id_token to this attempt."""
        assert _query(self.start())["nonce"]

    def test_state_is_unpredictable(self):
        """Two attempts never share a state."""
        first = _query(self.start())["state"]
        second = _query(self.start())["state"]

        assert first != second

    def test_attempt_is_stored(self):
        """The attempt is bound to the initiating session."""
        state = _query(self.start())["state"]

        assert state in self.session[SESSION_KEY]

    def test_came_from_is_validated_at_start(self):
        """A hostile target is dropped before it is ever stored."""
        self.start(came_from="https://evil.example")

        assert self.stored()["came_from"] == ""

    def test_link_for_is_recorded(self):
        """A linking flow remembers whose account it is linking to."""
        self.start(link_for="userid-1")

        assert self.stored()["link_for"] == "userid-1"

    def test_metadata_without_endpoint_refused(self):
        """Unusable discovery is an error, not a broken redirect."""
        with pytest.raises(FlowError, match="authorization_endpoint"):
            self.manager.start(
                self.provider, REDIRECT_URI, {"issuer": "http://dex:5556/dex"}
            )


class TestStatePopping:
    """The state must be present, unexpired and unused."""

    @pytest.fixture(autouse=True)
    def _setup(
        self, manager: FlowManager, provider: ProviderConfig, session: dict
    ) -> None:
        self.manager = manager
        self.provider = provider
        self.session = session
        self.state = self.start()

    def start(self) -> str:
        """Start a flow and return its state.

        :returns: The state.
        """
        url = self.manager.start(self.provider, REDIRECT_URI, DEX_METADATA)
        return _query(url)["state"]

    def expire(self, state: str) -> None:
        """Age a stored attempt past the TTL.

        :param state: The state whose attempt to age.
        """
        stale = FlowAttempt.deserialize(self.session[SESSION_KEY][state])
        stale.created = stale.created - ATTEMPT_TTL - timedelta(seconds=1)
        self.session[SESSION_KEY][state] = stale.serialize()

    def test_pop_returns_attempt(self):
        """A genuine callback finds its attempt."""
        attempt = self.manager.pop(self.state)

        assert attempt.state == self.state
        assert attempt.provider_id == "dex"

    def test_unknown_state_refused(self):
        """A forged state matches nothing."""
        with pytest.raises(FlowError):
            self.manager.pop("not-a-real-state")

    def test_replay_refused(self):
        """An attempt is single-use, so the second callback fails."""
        self.manager.pop(self.state)

        with pytest.raises(FlowError):
            self.manager.pop(self.state)

    def test_expired_state_refused(self):
        """An attempt left overnight is not honoured."""
        self.expire(self.state)

        with pytest.raises(FlowError):
            self.manager.pop(self.state)

    def test_expired_attempts_are_swept(self):
        """Dead attempts do not accumulate in the session."""
        self.expire(self.state)

        with pytest.raises(FlowError):
            self.manager.pop(self.state)

        assert self.session[SESSION_KEY] == {}

    def test_errors_do_not_distinguish_causes(self):
        """Unknown, expired and replayed all read the same, so a caller
        cannot probe which states exist."""
        self.manager.pop(self.state)
        with pytest.raises(FlowError) as replayed:
            self.manager.pop(self.state)
        with pytest.raises(FlowError) as unknown:
            self.manager.pop("never-existed")

        assert str(replayed.value) == str(unknown.value)

    def test_sibling_attempts_survive(self):
        """Finishing one flow does not disturb another tab's."""
        other = self.start()

        self.manager.pop(self.state)

        assert self.manager.pop(other).state == other


class TestProviderBinding:
    """A code issued for one provider is never redeemed at another."""

    @pytest.fixture(autouse=True)
    def _setup(
        self, manager: FlowManager, provider: ProviderConfig, session: dict
    ) -> None:
        self.manager = manager
        self.provider = provider
        self.session = session
        url = manager.start(provider, REDIRECT_URI, DEX_METADATA)
        self.state = _query(url)["state"]
        self.without_token_endpoint = {
            k: v for k, v in DEX_METADATA.items() if k != "token_endpoint"
        }

    def test_mismatched_provider_refused(self):
        """The attempt names its provider, and finish() checks it."""
        other = ProviderConfig.deserialize({**DEX_PROVIDER, "id": "other-dex"})

        with pytest.raises(FlowError, match="does not match"):
            self.manager.finish(
                other, REDIRECT_URI, DEX_METADATA, self.state, "some-code"
            )

    def test_missing_token_endpoint_refused(self):
        """Unusable discovery fails before any network call."""
        with pytest.raises(FlowError, match="token_endpoint"):
            self.manager.finish(
                self.provider,
                REDIRECT_URI,
                self.without_token_endpoint,
                self.state,
                "some-code",
            )

    def test_finish_consumes_the_attempt(self):
        """Even a failed finish burns the state, so it cannot be retried."""
        with pytest.raises(FlowError):
            self.manager.finish(
                self.provider,
                REDIRECT_URI,
                self.without_token_endpoint,
                self.state,
                "some-code",
            )

        assert self.state not in self.session[SESSION_KEY]


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
