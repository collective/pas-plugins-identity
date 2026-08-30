"""Unit tests for claim-to-property resolution."""

from pas.plugins.identity.core.utils.propertymap import apply_property_map
from pas.plugins.identity.core.utils.propertymap import resolve_claim

import pytest


CLAIMS = {
    "fullname": "Ada Lovelace",
    "email": "ada@example.org",
    "username": "",
    "raw": {
        "name": "Ada from the raw payload",
        "login": "ada",
        "address": {"formatted": "London", "country": ""},
        "groups": ["staff", "math"],
    },
}


class TestResolveClaim:
    """One lookup, ten answers.

    Every case is the same call with a different path, so the table *is* the
    test; what used to be nine near-identical methods is the nine rows below.
    The reasoning that lived in their docstrings lives in the comments beside
    the rows it explains.
    """

    @pytest.mark.parametrize(
        "path,expected",
        [
            # The package's own derivation beats the raw payload.
            ("fullname", "Ada Lovelace"),
            # A key the normalization does not produce still resolves.
            ("login", "ada"),
            # A blank normalized value is not an answer: ``username`` is
            # normalized to "" here while the raw payload has a usable
            # ``login``, and mapping ``username`` must not yield "".
            ("username", None),
            # Nesting is addressed by path rather than by a nested map.
            ("address.formatted", "London"),
            ("nope.not.here", None),
            ("", None),
            # Walking into a string must not raise.
            ("email.something", None),
            ("address.country", None),
            ("groups", ["staff", "math"]),
        ],
        ids=[
            "normalized-claim-wins",
            "falls-through-to-raw",
            "empty-normalized-falls-through-to-raw",
            "dotted-path-reaches-into-raw",
            "unknown-path-is-none",
            "empty-path-is-none",
            "path-through-a-non-mapping-is-none",
            "empty-leaf-is-none",
            "non-string-value-survives",
        ],
    )
    def test_resolution(self, path: str, expected):
        assert resolve_claim(path, CLAIMS) == expected

    def test_missing_raw_is_tolerated(self):
        """Claims built by hand need not carry a raw payload.

        Left out of the table above because it is the one case with a
        different payload, and folding it in would have meant a column that
        is the same value in every other row.
        """
        assert resolve_claim("email", {"email": "x@example.org"}) == "x@example.org"


class TestApplyPropertyMap:
    def test_maps_claim_onto_field(self):
        assert apply_property_map({"fullname": "fullname"}, CLAIMS) == {
            "fullname": "Ada Lovelace"
        }

    def test_renames(self):
        """The point of the map: the two sides have different names."""
        assert apply_property_map({"login": "username"}, CLAIMS) == {"username": "ada"}

    def test_unresolvable_claim_is_omitted(self):
        """A missing claim must not blank the property it maps to."""
        assert apply_property_map({"absent": "fullname"}, CLAIMS) == {}

    def test_empty_target_is_skipped(self):
        """A half-filled row in the control panel is not a mapping."""
        assert apply_property_map({"fullname": ""}, CLAIMS) == {}

    def test_empty_map_resolves_to_nothing(self):
        assert apply_property_map({}, CLAIMS) == {}

    @pytest.mark.parametrize(
        "path,field,expected",
        [
            ("address.formatted", "location", "London"),
            ("email", "email", "ada@example.org"),
        ],
    )
    def test_several_shapes(self, path, field, expected):
        assert apply_property_map({path: field}, CLAIMS) == {field: expected}
