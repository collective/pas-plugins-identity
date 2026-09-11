"""``GET @identity-providers`` -- list, read one, or export."""

from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel.export import document_filename
from pas.plugins.identity.core.controlpanel.export import fragment_filename
from pas.plugins.identity.core.controlpanel.export import provider_fragment
from pas.plugins.identity.core.controlpanel.export import providers_document
from pas.plugins.identity.core.controlpanel.interfaces import IProviderRecords
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.services.providers import EXPORT_ACTION
from pas.plugins.identity.core.services.providers import EXPORT_ALL
from pas.plugins.identity.core.services.providers import EXPORT_PERMISSION
from pas.plugins.identity.core.services.providers import ProvidersService
from pas.plugins.identity.core.services.schema import jsonschema_for
from plone import api


class ProvidersGet(ProvidersService):
    """Read the configured providers."""

    def reply(self) -> JSONDict:
        """Return the configured providers, or an export of them.

        :returns: The listing, one provider or an export, or an error body.
        """
        # The exports come first, behind a permission of their own: they carry
        # every client secret in the clear, and managing the site does not
        # entitle anybody to read those.
        if self.segments == [EXPORT_ALL]:
            return self._export_all()
        if len(self.segments) == 2 and self.segments[1] == EXPORT_ACTION:
            return self._export(self.segments[0])

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
                # Whether the caller may take an export. Said here so the panel
                # offers its export actions only to somebody they would work
                # for, rather than a button that can only be refused.
                "can_export": api.user.has_permission(EXPORT_PERMISSION),
            }

        provider = get_provider(self.segments[0])
        if provider is None:
            return self._error(404, "Unknown provider", repr(self.segments[0]))

        if len(self.segments) == 1:
            return self._render(provider)
        # Refused rather than ignored. A trailing segment used to fall through
        # to the provider itself, so `@identity-providers/github/expot` was a
        # successful read of something the caller did not ask for.
        return self._error(
            400,
            "Bad request",
            f"Expected @identity-providers/<id>, /<id>/{EXPORT_ACTION} "
            f"or /{EXPORT_ALL}",
        )

    def _export(self, provider_id: str) -> JSONDict:
        """Return one provider as a registry fragment.

        The XML travels as a string in a JSON body rather than as an
        ``application/xml`` response, because every other verb on this
        endpoint answers JSON and the control panel wants the filename
        alongside it.

        :param provider_id: The provider to export.
        :returns: The fragment and where it belongs, or an error body.
        """
        refusal = self._refuse_unless(EXPORT_PERMISSION)
        if refusal is not None:
            return refusal
        if get_provider(provider_id) is None:
            return self._error(404, "Unknown provider", repr(provider_id))
        return {
            "@id": f"{self._base()}/{provider_id}/{EXPORT_ACTION}",
            "provider": provider_id,
            "filename": fragment_filename(provider_id),
            "xml": provider_fragment(provider_id),
        }

    def _export_all(self) -> JSONDict:
        """Return every provider as one registry document.

        :returns: The document and where it belongs, or an error body.
        """
        refusal = self._refuse_unless(EXPORT_PERMISSION)
        if refusal is not None:
            return refusal
        return {
            "@id": f"{self._base()}/{EXPORT_ALL}",
            "filename": document_filename(),
            "xml": providers_document(),
        }
