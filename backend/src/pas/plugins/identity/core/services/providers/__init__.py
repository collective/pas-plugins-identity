"""``@identity-providers`` and ``@identity-drivers`` -- the control panel API.

The Volto control-panel widget is generated from driver metadata rather than
hand-written per provider, so there are two endpoints: one that describes
what a driver needs, and one that manages the provider records themselves.

``GET @identity-drivers``
    Every registered driver and its config schema. This is what the widget
    renders a form from.

``GET @identity-providers`` / ``GET @identity-providers/<id>``
``POST @identity-providers``
``PATCH @identity-providers/<id>``
``DELETE @identity-providers/<id>``
``POST @identity-providers/<id>/test-connection``

Everything here needs ``Manage portal``. Secrets are write-only through all of
it: what leaves is masked, and a PATCH echoing the mask back leaves the stored
value alone.
"""

from pas.plugins.identity.core.controlpanel import ProviderConfig
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

#: Path segment that runs the per-provider connection check.
TEST_ACTION = "test-connection"


class ControlPanelService(IdentityService):
    """Shared guard: none of this is readable without Manage portal."""

    def _refuse_unless_manager(self) -> JSONDict | None:
        """Return an error body unless the caller may manage the site.

        Provider configuration names the site's identity providers and, for a
        misconfigured driver, could carry a secret. It is not public.

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


@implementer(IPublishTraverse)
class ProvidersService(ControlPanelService):
    """Base for the provider CRUD verbs."""

    def __init__(self, context: PloneSite, request: HTTPRequest) -> None:
        """Bind the service and prepare to consume path segments.

        :param context: The context the service was traversed on.
        :param request: The current request.
        """
        super().__init__(context, request)
        self.segments: list[str] = []

    def publishTraverse(self, request: HTTPRequest, name: str) -> "ProvidersService":
        """Collect ``<id>`` and any action from the URL.

        :param request: The current request.
        :param name: The next path segment.
        :returns: This service.
        """
        self.segments.append(name)
        return self

    def _base(self) -> str:
        """Return this service's canonical URL.

        :returns: The URL.
        """
        return f"{self.context.absolute_url()}/@identity-providers"

    def _render(self, provider: ProviderConfig) -> JSONDict:
        """Render one provider for an API response.

        :param provider: The provider.
        :returns: JSON-ready mapping, secrets masked.
        """
        payload = provider.serialize()
        payload["@id"] = f"{self._base()}/{provider.provider_id}"
        return payload
