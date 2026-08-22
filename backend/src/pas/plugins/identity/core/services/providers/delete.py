"""``DELETE @identity-providers/<id>`` -- remove a provider."""

from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.services.providers import ProvidersService


class ProvidersDelete(ProvidersService):
    """Remove a provider record."""

    def reply(self) -> JSONDict:
        """Remove a provider record.

        The identities already stored against it are deliberately left alone:
        deleting a provider is a configuration change, and silently dropping
        every account that logs in through it is not something a control
        panel should do without being asked.

        :returns: No content on success, or an error body.
        """
        refusal = self._refuse_unless_manager()
        if refusal is not None:
            return refusal
        self._disable_csrf()

        if len(self.segments) != 1:
            return self._error(400, "Bad request", "Expected @identity-providers/<id>")
        providers = get_providers()
        remaining = [p for p in providers if p.provider_id != self.segments[0]]
        if len(remaining) == len(providers):
            return self._error(404, "Unknown provider", repr(self.segments[0]))

        set_providers(remaining)
        return self.reply_no_content()
