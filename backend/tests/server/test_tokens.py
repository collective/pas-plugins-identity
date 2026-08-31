"""Access tokens.

Self-encoded, so the assertions divide in two: what a token carries, and what
a verifier refuses. The second half is the one that matters, and every refusal
here is deliberately indistinguishable from the outside.
"""

from . import ISSUER
from . import PROFILE_ID
from pas.plugins.identity.server.grants.tokens import decode_access_token
from pas.plugins.identity.server.grants.tokens import get_issuer
from pas.plugins.identity.server.grants.tokens import get_ttl
from pas.plugins.identity.server.grants.tokens import ISSUER_RECORD
from pas.plugins.identity.server.grants.tokens import mint_access_token
from pas.plugins.identity.server.grants.tokens import token_response
from pas.plugins.identity.server.grants.tokens import TOKEN_TYPE
from pas.plugins.identity.server.grants.tokens import TokenError
from pas.plugins.identity.server.grants.tokens import TTL_RECORD
from pas.plugins.identity.server.utils.keys import rotate_keys
from pas.plugins.identity.server.utils.keys import set_keys
from plone import api

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


class TestIssuer:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_an_unconfigured_issuer_is_refused(self):
        """The server signs nothing until the site says what it is called: a
        token with the wrong `iss` is rejected by every relying party, and
        the failure would surface at the RP rather than here."""
        with pytest.raises(TokenError, match="No issuer"):
            get_issuer()

    def test_a_trailing_slash_is_stripped(self):
        """Relying parties compare `iss` byte for byte."""
        api.portal.set_registry_record(ISSUER_RECORD, f"{ISSUER}/")

        assert get_issuer() == ISSUER

    def test_surrounding_whitespace_is_stripped(self):
        """A value pasted into the control panel."""
        api.portal.set_registry_record(ISSUER_RECORD, f"  {ISSUER}  ")

        assert get_issuer() == ISSUER

    def test_a_whitespace_only_issuer_counts_as_unset(self):
        api.portal.set_registry_record(ISSUER_RECORD, "   ")

        with pytest.raises(TokenError):
            get_issuer()


class TestTTL:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_the_default_is_fifteen_minutes(self):
        """Short by design. With no denylist, the lifetime is the only thing
        limiting how long a token stays good after access is withdrawn."""
        assert get_ttl() == 900

    def test_it_is_configurable(self):
        api.portal.set_registry_record(TTL_RECORD, 60)

        assert get_ttl() == 60


class TestMinting:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, issuer) -> None:
        self.portal = portal
        self.issuer = issuer

    def test_a_token_is_a_string(self):
        """authlib hands back bytes; everything downstream wants str."""
        token, _ttl = mint_access_token("app", "alice")

        assert isinstance(token, str)

    def test_the_lifetime_is_reported(self):
        _token, ttl = mint_access_token("app", "alice")

        assert ttl == 900

    def test_the_lifetime_can_be_overridden(self):
        _token, ttl = mint_access_token("app", "alice", ttl=30)

        assert ttl == 30

    def test_the_claims_round_trip(self):
        token, _ttl = mint_access_token("app", "alice", scope="read write")

        claims = decode_access_token(token, audience="app")

        assert claims["sub"] == "alice"
        assert claims["iss"] == self.issuer
        assert claims["aud"] == "app"
        assert claims["client_id"] == "app"
        assert claims["scope"] == "read write"

    def test_every_token_is_unique(self):
        """Two tokens minted in the same second for the same subject still
        have to be distinguishable in an audit trail."""
        first, _ = mint_access_token("app", "alice")
        second, _ = mint_access_token("app", "alice")

        assert first != second

    def test_the_jti_is_what_makes_them_unique(self):
        first, _ = mint_access_token("app", "alice")
        second, _ = mint_access_token("app", "alice")

        assert decode_access_token(first)["jti"] != decode_access_token(second)["jti"]

    def test_minting_without_a_key_is_refused(self):
        set_keys([])

        with pytest.raises(TokenError, match="no signing key"):
            mint_access_token("app", "alice")

    def test_minting_without_an_issuer_is_refused(self):
        api.portal.set_registry_record(ISSUER_RECORD, "")

        with pytest.raises(TokenError, match="No issuer"):
            mint_access_token("app", "alice")


