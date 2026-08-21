"""``@login-providers`` -- what the user can log in with, and how to start.

Two shapes, deliberately:

``GET @login-providers``
    Lists the enabled providers. Cheap and side-effect free, which matters
    because a login page renders it on every visit.

``GET @login-providers/<id>``
    Starts a flow against one provider and answers with the URL to send the
    browser to. This is where the ``state``, PKCE verifier and nonce are
    minted and stored, so it must not be folded into the listing: doing so
    would mint an attempt per provider on every page load.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.controlpanel import enabled_providers
from pas.plugins.identity.core.controlpanel import get_callback_url
from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.flows import FlowManager
from pas.plugins.identity.core.flows.metadata import metadata_for
from pas.plugins.identity.core.flows.session import FlowSession
from pas.plugins.identity.core.interfaces import FlowError
from pas.plugins.identity.core.services.base import IdentityService
from plone import api
from typing import Any
from zope.interface import implementer
from zope.publisher.interfaces import IPublishTraverse


@implementer(IPublishTraverse)
class LoginProviders(IdentityService):
    """List the providers, or start a flow against one of them."""

    def __init__(self, context: Any, request: Any) -> None:
        """Bind the service and prepare to consume a path segment.

        :param context: The context the service was traversed on.
        :param request: The current request.
        """
        super().__init__(context, request)
        self.provider_id: str | None = None

    def publishTraverse(self, request: Any, name: str) -> "LoginProviders":
        """Consume ``<id>`` from the URL.

        :param request: The current request.
        :param name: The next path segment.
        :returns: This service.
        """
        self.provider_id = name
        return self

    def reply(self) -> dict[str, Any]:
        """Answer the request.

        :returns: The provider listing, or the authorize URL for one provider.
        """
        if self.provider_id is None:
            return self._listing()
        return self._start()

    # ------------------------------------------------------------------
    # GET @login-providers
    # ------------------------------------------------------------------

    def _listing(self) -> dict[str, Any]:
        """Return the providers a user may log in with.

        No secrets and no configuration leave here (I4): a login button needs
        an id, a label and somewhere to click.

        :returns: The listing.
        """
        base = f"{self.context.absolute_url()}/@login-providers"
        return {
            "@id": base,
            "items": [
                {
                    "@id": f"{base}/{provider.provider_id}",
                    "id": provider.provider_id,
                    "title": provider.title,
                    "driver": provider.driver_id,
                }
                for provider in enabled_providers()
            ],
        }

    # ------------------------------------------------------------------
    # GET @login-providers/<id>
    # ------------------------------------------------------------------

    def _start(self) -> dict[str, Any]:
        """Start a flow and return where to send the browser.

        :returns: The authorize URL, or an error body.
        """
        provider = get_provider(self.provider_id)
        if provider is None or not provider.enabled or provider.driver is None:
            # One answer for "no such provider" and "disabled": which
            # providers a site has configured is not worth probing for.
            return self._error(404, "Unknown provider", f"{self.provider_id!r}")

        came_from = self.request.form.get("came_from", "")
        try:
            metadata = metadata_for(provider)
            authorize_url = self._manager().start(
                provider,
                get_callback_url(),
                metadata,
                came_from=came_from,
            )
        except FlowError as exc:
            logger.info(
                "Refusing to start a flow for %r: %s", provider.provider_id, exc
            )
            return self._error(502, "Provider unavailable", str(exc))

        base = f"{self.context.absolute_url()}/@login-providers"
        return {
            "@id": f"{base}/{provider.provider_id}",
            "provider": provider.provider_id,
            "authorize_url": authorize_url,
        }

    def _manager(self) -> FlowManager:
        """Return a flow manager bound to this request.

        :returns: The manager.
        """
        return FlowManager(FlowSession(self.request), api.portal.get().absolute_url())
