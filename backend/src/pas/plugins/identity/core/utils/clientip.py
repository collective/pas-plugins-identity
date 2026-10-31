"""Who is on the other end of a request.

Two things ask: the audit log, which records the address when a site opts in,
and the magic-link rate limit, which counts sends against it. They ask here so
that they cannot disagree.

**A request header is client input until something vouches for it.** Anybody
can send ``CF-Connecting-IP`` or ``X-Forwarded-For`` to a site that sits behind
no proxy at all, or directly to the origin of one that does. Believing such a
header lets that caller write any address into the audit log, and take a fresh
rate-limit bucket on every request. So the headers read are the ones the site
names in ``client_ip_headers``, which is an operator saying that their proxy
sets them and that nobody reaches the site around that proxy.

A site that names none gets ``X-Forwarded-For``, since most sites run behind a
proxy that appends to it and would otherwise see every visitor as that proxy.
That default is the one place a header is believed unvouched for, and a site
reachable without a proxy has to name a header or set ``trusted-proxy``.

Zope's ``trusted-proxy`` setting takes the default's place when it is set: it
reads the same header, and skips every proxy it knows of rather than taking the
last entry. The answer is then :meth:`HTTPRequest.getClientAddr`, which is also
the answer when a request has none of the headers read.
"""

from plone import api
from ZPublisher import HTTPRequest as publisher
from ZPublisher.HTTPRequest import HTTPRequest

import re


#: The registry record naming the headers to believe.
HEADERS_RECORD = "pas.plugins.identity.client_ip_headers"

#: What a site that names no headers gets.
DEFAULT_HEADERS = ("X-Forwarded-For",)

#: Letters, digits and hyphens. An underscore is a legal header character and
#: is refused anyway: WSGI folds ``-`` and ``_`` into the same environ key, so
#: a client could answer for a name with an underscore by sending the hyphen.
_HEADER_NAME = re.compile(r"^[A-Za-z0-9]+(-[A-Za-z0-9]+)*$")


def is_header_name(value: object) -> bool:
    """Report whether a value can name a request header.

    The field's constraint, and the check :func:`client_ip` makes on what it
    reads: a registry record does not keep a field's constraint, so the form
    is not the only way a value gets there.

    :param value: A candidate header name.
    :returns: Whether it is letters and digits separated by single hyphens.
    """
    return isinstance(value, str) and bool(_HEADER_NAME.match(value))


def _environ_key(header: str) -> str:
    """Return the WSGI environ key a request header arrives under.

    :param header: A header name, in any case.
    :returns: The key, such as ``HTTP_CF_CONNECTING_IP``.
    """
    return f"HTTP_{header.upper().replace('-', '_')}"


def client_ip(request: HTTPRequest) -> str:
    """Return the address of whoever sent a request.

    A header listing several addresses answers with its **last**. Each proxy
    appends the peer it saw, so the entries before the last came from further
    out, and the leftmost is whatever the client chose to send.

    :param request: The current request.
    :returns: The value of the first header read that has one, failing that
        :meth:`HTTPRequest.getClientAddr`, or an empty string when there is
        none.
    """
    headers = api.portal.get_registry_record(HEADERS_RECORD, default=()) or ()
    if not headers and not publisher.trusted_proxies:
        headers = DEFAULT_HEADERS
    for header in headers:
        if not is_header_name(header):
            continue
        value = request.environ.get(_environ_key(header), "")
        address = value.rsplit(",", 1)[-1].strip()
        if address:
            return address
    return request.getClientAddr() or ""