class TestVerifying:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, issuer) -> None:
        self.portal = portal
        self.issuer = issuer
        self.token, _ttl = mint_access_token("app", "alice", scope="read")

    def test_a_good_token_verifies(self):
        assert decode_access_token(self.token)["sub"] == "alice"

    def test_the_right_audience_verifies(self):
        assert decode_access_token(self.token, audience="app")

    def test_the_wrong_audience_is_refused(self):
        """A token minted for one client must not be replayable at a resource
        server that trusts another."""
        with pytest.raises(TokenError):
            decode_access_token(self.token, audience="other-app")

    def test_an_expired_token_is_refused(self):
        expired, _ttl = mint_access_token("app", "alice", ttl=-10)

        with pytest.raises(TokenError):
            decode_access_token(expired)

    def test_a_token_from_another_issuer_is_refused(self):
        """Somebody else's authorization server is not this one, even if the
        signature is perfectly good over there."""
        api.portal.set_registry_record(ISSUER_RECORD, "https://elsewhere.example")

        with pytest.raises(TokenError):
            decode_access_token(self.token)

    def test_a_tampered_payload_is_refused(self):
        """The signature is over the payload; flipping a character in it must
        not survive."""
        head, payload, signature = self.token.split(".")
        tampered = f"{head}.{payload[:-2]}XY.{signature}"

        with pytest.raises(TokenError):
            decode_access_token(tampered)

    def test_a_token_signed_by_a_stranger_is_refused(self):
        """The key ring is the whole trust boundary. A perfectly well-formed
        token signed by a key this server never had is a forgery."""
        set_keys([])
        rotate_keys()
        alien, _ttl = mint_access_token("app", "mallory")
        set_keys([])
        rotate_keys()

        with pytest.raises(TokenError):
            decode_access_token(alien)

    @pytest.mark.parametrize(
        "token",
        ["", "garbage", "a.b", "a.b.c", "....", "not.a.jwt.at.all"],
    )
    def test_a_malformed_token_is_refused_not_crashed(self, token):
        """The Bearer plugin will hand this whatever arrived in a header."""
        with pytest.raises(TokenError):
            decode_access_token(token)

    def test_verification_without_a_key_is_refused(self):
        """A token presented to a site that has since removed the server
        profile. There is nothing to verify against, and the answer has to be
        a refusal rather than a traceback out of the Bearer plugin."""
        set_keys([])

        with pytest.raises(TokenError, match="no signing key"):
            decode_access_token(self.token)

    def test_verification_survives_a_rotation(self):
        """The reason the ring keeps old keys at all."""
        rotate_keys()

        assert decode_access_token(self.token)["sub"] == "alice"

    def test_verification_fails_once_the_key_falls_off_the_ring(self):
        """Stated so the bound is a decision rather than a surprise: rotate
        past the ring size and older tokens stop verifying."""
        for _ in range(5):
            rotate_keys()

        with pytest.raises(TokenError):
            decode_access_token(self.token)


class TestTokenResponse:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, issuer) -> None:
        self.portal = portal

    def test_the_shape_is_rfc6749(self):
        body = token_response("app", "alice", scope="read")

        assert body["token_type"] == TOKEN_TYPE
        assert body["expires_in"] == 900
        assert body["scope"] == "read"

    def test_the_token_verifies(self):
        body = token_response("app", "alice")

        assert decode_access_token(body["access_token"], audience="app")

    def test_scope_is_omitted_when_empty(self):
        """RFC 6749 asks for it only when it differs from what was
        requested; sending an empty string reads as 'no scopes granted'."""
        assert "scope" not in token_response("app", "alice")
