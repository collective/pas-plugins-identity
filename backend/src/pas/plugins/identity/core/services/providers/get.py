"""``GET @identity-providers`` -- list, or read one."""

from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.services.providers import ProvidersService


class ProvidersGet(ProvidersService):
    """Read the configured providers."""

    def reply(self) -> JSONDict:
        """Return the configured providers.

        :returns: The listing or one provider, or an error body.
        """
        refusal = self._refuse_unless_manager()
        if refusal is not None:
            return refusal

        if not self.segments:
            return {
                "@id": self._base(),
                "items": [self._render(p) for p in get_providers()],
            }

        provider = get_provider(self.segments[0])
        if provider is None:
            return self._error(404, "Unknown provider", repr(self.segments[0]))
        return self._render(provider)
