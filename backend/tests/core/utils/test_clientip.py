"""Which address a request is attributed to, and whose word that takes."""

from io import BytesIO
from pas.plugins.identity.core.utils.clientip import client_ip
from pas.plugins.identity.core.utils.clientip import HEADERS_RECORD
from pas.plugins.identity.core.utils.clientip import is_header_name
from plone import api
from ZPublisher import HTTPRequest as publisher
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse

import pytest


#: The proxy in front of the site, as the socket sees it.
PROXY = "10.0.0.1"

#: The visitor.
VISITOR = "203.0.113.7"

#: Somebody else's address, as a client would forge it.
FORGED = "198.51.100.9"


def make_request(**headers: str) -> HTTPRequest:
    """Return a request built the way the publisher builds one.

    ``getClientAddr`` is settled in the constructor, so the environ has to be
    complete before the request exists.

    :param headers: Environ keys and their values.
    :returns: The request.
    """
    environ = {"SERVER_NAME": "nohost", "SERVER_PORT": "80", "REMOTE_ADDR": PROXY}
    environ.update(headers)
    return HTTPRequest(BytesIO(), environ, HTTPResponse())


class TestClientIp:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def configure(self, *headers: str) -> None:
        """Name the headers the site believes.

        :param headers: Header names, in order.
        """
        api.portal.set_registry_record(HEADERS_RECORD, headers)

    def test_no_header_is_believed_by_default(self):
        """The reason the setting exists: left alone, a client's headers
        decide nothing."""
        request = make_request(
            HTTP_X_FORWARDED_FOR=FORGED, HTTP_CF_CONNECTING_IP=FORGED
        )

        assert client_ip(request) == PROXY

    def test_a_named_header_is_believed(self):
        self.configure("CF-Connecting-IP")

        assert client_ip(make_request(HTTP_CF_CONNECTING_IP=VISITOR)) == VISITOR

    def test_only_a_named_header_is_believed(self):
        self.configure("CF-Connecting-IP")

        assert client_ip(make_request(HTTP_X_FORWARDED_FOR=FORGED)) == PROXY

    def test_the_first_header_present_wins(self):
        """Cloudflare's overwrite mode keeps a visitor's real IPv6 address
        apart from the one in ``CF-Connecting-IP``."""
        self.configure("CF-Connecting-IPv6", "CF-Connecting-IP")
        request = make_request(
            HTTP_CF_CONNECTING_IPV6="2001:db8::7", HTTP_CF_CONNECTING_IP=VISITOR
        )

        assert client_ip(request) == "2001:db8::7"

    def test_a_missing_header_gives_way_to_the_next(self):
        self.configure("CF-Connecting-IPv6", "CF-Connecting-IP")

        assert client_ip(make_request(HTTP_CF_CONNECTING_IP=VISITOR)) == VISITOR

    def test_the_last_entry_of_a_list_is_taken(self):
        """A proxy appends the peer it saw, so the leftmost entry is whatever
        the client sent. Reading that one is how a rate limit gets a fresh
        bucket per request."""
        self.configure("X-Forwarded-For")
        request = make_request(HTTP_X_FORWARDED_FOR=f"{FORGED}, {VISITOR}")

        assert client_ip(request) == VISITOR

    def test_an_empty_header_falls_back(self):
        self.configure("CF-Connecting-IP")

        assert client_ip(make_request(HTTP_CF_CONNECTING_IP=" ")) == PROXY

    def test_a_name_that_is_no_header_is_skipped(self):
        """A record does not keep its field's constraint, so a value set
        around the form has to be harmless too."""
        self.configure("REMOTE ADDR")

        assert client_ip(make_request()) == PROXY

    def test_zopes_trusted_proxy_setting_is_honoured(self, monkeypatch):
        """Without a header named here, Zope's own setting still answers."""
        monkeypatch.setattr(publisher, "trusted_proxies", [PROXY])

        assert client_ip(make_request(HTTP_X_FORWARDED_FOR=VISITOR)) == VISITOR

    def test_no_address_at_all(self):
        request = make_request()
        request._client_addr = ""

        assert client_ip(request) == ""


class TestIsHeaderName:
    @pytest.mark.parametrize(
        "value", ["CF-Connecting-IP", "cf-connecting-ipv6", "X-Forwarded-For", "Via"]
    )
    def test_accepted(self, value: str):
        assert is_header_name(value) is True

    @pytest.mark.parametrize(
        "value",
        ["", " ", "X_Forwarded_For", "X-Forwarded-For:", "-X", "X-", "A--B", None, 1],
    )
    def test_refused(self, value: object):
        assert is_header_name(value) is False
