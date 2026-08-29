"""``POST @identity-providers`` -- create, or run an action."""

from pas.plugins.identity import logger
from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel import InvalidColor
from pas.plugins.identity.core.controlpanel import InvalidProviderId
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.controlpanel import validate_provider_id
from pas.plugins.identity.core.drivers import get_driver
from pas.plugins.identity.core.flows import metadata as flow_metadata
from pas.plugins.identity.core.interfaces import FlowError
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.services.providers import ProvidersService
from pas.plugins.identity.core.services.providers import TEST_ACTION
from pas.plugins.identity.core.utils.svg import InvalidSVG
from plone.restapi.deserializer import json_body


class ProvidersPost(ProvidersService):
    """Create a provider, or run the per-provider connection check."""

    def reply(self) -> JSONDict:
        """Create a provider, or run ``test-connection`` on one.

        :returns: The created provider, the check result, or an error body.
        """
        refusal = self._refuse_unless_manager()
        if refusal is not None:
            return refusal
        self._disable_csrf()

        if len(self.segments) == 2 and self.segments[1] == TEST_ACTION:
            return self._test_connection(self.segments[0])
        if self.segments:
            return self._error(
                400, "Bad request", f"Expected @identity-providers/<id>/{TEST_ACTION}"
            )

        data = json_body(self.request)
        provider_id = (data.get("id") or "").strip()
        driver_id = (data.get("driver") or "").strip()
        if not provider_id or not driver_id:
            return self._error(400, "Missing parameters", "Required: id, driver")
        try:
            validate_provider_id(provider_id)
        except InvalidProviderId as error:
            # The id becomes part of a registry record name, so this is a
            # storage constraint rather than a matter of taste.
            return self._error(400, "Invalid provider id", str(error))
        if get_driver(driver_id) is None:
            return self._error(400, "Unknown driver", repr(driver_id))
        if get_provider(provider_id) is not None:
            # Reusing an id would silently re-point every identity already
            # stored against it.
            return self._error(
                409, "Already configured", f"{provider_id!r} already exists."
            )

        try:
            provider = ProviderConfig(
                provider_id=provider_id,
                driver_id=driver_id,
                title=data.get("title", ""),
                enabled=bool(data.get("enabled", True)),
                show_in_login=bool(data.get("show_in_login", True)),
                icon=data.get("icon", "") or "",
                background_color=data.get("background_color", "") or "",
                foreground_color=data.get("foreground_color", "") or "",
                config=data.get("config", {}),
                propertymap=data.get("propertymap", {}),
                groupmap=data.get("groupmap", {}),
            )
        except (InvalidSVG, InvalidColor) as error:
            return self._error(400, "Invalid style", str(error))
        set_providers([*get_providers(), provider])
        self.request.response.setStatus(201)
        return self._render(provider)

    def _test_connection(self, provider_id: str) -> JSONDict:
        """Check that a provider's metadata can actually be resolved.

        :param provider_id: The provider to check.
        :returns: The result, or an error body.
        """
        provider = get_provider(provider_id)
        if provider is None:
            return self._error(404, "Unknown provider", repr(provider_id))

        # Always against live state: a cached document would make a
        # test-connection button that reports the last answer rather than
        # the current one, which is worse than having no button.
        try:
            flow_metadata.forget(flow_metadata.issuer_for(provider))
        except FlowError:
            # A driver with no issuer has nothing cached either.
            logger.debug("No issuer to forget for %r", provider_id)

        try:
            metadata = flow_metadata.metadata_for(provider)
        except FlowError as exc:
            return {
                "@id": f"{self._base()}/{provider_id}/{TEST_ACTION}",
                "ok": False,
                "error": str(exc),
            }
        return {
            "@id": f"{self._base()}/{provider_id}/{TEST_ACTION}",
            "ok": True,
            "authorization_endpoint": metadata.get("authorization_endpoint", ""),
            "token_endpoint": metadata.get("token_endpoint", ""),
            "has_jwks": bool(metadata.get("jwks")),
        }
