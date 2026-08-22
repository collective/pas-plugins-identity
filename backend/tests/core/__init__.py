"""Helpers shared across the core layer's tests."""

from pas.plugins.identity.core.interfaces import JSONDict
from ZPublisher.HTTPRequest import HTTPRequest

import json


def body(request: HTTPRequest, data: JSONDict) -> None:
    """Put a JSON body on a request.

    :param request: The request to write to.
    :param data: The body payload.
    """
    request.set("BODY", json.dumps(data))
