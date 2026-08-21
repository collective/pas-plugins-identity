"""``@identity-providers`` and ``@identity-drivers`` -- the control panel API.

The Volto control-panel widget is generated from driver metadata rather than
hand-written per provider (§4.5), so there are two endpoints: one that
describes what a driver needs, and one that manages the provider records
themselves.

``GET @identity-drivers``
    Every registered driver and its config schema. This is what the widget
    renders a form from.

``GET @identity-providers`` / ``GET @identity-providers/<id>``
``POST @identity-providers``
``PATCH @identity-providers/<id>``
``DELETE @identity-providers/<id>``
``POST @identity-providers/<id>/test-connection``

Everything here needs ``Manage portal``. Secrets are write-only through all of
it (S7/I4): what leaves is masked, and a PATCH echoing the mask back leaves
the stored value alone.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.controlpanel import unmask
from pas.plugins.identity.core.drivers import all_drivers
from pas.plugins.identity.core.drivers import get_driver
from pas.plugins.identity.core.flows import metadata as flow_metadata
from pas.plugins.identity.core.interfaces import FlowError
from pas.plugins.identity.core.services.base import IdentityService
from plone import api
from plone.restapi.deserializer import json_body
from typing import Any
from zope.interface import alsoProvides
from zope.interface import implementer
from zope.publisher.interfaces import IPublishTraverse

import plone.protect.interfaces


#: Permission every one of these endpoints requires.
MANAGE_PERMISSION = "Manage portal"

#: Path segment that runs the per-provider connection check.
TEST_ACTION = "test-connection"


class ControlPanelService(IdentityService):
    """Shared guard: none of this is readable without Manage portal."""

    def _refuse_unless_manager(self) -> dict[str, Any] | None:
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


class DriversGet(ControlPanelService):
    """``GET @identity-drivers`` -- what the control-panel widget renders."""

    def reply(self) -> dict[str, Any]:
        """Describe every registered driver.

        :returns: The listing, or an error body.
        """
        refusal = self._refuse_unless_manager()
        if refusal is not None:
            return refusal

        return {
            "@id": f"{self.context.absolute_url()}/@identity-drivers",
            "items": [
                {
                    "id": driver.driver_id,
                    "title": driver.title,
                    "schema": driver.config_schema(),
                }
                for _name, driver in sorted(all_drivers().items())
            ],
        }


@implementer(IPublishTraverse)
class ProvidersService(ControlPanelService):
    """Base for the provider CRUD verbs."""

    def __init__(self, context: Any, request: Any) -> None:
        """Bind the service and prepare to consume path segments.

        :param context: The context the service was traversed on.
        :param request: The current request.
        """
        super().__init__(context, request)
        self.segments: list[str] = []

    def publishTraverse(self, request: Any, name: str) -> "ProvidersService":
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

    def _render(self, provider: ProviderConfig) -> dict[str, Any]:
        """Render one provider for an API response.

        :param provider: The provider.
        :returns: JSON-ready mapping, secrets masked (I4).
        """
        payload = provider.serialize()
        payload["@id"] = f"{self._base()}/{provider.provider_id}"
        return payload


class ProvidersGet(ProvidersService):
    """``GET @identity-providers`` -- list, or read one."""

    def reply(self) -> dict[str, Any]:
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


class ProvidersPost(ProvidersService):
    """``POST @identity-providers`` -- create, or run an action."""

    def reply(self) -> dict[str, Any]:
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
        if get_driver(driver_id) is None:
            return self._error(400, "Unknown driver", repr(driver_id))
        if get_provider(provider_id) is not None:
            # Reusing an id would silently re-point every identity already
            # stored against it.
            return self._error(
                409, "Already configured", f"{provider_id!r} already exists."
            )

        provider = ProviderConfig(
            provider_id=provider_id,
            driver_id=driver_id,
            title=data.get("title", ""),
            enabled=bool(data.get("enabled", True)),
            config=data.get("config", {}),
        )
        set_providers([*get_providers(), provider])
        self.request.response.setStatus(201)
        return self._render(provider)

    def _test_connection(self, provider_id: str) -> dict[str, Any]:
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


class ProvidersPatch(ProvidersService):
    """``PATCH @identity-providers/<id>`` -- update in place."""

    def reply(self) -> dict[str, Any]:
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
        if "config" in data:
            # S7/I4 -- a round trip echoes the mask back, and that must not
            # overwrite the stored secret with a row of bullets.
            target.config = unmask(target.driver_id, data["config"], target.config)

        set_providers(providers)
        return self.reply_no_content()


class ProvidersDelete(ProvidersService):
    """``DELETE @identity-providers/<id>`` -- remove a provider."""

    def reply(self) -> dict[str, Any]:
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
