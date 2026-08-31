"""What a client may be registered with, and what is refused.

Until this existed, ``POST @identity-clients`` stored ``redirect_uris``
exactly as it received them. No scheme check, no rejection of fragments, no
loopback rule -- so a ``javascript:`` URI could be registered and would later
be handed to a browser redirect at the end of an authorization flow. Found in
the review Érico asked for (2026-08-29) and the most serious thing in it.

The rules live on the schema field, so every route in is held to them: the
endpoint, a GenericSetup profile, the demo's own setup handler, and a test.
The two classes below are the two halves of that -- the rule itself, and the
proof that assignment cannot get around it.
"""

from pas.plugins.identity.server.controlpanel.clients import ClientConfig
from pas.plugins.identity.server.controlpanel.interfaces import is_redirect_uri
from pas.plugins.identity.server.interfaces import ServerError
from zope.interface import Invalid

import pytest


#: Every shape this server will send a browser to.
ACCEPTED = [
    "https://app.example.com/callback",
    "https://app.example.com:8443/callback?next=1",
    "http://127.0.0.1:8080/callback",
    "http://[::1]:8080/callback",
    "http://localhost:3000/login-identity",
    # RFC 6761 reserves the whole `.localhost` name space to loopback, which
    # is what this package's own federation demo runs on.
    "http://plone.localhost/login-identity",
    "http://id.localhost:8081/login-identity",
    # RFC 8252's private-use scheme, which is how a native app comes back.
    "com.example.app:/oauth2redirect",
    # The two wildcard positions, so a site does not register its hosts one
    # by one. What each one covers is TestWildcardMatching, next door.
    "https://*.example.com/callback",
    "https://app.example.com/*",
    "https://*.example.com/*",
    "https://app.example.com/console/*",
]

#: Every shape it will not, and what is wrong with each.
REFUSED = [
    ("javascript:alert(document.cookie)", "executable in a browser"),
    ("data:text/html,<script>1</script>", "executable in a browser"),
    ("vbscript:msgbox(1)", "executable in a browser"),
    ("http://evil.example.com/callback", "plain HTTP off the loopback"),
    ("https://app.example.com/cb#fragment", "carries a fragment"),
    # A wildcard is allowed in two positions and refused everywhere else.
    ("https://*.com/cb", "wildcard directly under a public suffix"),
    ("https://a*.example.com/cb", "wildcard that is only part of a label"),
    ("https://*.*.example.com/cb", "two host wildcards"),
    ("https://app.example.com/*/cb", "wildcard in the middle of a path"),
    ("https://app.example.com/*/*", "two path wildcards"),
    ("https://app.example.com/cb?next=*", "wildcard in a query string"),
    ("https://*.example.com:*/cb", "wildcard in a port"),
    ("https://*@example.com/cb", "wildcard in a user name"),
    ("/relative/callback", "not absolute"),
    ("https:///callback", "names no host"),
    ("", "empty"),
]


class TestTheRule:
    """The constraint on its own, which is where the reasons live."""

    @pytest.mark.parametrize("uri", ACCEPTED)
    def test_accepted(self, uri: str):
        """Anything a real client legitimately comes back to."""
        assert is_redirect_uri(uri) is True

    @pytest.mark.parametrize(
        "uri,why", REFUSED, ids=[u or "empty" for u, _w in REFUSED]
    )
    def test_refused(self, uri: str, why: str):
        """Each of these used to be stored without a word."""
        with pytest.raises(Invalid):
            is_redirect_uri(uri)

    def test_the_refusal_says_what_is_wrong(self):
        """An operator who pasted a URL with a fragment has to be able to see
        that the fragment is the problem."""
        with pytest.raises(Invalid) as caught:
            is_redirect_uri("https://app.example.com/cb#x")

        assert "fragment" in str(caught.value)

    def test_a_misplaced_wildcard_says_where_it_may_go(self):
        """The operator pasted the shape every other provider uses. Saying
        "invalid" would leave them guessing which half was wrong."""
        with pytest.raises(Invalid) as caught:
            is_redirect_uri("https://a*.example.com/cb")

        assert "leftmost label" in str(caught.value)

    def test_a_public_suffix_wildcard_is_refused(self):
        """``https://*.com`` is every site on the internet with a `.com`
        name, which is not a widening anybody means to ask for."""
        with pytest.raises(Invalid) as caught:
            is_redirect_uri("https://*.com/cb")

        assert "registered domain" in str(caught.value)


class TestNoWayRound:
    """A rule only the constructor enforces is a rule with a door in it."""

    def test_construction_refuses(self):
        """The route the registration endpoint takes."""
        with pytest.raises(ServerError):
            ClientConfig("c", redirect_uris=["javascript:alert(1)"])

    def test_assignment_refuses(self):
        """The route the demo's own setup handler takes, and the reason
        ``redirect_uris`` is a property rather than an attribute."""
        client = ClientConfig("c", redirect_uris=["https://ok.example.com/cb"])

        with pytest.raises(ServerError):
            client.redirect_uris = ["http://evil.example.com/cb"]

    def test_the_good_ones_survive_both(self):
        """The rule refuses; it does not mangle."""
        client = ClientConfig("c", redirect_uris=["https://a.example.com/cb"])
        client.redirect_uris = ["https://b.example.com/cb", "com.example.app:/cb"]

        assert client.redirect_uris == [
            "https://b.example.com/cb",
            "com.example.app:/cb",
        ]


class TestGrants:
    """A grant nothing implements used to be stored and then refused at the
    token endpoint, where it reads as a client bug."""

    def test_an_unimplemented_grant_is_refused(self):
        with pytest.raises(ServerError) as caught:
            ClientConfig("c", grant_types=["password"])

        assert "password" in str(caught.value)

    def test_the_refusal_names_what_is_served(self):
        """So the operator does not have to go and read discovery."""
        with pytest.raises(ServerError) as caught:
            ClientConfig("c", grant_types=["implicit"])

        assert "authorization_code" in str(caught.value)

    def test_saying_nothing_means_the_code_grant(self):
        """Which is what a client that names no grant wants."""
        assert ClientConfig("c").grant_types == ["authorization_code"]

    @pytest.mark.parametrize(
        "grant", ["authorization_code", "client_credentials", "refresh_token"]
    )
    def test_every_advertised_grant_is_registrable(self, grant: str):
        """Discovery advertises three; a registration must accept all three,
        or the document is a promise the panel cannot keep."""
        assert ClientConfig("c", grant_types=[grant]).grant_types == [grant]
