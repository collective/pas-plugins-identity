"""The shared normalization every driver inherits.

Exercised through the generic OIDC driver, which adds nothing of its own to
the base behaviour.
"""

from . import UNVERIFIED_OIDC
from pas.plugins.identity.core.drivers.github import GitHubDriver
from pas.plugins.identity.core.drivers.google import GoogleDriver
from pas.plugins.identity.core.drivers.oidc import GenericOIDCDriver
from pas.plugins.identity.core.interfaces import ClaimsError

import pytest


class TestEmailVerifiedIsStrict:
    """Only a literal ``True`` counts as verified."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            (True, True),
            (False, False),
            (None, False),
            ("true", False),
            ("True", False),
            (1, False),
            ("", False),
        ],
    )
    def test_email_verified(self, value, expected: bool):
        """Truthy-but-not-True values are treated as unverified."""
        payload = {"sub": "s", "email": "e@example.com", "email_verified": value}

        assert (
            GenericOIDCDriver().normalize_claims(payload)["email_verified"] is expected
        )

    def test_missing_key_is_unverified(self):
        """A provider that says nothing has asserted nothing."""
        payload = {"sub": "s", "email": "e@example.com"}

        assert GenericOIDCDriver().normalize_claims(payload)["email_verified"] is False

    def test_forged_unverified_payload(self):
        """A payload claiming somebody else's address normalizes to
        unverified, which is what stops it linking anywhere."""
        claims = GenericOIDCDriver().normalize_claims(UNVERIFIED_OIDC)

        assert claims["email"] == "erico@plone.org"
        assert claims["email_verified"] is False


class TestTextHelpers:
    """Edge cases in the shared field-reading helper."""

    @pytest.mark.parametrize(
        "payload,expected",
        [
            ({"name": "  Érico  "}, "Érico"),
            ({"name": "   "}, ""),
            ({"name": None}, ""),
            ({"name": 42}, ""),
            ({}, ""),
        ],
    )
    def test_fullname_reading(self, payload: dict, expected: str):
        """Whitespace is trimmed; non-strings never leak into claims."""
        payload = {"sub": "s", **payload}

        assert GenericOIDCDriver().normalize_claims(payload)["fullname"] == expected

    def test_subject_rejects_boolean(self):
        """``True`` is an int in Python; it must not become subject ``"1"``."""
        with pytest.raises(ClaimsError):
            GitHubDriver().subject({"id": True})

    def test_subject_rejects_blank_string(self):
        """A whitespace-only subject is no subject."""
        with pytest.raises(ClaimsError):
            GoogleDriver().subject({"sub": "   "})
