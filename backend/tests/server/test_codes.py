"""Authorization codes.

Codes are the one thing this layer persists, and the only reason to persist
them is to be able to refuse the second use. Most of what is asserted here is
therefore about refusal.
"""

from datetime import datetime
from datetime import timedelta
from datetime import UTC
from pas.plugins.identity.server.codes import AuthorizationCode
from pas.plugins.identity.server.codes import AuthorizationCodeStore
from pas.plugins.identity.server.codes import ChallengeError
from pas.plugins.identity.server.codes import check_challenge
from pas.plugins.identity.server.codes import CODE_TTL
from pas.plugins.identity.server.codes import CodeError
from pas.plugins.identity.server.codes import make_verifier

import pytest


REDIRECT = "https://app.example.org/cb"


class TestIssuing:
    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.store = AuthorizationCodeStore()

    def test_a_code_is_returned(self):
        assert self.store.issue("app", "alice", REDIRECT)

    def test_codes_are_unique(self):
        codes = {self.store.issue("app", "alice", REDIRECT) for _ in range(20)}

        assert len(codes) == 20

    def test_the_grant_records_what_was_authorized(self):
        code = self.store.issue("app", "alice", REDIRECT, scope="read")

        grant = self.store.redeem(code, "app", REDIRECT)

        assert grant.subject == "alice"
        assert grant.scope == "read"
        assert grant.client_id == "app"


class TestRedeeming:
    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.store = AuthorizationCodeStore()
        self.code = self.store.issue("app", "alice", REDIRECT)

    def test_a_good_code_redeems(self):
        assert self.store.redeem(self.code, "app", REDIRECT).subject == "alice"

    def test_a_code_is_single_use(self):
        """The whole reason codes are persisted."""
        self.store.redeem(self.code, "app", REDIRECT)

        with pytest.raises(CodeError):
            self.store.redeem(self.code, "app", REDIRECT)

    def test_an_unknown_code_is_refused(self):
        with pytest.raises(CodeError):
            self.store.redeem("never-issued", "app", REDIRECT)

    def test_another_client_cannot_redeem_it(self):
        """A code leaked to a second registered client is not a token for
        that client."""
        with pytest.raises(CodeError):
            self.store.redeem(self.code, "other", REDIRECT)

    def test_another_redirect_uri_is_refused(self):
        """RFC 6749 requires the token request to repeat it, which is what
        stops a code obtained through one registered URI being redeemed as
        though it came through another."""
        with pytest.raises(CodeError):
            self.store.redeem(self.code, "app", "https://app.example.org/other")

    def test_an_expired_code_is_refused(self):
        store = AuthorizationCodeStore()
        code = store.issue("app", "alice", REDIRECT)
        store._codes[code].expires_at = datetime.now(UTC) - timedelta(seconds=1)

        with pytest.raises(CodeError):
            store.redeem(code, "app", REDIRECT)

    def test_a_failed_redemption_still_burns_the_code(self):
        """Otherwise one leaked code is an unlimited number of guesses."""
        with pytest.raises(CodeError):
            self.store.redeem(self.code, "wrong-client", REDIRECT)

        with pytest.raises(CodeError):
            self.store.redeem(self.code, "app", REDIRECT)


