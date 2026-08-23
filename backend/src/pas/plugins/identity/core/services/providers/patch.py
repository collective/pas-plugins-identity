"""``PATCH @identity-providers/<id>`` -- update in place."""

from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.controlpanel import unmask
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.services.providers import ProvidersService
from plone.restapi.deserializer import json_body


class ProvidersPatch(ProvidersService):
    """Apply a partial update to one provider."""

    def reply(self) -> JSONDict:
        """Apply a partial update.

        :returns: No content on success, or an error body.
        """
        refusal = self._refuse_unless_manager()
        if refusal is not None:
            return refusal
        self._disable_csrf()

        if len(self.segments) != 1:
            return self._error(400, "Bad request", "Expected @identity-providers/<id>")
        providers = get_providers()
        target = next((p for p in providers if p.provider_id == self.segments[0]), None)
        if target is None:
            return self._error(404, "Unknown provider", repr(self.segments[0]))

        data = json_body(self.request)
        if "title" in data:
            target.title = data["title"]
        if "enabled" in data:
            target.enabled = bool(data["enabled"])
        if "propertymap" in data:
            target.propertymap = dict(data["propertymap"] or {})
        if "config" in data:
            # A round trip echoes the mask back, and that must not overwrite
            # the stored secret with a row of bullets.
            target.config = unmask(target.driver_id, data["config"], target.config)

        set_providers(providers)
        return self.reply_no_content()
