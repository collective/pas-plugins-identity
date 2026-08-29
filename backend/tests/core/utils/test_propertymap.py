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
    def test_normalized_claim_wins(self):
        """The package's own derivation beats the raw payload."""
        assert resolve_claim("fullname", CLAIMS) == "Ada Lovelace"

    def test_falls_through_to_raw(self):
        """A key the normalization does not produce still resolves."""
        assert resolve_claim("login", CLAIMS) == "ada"

    def test_empty_normalized_falls_through_to_raw(self):
        """A blank normalized value is not an answer."""
        # ``username`` is normalized to "" here while the raw payload has a
        # usable ``login``; mapping ``username`` must not yield "".
        assert resolve_claim("username", CLAIMS) is None

    def test_dotted_path_reaches_into_raw(self):
        """Nesting is addressed by path rather than by a nested map."""
        assert resolve_claim("address.formatted", CLAIMS) == "London"

    def test_unknown_path_is_none(self):
        assert resolve_claim("nope.not.here", CLAIMS) is None

    def test_empty_path_is_none(self):
        assert resolve_claim("", CLAIMS) is None

    def test_path_through_a_non_mapping_is_none(self):
        """Walking into a string must not raise."""
        assert resolve_claim("email.something", CLAIMS) is None

    def test_empty_leaf_is_none(self):
        assert resolve_claim("address.country", CLAIMS) is None

    def test_non_string_value_survives(self):
        assert resolve_claim("groups", CLAIMS) == ["staff", "math"]

    def test_missing_raw_is_tolerated(self):
        """Claims built by hand need not carry a raw payload."""
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
