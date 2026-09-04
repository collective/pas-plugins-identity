"""Repairing a provider that sends its verification flags as text.

The strict check in the driver layer is the security property and it does not
move: only a literal ``True`` satisfies the link-by-email gate. What these
cover is the repair that runs *before* it, for a provider whose operator has
said it serializes booleans as strings -- and, just as much, what the repair
declines to guess at.
"""

from pas.plugins.identity.core.utils.flags import BOOLEAN_CLAIMS
from pas.plugins.identity.core.utils.flags import repaired_flags

import pytest


class TestWhatIsRepaired:
    @pytest.mark.parametrize("claim", BOOLEAN_CLAIMS)
    def test_the_string_true_becomes_true(self, claim: str):
        assert repaired_flags({claim: "true"})[claim] is True

    @pytest.mark.parametrize("claim", BOOLEAN_CLAIMS)
    def test_the_string_false_becomes_false(self, claim: str):
        """Both directions, or "repair" would mean "grant"."""
        assert repaired_flags({claim: "false"})[claim] is False

    @pytest.mark.parametrize("value", ["True", "TRUE", " true ", "True "])
    def test_case_and_whitespace_are_tolerated(self, value: str):
        """A serializer that gets the type wrong is not one to trust about
        capitalisation either."""
        assert repaired_flags({"email_verified": value})["email_verified"] is True

    def test_a_real_boolean_is_left_alone(self):
        assert repaired_flags({"email_verified": True})["email_verified"] is True

    def test_phone_number_verified_is_repaired_too(self):
        """A provider that sends one flag as a string sends both that way: it
        is a fact about its serializer, not about the claim."""
        repaired = repaired_flags({"phone_number_verified": "true"})

        assert repaired["phone_number_verified"] is True


class TestWhatIsNotGuessedAt:
    @pytest.mark.parametrize("value", ["1", "yes", "on", "Y", "verified", ""])
    def test_anything_else_is_left_for_the_strict_check(self, value: str):
        """Each of these is a guess about what somebody meant, and guessing
        wrong grants a verified address. Left as it arrived, the strict check
        refuses it, which is what should happen to a value nobody can read
        with confidence."""
        assert repaired_flags({"email_verified": value})["email_verified"] == value

    def test_a_number_is_not_a_boolean(self):
        assert repaired_flags({"email_verified": 1})["email_verified"] == 1

    def test_no_other_claim_is_touched(self):
        """It repairs two named flags, not every string in the payload."""
        payload = {"email": "true", "name": "false", "sub": "s1"}

        assert repaired_flags(payload) == payload


class TestItLeavesTheCallerAlone:
    def test_the_payload_is_not_modified(self):
        """``raw`` is put back from this object afterwards, so it has to still
        say what the provider said."""
        payload = {"email_verified": "true"}

        repaired_flags(payload)

        assert payload["email_verified"] == "true"

    def test_a_payload_with_nothing_to_repair_is_still_a_copy(self):
        """So the caller never has to ask whether anything happened."""
        payload = {"sub": "s1"}

        assert repaired_flags(payload) is not payload

    def test_everything_else_is_carried(self):
        repaired = repaired_flags({"sub": "s1", "email_verified": "true"})

        assert repaired["sub"] == "s1"
