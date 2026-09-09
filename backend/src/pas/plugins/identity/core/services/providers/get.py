"""``GET @identity-providers`` -- list, read one, or export one."""

from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel.export import fragment_filename
from pas.plugins.identity.core.controlpanel.export import provider_fragment
from pas.plugins.identity.core.controlpanel.interfaces import IProviderRecords
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.services.providers import EXPORT_ACTION
from pas.plugins.identity.core.services.providers import ProvidersService
from pas.plugins.identity.core.services.schema import jsonschema_for


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
                # The provider's own fields, serialized from
                # `IProviderRecords` -- the same interface its registry
                # records are bound to, so the form and the storage cannot
                # describe different things. The driver's half comes from
                # `@identity-drivers`, and the panel renders the two together.
                "schema": jsonschema_for(IProviderRecords, self.context, self.request),
            }

        provider = get_provider(self.segments[0])
        if provider is None:
            return self._error(404, "Unknown provider", repr(self.segments[0]))

        if len(self.segments) == 1:
            return self._render(provider)
        if self.segments[1:] == [EXPORT_ACTION]:
            return self._export(provider.provider_id)
        # Refused rather than ignored. A trailing segment used to fall through
        # to the provider itself, so `@identity-providers/github/expot` was a
        # successful read of something the caller did not ask for.
        return self._error(
            400,
            "Bad request",
            f"Expected @identity-providers/<id> or /<id>/{EXPORT_ACTION}",
        )

    def _export(self, provider_id: str) -> JSONDict:
        """Return one provider as a registry fragment.

        The XML travels as a string in a JSON body rather than as an
        ``application/xml`` response, because every other verb on this
        endpoint answers JSON and the control panel wants the filename
        alongside it.

        :param provider_id: The provider to export.
        :returns: The fragment and where it belongs.
        """
        return {
            "@id": f"{self._base()}/{provider_id}/{EXPORT_ACTION}",
            "provider": provider_id,
            "filename": fragment_filename(provider_id),
            "xml": provider_fragment(provider_id),
        }
