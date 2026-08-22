"""Integration tests for the signed flow cookie.

The point of the signature is that the callback is bound to the browser that
started the flow, so most of what is worth testing here is what happens to a
cookie somebody else wrote.
"""

from . import DEX_METADATA
from . import PORTAL_URL
from . import REDIRECT_URI
from base64 import urlsafe_b64encode
from pas.plugins.identity.core.flows import FlowManager
from pas.plugins.identity.core.flows import session as flow_session
from pas.plugins.identity.core.flows import SESSION_KEY
from pas.plugins.identity.core.flows.session import COOKIE_NAME
from pas.plugins.identity.core.flows.session import decode
from pas.plugins.identity.core.flows.session import encode
from pas.plugins.identity.core.flows.session import FlowSession
from pas.plugins.identity.core.flows.session import KEY_RING
from pas.plugins.identity.core.flows.session import signing_keys
from pas.plugins.identity.core.interfaces import FlowError
from plone.keyring.interfaces import IKeyManager
from urllib.parse import parse_qs
from urllib.parse import urlparse
from zope.component import getUtility

import hashlib
import hmac
import json
import pytest


def sign(payload: bytes, key: bytes) -> str:
    """Render a payload and signature as a cookie value.

    :param payload: The raw payload bytes.
    :param key: The derived key to sign with.
    :returns: The cookie value.
    """
    signature = hmac.new(key, payload, hashlib.sha256).digest()
    return (
        f"{urlsafe_b64encode(payload).decode('ascii')}"
        f".{urlsafe_b64encode(signature).decode('ascii')}"
    )


@pytest.fixture
def request_(portal):
    """Return the current request with no flow cookie set."""
    portal.REQUEST.cookies.pop(COOKIE_NAME, None)
    return portal.REQUEST


class TestSigning:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_round_trip(self):
        """What was encoded comes back."""
        assert decode(encode({"a": 1, "b": "two"})) == {"a": 1, "b": "two"}

    def test_signature_is_not_the_payload(self):
        """Sanity: the value carries two parts."""
        payload, _, signature = encode({"a": 1}).partition(".")

        assert payload and signature

    def test_payload_is_readable_by_the_browser(self):
        """Signing is integrity, not confidentiality -- and nothing secret to
        the *user* is in here; the verifier is secret from the provider."""
        from base64 import urlsafe_b64decode

        payload = encode({"a": 1}).partition(".")[0]

        assert json.loads(urlsafe_b64decode(payload)) == {"a": 1}

    def test_tampered_payload_is_refused(self):
        """The whole point: editing the state invalidates the cookie."""
        value = encode({"state": "mine"})
        forged = sign(b'{"state":"theirs"}', b"not-the-key")

        assert decode(value) == {"state": "mine"}
        assert decode(forged) == {}

    def test_signature_from_the_wrong_key_is_refused(self):
        """An attacker who guesses the format still cannot sign."""
        forged = sign(json.dumps({"state": "theirs"}).encode(), b"wrong-key")

        assert decode(forged) == {}

    def test_truncated_signature_is_refused(self):
        """Comparison is constant-time and length-sensitive."""
        value = encode({"a": 1})

        assert decode(value[:-4]) == {}

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "no-dot",
            ".",
            # Stray characters outside the alphabet are silently dropped by
            # urlsafe_b64decode, so these decode to nothing and then fail the
            # signature check ...
            "!!!.!!!",
            # ... while bad padding raises out of the decoder itself, which is
            # a different branch.
            "abcde.abcde",
        ],
    )
    def test_malformed_values_yield_an_empty_session(self, value: str):
        """A broken cookie is an empty session, never an error page."""
        assert decode(value) == {}

    def test_signed_non_json_is_refused(self):
        """A correctly signed cookie still has to contain JSON."""
        assert decode(sign(b"not json at all", signing_keys()[0])) == {}

    def test_signed_non_object_is_refused(self):
        """A signed JSON list is not a session."""
        assert decode(sign(b"[1, 2, 3]", signing_keys()[0])) == {}

    def test_an_older_ring_key_still_verifies(self):
        """Rotating the keyring must not strand a login already in flight."""
        older = signing_keys()[-1]

        assert decode(sign(json.dumps({"a": 1}).encode(), older)) == {"a": 1}

    def test_key_is_derived_not_reused(self):
        """The raw ring secret must never be the signing key: a flow cookie
        and an auth ticket signed with the same ring must not be
        interchangeable."""
        raw = getUtility(IKeyManager)[KEY_RING][0].encode("utf-8")

        assert raw not in signing_keys()

    def test_empty_ring_is_an_error(self, monkeypatch):
        """Signing with nothing would silently produce forgeable cookies."""
        monkeypatch.setattr(
            flow_session, "getUtility", lambda iface: {KEY_RING: [None, None]}
        )

        with pytest.raises(RuntimeError, match="no secret"):
            signing_keys()


