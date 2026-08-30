"""The signing key ring.

The property that matters is not "a key exists" but "a rotation does not
invalidate what is still in flight", so most of what is asserted here is about
the ring rather than about any single key.
"""

from . import PROFILE_ID
from pas.plugins.identity.server.interfaces import ServerError
from pas.plugins.identity.server.utils.keys import current_key
from pas.plugins.identity.server.utils.keys import ensure_keys
from pas.plugins.identity.server.utils.keys import generate_key
from pas.plugins.identity.server.utils.keys import get_keys
from pas.plugins.identity.server.utils.keys import key_set
from pas.plugins.identity.server.utils.keys import public_jwks
from pas.plugins.identity.server.utils.keys import RING_SIZE
from pas.plugins.identity.server.utils.keys import rotate_keys
from pas.plugins.identity.server.utils.keys import set_keys

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


class TestGenerating:
    def test_a_key_is_private(self):
        """The private members are what signing needs."""
        assert {"d", "p", "q"} <= set(generate_key())

    def test_a_key_carries_a_kid(self):
        """Which is how a verifier picks it out of the JWKS."""
        assert generate_key()["kid"]

    def test_two_keys_differ(self):
        """A generator that repeated would let one site sign as another."""
        assert generate_key()["kid"] != generate_key()["kid"]


class TestInstalled:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_the_profile_generated_a_key(self):
        """Generated, not shipped: a key in the package would be the same
        key in every site running it."""
        assert len(get_keys()) == 1

    def test_the_key_is_usable_for_signing(self):
        assert current_key()["kid"]

    def test_ensure_is_idempotent(self):
        """Re-applying the profile must not rotate the key underneath tokens
        that are still valid."""
        before = current_key()["kid"]

        ensure_keys()

        assert current_key()["kid"] == before


class TestWithoutKeys:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        set_keys([])

    def test_signing_is_refused(self):
        """Rather than generating one on the spot, which would produce tokens
        nothing could verify a request later."""
        with pytest.raises(ServerError, match="no signing key"):
            current_key()

    def test_verification_is_refused(self):
        with pytest.raises(ServerError, match="no signing key"):
            key_set()

    def test_the_published_jwks_is_empty_rather_than_an_error(self):
        """The endpoint is public and unauthenticated; it answers honestly
        that there is nothing to verify with."""
        assert public_jwks() == {"keys": []}

    def test_ensure_generates_one(self):
        assert len(ensure_keys()) == 1


class TestRotating:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.original = current_key()["kid"]

    def test_the_new_key_signs(self):
        rotate_keys()

        assert current_key()["kid"] != self.original

    def test_the_old_key_stays_in_the_ring(self):
        """This is the whole point: a token minted a minute ago must still
        verify a minute later."""
        rotate_keys()

        assert self.original in [key["kid"] for key in get_keys()]

    def test_the_old_key_is_still_published(self):
        rotate_keys()

        assert self.original in [key["kid"] for key in public_jwks()["keys"]]

    def test_the_ring_is_bounded(self):
        """An unbounded ring would grow a registry record forever."""
        for _ in range(RING_SIZE + 3):
            rotate_keys()

        assert len(get_keys()) == RING_SIZE

    def test_the_oldest_key_falls_off(self):
        for _ in range(RING_SIZE):
            rotate_keys()

        assert self.original not in [key["kid"] for key in get_keys()]

    def test_newest_is_first(self):
        """The convention the rest of the module relies on."""
        minted = rotate_keys()

        assert get_keys()[0]["kid"] == minted["kid"]


class TestPublishing:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_the_jwks_has_a_key(self):
        assert len(public_jwks()["keys"]) == 1

    def test_no_private_member_is_published(self):
        """The one mistake in this module that would be catastrophic and
        silent: a JWKS is fetched by anyone, and 'd' is the private
        exponent."""
        for key in public_jwks()["keys"]:
            assert not {"d", "p", "q", "dp", "dq", "qi"} & set(key)

    def test_the_published_key_keeps_its_kid(self):
        """Otherwise a verifier could not match it to a token header."""
        assert public_jwks()["keys"][0]["kid"] == current_key()["kid"]

    def test_every_ring_key_is_published(self):
        rotate_keys()

        assert len(public_jwks()["keys"]) == len(get_keys())
