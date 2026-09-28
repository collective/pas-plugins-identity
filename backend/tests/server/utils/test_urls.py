"""Building the URL a client's redirect URI answers with.

RFC 6749, section 3.1.2: a query already in the redirection endpoint "MUST be
retained when adding additional query parameters". What is asserted here is
that the registered URI comes back exactly as it was written, with the
response added to it and nothing else touched.
"""

from pas.plugins.identity.server.utils.urls import redirect_with
from urllib.parse import parse_qsl
from urllib.parse import urlsplit

import pytest


class TestWithoutAQuery:
    def test_the_parameters_become_the_query(self):
        url = redirect_with("https://app.example.org/cb", {"code": "abc"})

        assert url == "https://app.example.org/cb?code=abc"

    def test_several_parameters_keep_their_order(self):
        url = redirect_with(
            "https://app.example.org/cb", {"code": "abc", "state": "xyz"}
        )

        assert url == "https://app.example.org/cb?code=abc&state=xyz"

    def test_a_trailing_question_mark_is_not_doubled(self):
        """An empty query is still no query."""
        url = redirect_with("https://app.example.org/cb?", {"code": "abc"})

        assert url == "https://app.example.org/cb?code=abc"

    def test_no_parameters_leave_the_uri_alone(self):
        assert redirect_with("https://app.example.org/cb", {}) == (
            "https://app.example.org/cb"
        )


class TestWithAQuery:
    def test_the_parameters_are_added_to_it(self):
        url = redirect_with(
            "https://stats.example.org/index.php"
            "?module=RebelOIDC&action=callback&provider=oidc",
            {"code": "abc", "state": "xyz"},
        )

        assert url == (
            "https://stats.example.org/index.php"
            "?module=RebelOIDC&action=callback&provider=oidc&code=abc&state=xyz"
        )

    @pytest.mark.parametrize(
        "query",
        [
            "next=/home",
            "q=a%20b",
            "flag",
            "empty=",
        ],
    )
    def test_the_registered_query_is_kept_verbatim(self, query):
        """Not parsed and re-encoded: the client compares against what it
        registered, and a round trip through parse_qsl and urlencode changes
        every one of these."""
        uri = f"https://app.example.org/cb?{query}"

        url = redirect_with(uri, {"code": "abc"})

        assert url == f"{uri}&code=abc"

    def test_a_parameter_the_query_already_has_is_not_replaced(self):
        """Replacing the client's own value would be interpreting a query
        that belongs to it; the response is added and both are kept."""
        url = redirect_with(
            "https://app.example.org/cb?state=theirs", {"state": "ours"}
        )

        assert parse_qsl(urlsplit(url).query) == [
            ("state", "theirs"),
            ("state", "ours"),
        ]


class TestEncoding:
    def test_values_are_encoded(self):
        url = redirect_with(
            "https://app.example.org/cb",
            {"error_description": "a & b = c?", "state": "opaque value"},
        )

        assert dict(parse_qsl(urlsplit(url).query)) == {
            "error_description": "a & b = c?",
            "state": "opaque value",
        }

    def test_an_encoded_value_cannot_break_out_of_its_parameter(self):
        url = redirect_with("https://app.example.org/cb", {"state": "x&code=forged"})

        assert parse_qsl(urlsplit(url).query) == [("state", "x&code=forged")]


class TestTheRestOfTheUri:
    @pytest.mark.parametrize(
        "uri",
        [
            "https://app.example.org:8443/cb",
            "http://127.0.0.1:53412/callback",
            "com.example.app:/oauth2redirect",
            "https://app.example.org/a%20path/cb",
        ],
    )
    def test_scheme_host_port_and_path_are_untouched(self, uri):
        url = redirect_with(uri, {"code": "abc"})

        assert url == f"{uri}?code=abc"
