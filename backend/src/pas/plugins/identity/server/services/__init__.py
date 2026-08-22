"""The authorization server's admin API.

``@identity-providers`` manages who this site lets people log in *with*. This
is the other direction: who is allowed to log in *to* it, and what this server
signs with.

``GET @identity-clients`` / ``GET @identity-clients/<id>``
``POST @identity-clients``
``POST @identity-clients/<id>/rotate-secret``
``PATCH @identity-clients/<id>``
``DELETE @identity-clients/<id>``
``GET @identity-keys``
``POST @identity-keys/rotate``

Everything here needs ``Manage portal``, and everything is bound to the
``[server]`` browser layer, so a site that never switched the authorization
server on does not publish an endpoint for managing one.

The secret handling is the part that differs from the provider API, and the
difference is deliberate. A provider's secret is *masked*: this package is the
client there, has to keep sending it, and a round trip that echoes the mask
back leaves the stored value alone. Here this package is the server, and S8
says store a hash -- so there is nothing to mask and nothing to echo. A secret
exists exactly once, in the response that mints it, and is unrecoverable
afterwards. An operator who loses it rotates.
"""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.services.base import IdentityService
from plone import api
from Products.CMFPlone.Portal import PloneSite
from zope.interface import alsoProvides
from zope.interface import implementer
from zope.publisher.interfaces import IPublishTraverse
from ZPublisher.HTTPRequest import HTTPRequest

import plone.protect.interfaces


#: Permission every one of these endpoints requires.
MANAGE_PERMISSION = "Manage portal"

#: Path segment that mints a client a new secret.
ROTATE_SECRET_ACTION = "rotate-secret"  # noqa: S105 - a URL segment

#: Path segment that rotates the signing key.
ROTATE_KEY_ACTION = "rotate"


@implementer(IPublishTraverse)
class ServerAdminService(IdentityService):
    """Shared guard and traversal for the authorization server's admin API."""

    def __init__(self, context: PloneSite, request: HTTPRequest) -> None:
        """Bind the service and prepare to consume path segments.

        :param context: The context the service was traversed on.
        :param request: The current request.
        """
        super().__init__(context, request)
        self.segments: list[str] = []

    def publishTraverse(self, request: HTTPRequest, name: str) -> "ServerAdminService":
        """Collect ``<id>`` and any action from the URL.

        :param request: The current request.
        :param name: The next path segment.
        :returns: This service.
        """
        self.segments.append(name)
        return self

    def _refuse_unless_manager(self) -> JSONDict | None:
        """Return an error body unless the caller may manage the site.

        A client registration names who may obtain tokens for this site's
        users. Reading it is not public and writing it certainly is not.

        :returns: The error body, or ``None`` when the caller is allowed.
        """
        if api.user.is_anonymous():
            return self._error(401, "Not authenticated", "Log in first.")
        if not api.user.has_permission(MANAGE_PERMISSION):
            return self._error(
                403, "Not allowed", f"Needs the {MANAGE_PERMISSION!r} permission."
            )
        return None

    def _disable_csrf(self) -> None:
        """Exempt a write from plone.protect's form authenticator."""
        alsoProvides(self.request, plone.protect.interfaces.IDisableCSRFProtection)
