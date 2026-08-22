"""``POST @identities`` -- start a linking flow."""

from pas.plugins.identity import logger
from pas.plugins.identity.core.controlpanel import get_callback_url
from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.flows import FlowManager
from pas.plugins.identity.core.flows.metadata import metadata_for
from pas.plugins.identity.core.flows.session import FlowSession
from pas.plugins.identity.core.interfaces import FlowError
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.services.identities import IdentitiesBase
from plone import api
from plone.restapi.deserializer import json_body


class IdentitiesPost(IdentitiesBase):
    """Start a flow that links another provider to the caller's account."""

    def reply(self) -> JSONDict:
        """Start a flow that will link a provider to the caller's account.

        :returns: The authorize URL, or an error body.
        """
        self._disable_csrf()
        userid = self._userid()
        if userid is None:
            # A linking flow may not even be *started* anonymously.
            return self._error(401, "Not authenticated", "Log in first.")

        data = json_body(self.request)
        provider_id = data.get("provider")
        if not provider_id:
            return self._error(400, "Missing parameters", "Required: provider")

        provider = get_provider(provider_id)
        if provider is None or not provider.enabled or provider.driver is None:
            return self._error(404, "Unknown provider", repr(provider_id))

        try:
            manager = FlowManager(
                FlowSession(self.request), api.portal.get().absolute_url()
            )
            authorize_url = manager.start(
                provider,
                get_callback_url(),
                metadata_for(provider),
                came_from=data.get("came_from", ""),
                link_for=userid,
            )
        except FlowError as exc:
            logger.info("Refusing to start a link for %r: %s", provider_id, exc)
            return self._error(502, "Provider unavailable", str(exc))

        return {"provider": provider_id, "authorize_url": authorize_url}
