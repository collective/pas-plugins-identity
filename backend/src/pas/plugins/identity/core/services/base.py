"""Shared plumbing for this package's REST services."""

from pas.plugins.identity.core.interfaces import JSONDict
from plone.restapi.services import Service
from Products.CMFPlone.Portal import PloneSite
from ZPublisher.HTTPRequest import HTTPRequest


class IdentityService(Service):
    """Base for the login-flow services.

    Carries an explicit ``__init__``. ``plone.rest`` mixes ``BrowserView``
    into the class it publishes, so the registered service would get one
    either way -- but the factory class on its own would not, and a service
    that cannot be constructed directly cannot be tested without standing up
    the publisher.
    """

    def __init__(self, context: PloneSite, request: HTTPRequest) -> None:
        """Bind the service to its context and request.

        :param context: The context the service was traversed on.
        :param request: The current request.
        """
        self.context = context
        self.request = request

    def _error(self, status: int, kind: str, message: str) -> JSONDict:
        """Set a response status and render an error body.

        :param status: HTTP status to answer with.
        :param kind: Short error type.
        :param message: Human readable detail.
        :returns: The error body.
        """
        self.request.response.setStatus(status)
        return {"error": {"type": kind, "message": message}}
