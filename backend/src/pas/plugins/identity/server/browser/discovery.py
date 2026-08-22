"""Discovery and the JWKS, published for relying parties to fetch.

Both are anonymous, cacheable and entirely public. That is not an oversight:
the discovery document describes endpoints a client is about to be sent to
anyway, and the JWKS is the *public* half of the signing ring, whose whole
purpose is to be fetched by strangers.

``/.well-known/`` needs a traversal stub because the path has a segment
separator in it. A view cannot be registered under a name containing a slash,
so ``.well-known`` is the view and the document name is traversed into it.
"""

from pas.plugins.identity.server.discovery import DISCOVERY_DOCUMENT
from pas.plugins.identity.server.discovery import metadata
from pas.plugins.identity.server.discovery import WELL_KNOWN
from pas.plugins.identity.server.interfaces import ServerError
from pas.plugins.identity.server.keys import public_jwks
from Products.Five.browser import BrowserView
from zExceptions import NotFound
from zope.interface import implementer
from zope.publisher.interfaces import IPublishTraverse

import json


class JSONView(BrowserView):
    """A view that answers a JSON document to anybody who asks."""

    #: Seconds a relying party may cache the answer. Both documents change
    #: only when an operator changes configuration or rotates a key, and a
    #: client that re-fetched them per request would make its own login path
    #: depend on this server being fast.
    max_age = 3600

    def document(self):
        """Return the document to serialize.

        :returns: A JSON-ready mapping.
        :raises NotImplementedError: In this base class.
        """
        raise NotImplementedError

    def __call__(self) -> str:
        """Serialize the document.

        :returns: The JSON body, or an error body when the server is not
            configured well enough to describe itself.
        """
        response = self.request.response
        response.setHeader("Content-Type", "application/json")
        try:
            body = self.document()
        except ServerError as exc:
            # An unconfigured server answering 500 would look like a bug in
            # this package to whoever is trying to integrate against it. It
            # is a site that has not finished being set up, and saying so is
            # the difference between a five-minute fix and a bug report.
            response.setStatus(503)
            return json.dumps({"error": "server_not_configured", "detail": str(exc)})
        response.setHeader("Cache-Control", f"public, max-age={self.max_age}")
        return json.dumps(body)


class DiscoveryView(JSONView):
    """``/.well-known/openid-configuration``."""

    def document(self):
        """Return the OpenID provider metadata.

        :returns: The discovery document.
        """
        return metadata()


class JWKSView(JSONView):
    """The public signing keys.

    Every key in the ring is published, not only the one currently signing: a
    relying party holding a token minted before the last rotation still has to
    be able to verify it, and it finds the right one by ``kid``.
    """

    def document(self):
        """Return the JWKS.

        :returns: ``{"keys": [...]}``.
        """
        return public_jwks()


@implementer(IPublishTraverse)
class WellKnownView(BrowserView):
    """Traversal stub for ``/.well-known/<document>``.

    Only the documents this server actually publishes are reachable. An
    unknown name is a 404 rather than an empty document, because a relying
    party that asked for something else should discover that plainly instead
    of parsing a helpful-looking blank.
    """

    #: Document name to the view that renders it.
    documents = {DISCOVERY_DOCUMENT: DiscoveryView}  # noqa: RUF012

    def publishTraverse(self, request, name: str):
        """Traverse to a well-known document.

        :param request: The current request.
        :param name: The next path segment.
        :returns: The view rendering that document.
        :raises NotFound: When nothing is published under that name.
        """
        view = self.documents.get(name)
        if view is None:
            raise NotFound(self.context, name, request)
        return view(self.context, request)

    def __call__(self) -> str:
        """Refuse a bare ``/.well-known/``.

        :returns: Never; the directory itself is not a document.
        :raises NotFound: Always.
        """
        raise NotFound(self.context, WELL_KNOWN, self.request)