class TestFlowSession:
    """The mapping interface FlowManager is written against."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_) -> None:
        self.portal = portal
        self.request = request_

    def test_starts_empty(self):
        """No cookie, no session."""
        assert dict(FlowSession(self.request)) == {}

    def test_set_and_get(self):
        """Values survive within one request."""
        session = FlowSession(self.request)
        session["k"] = {"a": 1}

        assert session["k"] == {"a": 1}
        assert len(session) == 1
        assert list(session) == ["k"]

    def test_missing_key_raises(self):
        """It is a mapping, and behaves like one."""
        with pytest.raises(KeyError):
            FlowSession(self.request)["nope"]

    def test_delete(self):
        """Removing the last value empties the session."""
        session = FlowSession(self.request)
        session["k"] = {"a": 1}

        del session["k"]

        assert dict(session) == {}

    def test_writes_a_signed_cookie(self):
        """The value on the wire is what decode() accepts."""
        session = FlowSession(self.request)
        session["k"] = {"a": 1}

        written = self.request.response.cookies[COOKIE_NAME]["value"]
        assert decode(written) == {"k": {"a": 1}}

    def test_cookie_is_http_only(self):
        """Script must not be able to read the flow material."""
        session = FlowSession(self.request)
        session["k"] = {"a": 1}

        assert self.request.response.cookies[COOKIE_NAME]["HttpOnly"] is True

    def test_cookie_is_same_site_lax(self):
        """Strict would withhold the cookie on the provider's redirect back,
        which is the one request that must carry it."""
        session = FlowSession(self.request)
        session["k"] = {"a": 1}

        assert self.request.response.cookies[COOKIE_NAME]["SameSite"] == "Lax"

    def test_cookie_is_not_secure_over_http(self):
        """A development site on plain HTTP must still be able to log in."""
        self.request.other["SERVER_URL"] = "http://localhost:8080"
        session = FlowSession(self.request)
        session["k"] = {"a": 1}

        assert not self.request.response.cookies[COOKIE_NAME]["Secure"]

    def test_cookie_is_secure_over_https(self):
        """Anywhere real, the cookie must not travel in the clear."""
        self.request.other["SERVER_URL"] = "https://plone.example"
        session = FlowSession(self.request)
        session["k"] = {"a": 1}

        assert self.request.response.cookies[COOKIE_NAME]["Secure"] is True

    def test_emptying_expires_the_cookie(self):
        """A finished flow leaves no signed leftovers in the browser."""
        session = FlowSession(self.request)
        session["k"] = {"a": 1}

        del session["k"]

        assert self.request.response.cookies[COOKIE_NAME]["value"] == "deleted"

    def test_reads_an_existing_cookie(self):
        """The second request of a flow sees what the first one wrote."""
        self.request.cookies[COOKIE_NAME] = encode({"k": {"a": 1}})

        assert dict(FlowSession(self.request)) == {"k": {"a": 1}}

    def test_forged_cookie_reads_as_empty(self):
        """An attacker-authored cookie leaves the session blank."""
        self.request.cookies[COOKIE_NAME] = sign(b'{"k": 1}', b"wrong-key")

        assert dict(FlowSession(self.request)) == {}


class TestRoundTripWithTheFlowManager:
    """The thing that actually has to work: start a flow on one request and
    finish it on the next."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, provider) -> None:
        self.portal = portal
        self.request = request_
        self.provider = provider

    def test_attempt_survives_between_requests(self):
        """The callback finds the attempt the authorize request stored."""
        url = FlowManager(FlowSession(self.request), PORTAL_URL).start(
            self.provider, REDIRECT_URI, DEX_METADATA
        )
        state = parse_qs(urlparse(url).query)["state"][0]

        # The provider sends the browser back; the cookie comes with it.
        self.request.cookies[COOKIE_NAME] = self.request.response.cookies[COOKIE_NAME][
            "value"
        ]
        attempt = FlowManager(FlowSession(self.request), PORTAL_URL).pop(state)

        assert attempt.state == state
        assert attempt.provider_id == "dex"

    def test_attempt_does_not_survive_a_forged_cookie(self):
        """Without the signature this is where a flow could be hijacked."""
        url = FlowManager(FlowSession(self.request), PORTAL_URL).start(
            self.provider, REDIRECT_URI, DEX_METADATA
        )
        state = parse_qs(urlparse(url).query)["state"][0]

        stored = decode(self.request.response.cookies[COOKIE_NAME]["value"])
        self.request.cookies[COOKIE_NAME] = sign(
            json.dumps(stored).encode("utf-8"), b"attacker-key"
        )

        with pytest.raises(FlowError):
            FlowManager(FlowSession(self.request), PORTAL_URL).pop(state)

    def test_popping_clears_the_cookie(self):
        """Once the only attempt is consumed there is nothing left to keep."""
        url = FlowManager(FlowSession(self.request), PORTAL_URL).start(
            self.provider, REDIRECT_URI, DEX_METADATA
        )
        state = parse_qs(urlparse(url).query)["state"][0]
        self.request.cookies[COOKIE_NAME] = self.request.response.cookies[COOKIE_NAME][
            "value"
        ]

        session = FlowSession(self.request)
        FlowManager(session, PORTAL_URL).pop(state)

        assert not session.get(SESSION_KEY)
        assert self.request.response.cookies[COOKIE_NAME]["value"] == "deleted"