class TestPKCE:
    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.store = AuthorizationCodeStore()
        self.verifier, self.challenge = make_verifier()

    def test_the_right_verifier_redeems(self):
        code = self.store.issue("app", "alice", REDIRECT, challenge=self.challenge)

        assert self.store.redeem(code, "app", REDIRECT, verifier=self.verifier)

    def test_the_wrong_verifier_is_refused(self):
        code = self.store.issue("app", "alice", REDIRECT, challenge=self.challenge)
        other, _ = make_verifier()

        with pytest.raises(CodeError):
            self.store.redeem(code, "app", REDIRECT, verifier=other)

    def test_a_missing_verifier_is_refused(self):
        """A code issued under PKCE cannot be redeemed without it -- that is
        the entire attack PKCE exists to stop."""
        code = self.store.issue("app", "alice", REDIRECT, challenge=self.challenge)

        with pytest.raises(CodeError):
            self.store.redeem(code, "app", REDIRECT)

    def test_a_verifier_for_a_grant_without_a_challenge_is_refused(self):
        """The two halves of the exchange disagree about whether PKCE was in
        play, which is not a state this server accepts."""
        code = self.store.issue("app", "alice", REDIRECT)

        with pytest.raises(CodeError):
            self.store.redeem(code, "app", REDIRECT, verifier=self.verifier)

    def test_the_challenge_is_the_s256_of_the_verifier(self):
        """Pinning the transformation, not just that it round-trips: a
        symmetric bug in one implementation would round-trip happily."""
        import base64
        import hashlib

        expected = (
            base64
            .urlsafe_b64encode(hashlib.sha256(self.verifier.encode("ascii")).digest())
            .rstrip(b"=")
            .decode("ascii")
        )

        assert self.challenge == expected

    def test_the_challenge_is_unpadded(self):
        """RFC 7636 says base64url with no padding; a padded one is rejected
        by strict clients."""
        assert "=" not in self.challenge


class TestCheckChallenge:
    def test_s256_is_accepted(self):
        _verifier, challenge = make_verifier()

        assert check_challenge(challenge, "S256", required=True) == challenge

    def test_a_missing_challenge_is_allowed_when_not_required(self):
        assert check_challenge("", "", required=False) == ""

    def test_a_missing_challenge_is_refused_when_required(self):
        """S8: public clients must use PKCE."""
        with pytest.raises(ChallengeError, match="must use PKCE"):
            check_challenge("", "", required=True)

    def test_plain_is_refused(self):
        """`plain` puts the verifier in the authorization request, which is
        the exact place PKCE exists to protect."""
        with pytest.raises(ChallengeError, match="Unsupported"):
            check_challenge("abc", "plain", required=True)

    def test_an_omitted_method_is_refused(self):
        """RFC 7636 defaults it to `plain`, which this server does not accept.
        Saying so beats silently treating it as S256 and failing later with
        something that reads like a client bug."""
        with pytest.raises(ChallengeError, match="must be S256"):
            check_challenge("abc", "", required=False)


class TestSweeping:
    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.store = AuthorizationCodeStore()

    def test_expired_codes_are_dropped_on_write(self):
        """Most authorization requests are abandoned rather than completed,
        so without this the store only grows."""
        stale = self.store.issue("app", "alice", REDIRECT)
        self.store._codes[stale].expires_at = datetime.now(UTC) - timedelta(seconds=1)

        self.store.issue("app", "bob", REDIRECT)

        assert self.store.count() == 1

    def test_live_codes_survive_a_sweep(self):
        first = self.store.issue("app", "alice", REDIRECT)
        self.store.issue("app", "bob", REDIRECT)

        assert self.store.count() == 2
        assert self.store.redeem(first, "app", REDIRECT).subject == "alice"


class TestTheGrantObject:
    def test_a_fresh_code_is_not_expired(self):
        assert not AuthorizationCode("app", "alice", REDIRECT).is_expired()

    def test_the_default_lifetime_is_the_declared_one(self):
        grant = AuthorizationCode("app", "alice", REDIRECT)
        remaining = (grant.expires_at - datetime.now(UTC)).total_seconds()

        assert 0 < remaining <= CODE_TTL

    def test_serialize_never_carries_the_code(self):
        """The object is what the code maps *to*; the key is the secret."""
        grant = AuthorizationCode("app", "alice", REDIRECT, challenge="abc")

        assert "code" not in grant.serialize()
        assert grant.serialize()["pkce"] is True

    def test_serialize_reports_no_pkce_when_there_was_none(self):
        assert AuthorizationCode("app", "alice", REDIRECT).serialize()["pkce"] is False
