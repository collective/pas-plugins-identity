"""Shared plumbing for this package's REST services."""

from plone.restapi.services import Service
from typing import Any


class IdentityService(Service):
    """Base for the login-flow services.

    Carries an explicit ``__init__``. ``plone.rest`` mixes ``BrowserView``
    into the class it publishes, so the registered service would get one
    either way -- but the factory class on its own would not, and a service
    that cannot be constructed directly cannot be tested without standing up
    the publisher.
    """

    def __init__(self, context: Any, request: Any) -> None:
        """Bind the service to its context and request.

        :param context: The context the service was traversed on.
        :param request: The current request.
        """
        self.context = context
        self.request = request

    def _error(self, status: int, kind: str, message: str) -> dict[str, Any]:
        """Set a response status and render an error body.

        :param status: HTTP status to answer with.
        :param kind: Short error type.
        :param message: Human readable detail.
        :returns: The error body.
        """
        self.request.response.setStatus(status)
        return {"error": {"type": kind, "message": message}}
