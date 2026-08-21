"""Provider configuration (§4.5).

Providers live in a single registry record as a JSON list, which is what makes
them GenericSetup-exportable and importable. Each entry names the driver that
knows how to talk to it, so adding a provider is configuration rather than
code.

Secrets are stored here but never leave the backend in readable form (I4):
:func:`mask` replaces every field the driver flagged ``secret`` with
:data:`SECRET_SENTINEL`, and :func:`unmask` puts the stored value back when a
PATCH echoes the sentinel unchanged.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.drivers import get_driver
from plone import api
from typing import Any

import json


#: Registry key holding the provider list.
PROVIDERS_RECORD = "pas.plugins.identity.providers"

#: What a secret looks like once it has left the backend. A PATCH that sends
#: this back means "leave the stored value alone".
SECRET_SENTINEL = "•" * 8


class ProviderConfig:
    """One configured provider.

    :ivar provider_id: Site-unique id, used as the ``provider`` half of an
        identity key. Never reused for a different provider: doing so would
        silently re-point every stored identity.
    :ivar driver_id: Which driver handles it.
    :ivar title: Label shown on the login button.
    :ivar enabled: Whether it appears in ``@login-providers``.
    :ivar config: Driver-specific settings.
    """

    def __init__(
        self,
        provider_id: str,
        driver_id: str,
        title: str = "",
        enabled: bool = True,
        config: dict[str, Any] | None = None,
    ) -> None:
        """Build a provider configuration.

        :param provider_id: Site-unique provider id.
        :param driver_id: Driver that handles this provider.
        :param title: Label for the login button; defaults to the driver's.
        :param enabled: Whether the provider is offered.
        :param config: Driver-specific settings.
        """
        self.provider_id = provider_id
        self.driver_id = driver_id
        self.title = title
        self.enabled = enabled
        self.config = config or {}

    @property
    def driver(self):
        """Return the driver for this provider.

        :returns: The driver utility, or ``None`` when the driver named by
            this record is not registered -- e.g. an add-on was removed while
            its providers stayed configured.
        """
        return get_driver(self.driver_id)

    def serialize(self, mask_secrets: bool = True) -> dict[str, Any]:
        """Render the provider for storage or for an API response.

        :param mask_secrets: Whether to replace secret values with the
            sentinel. Always true on the way out of the backend (I4); false
            only when writing back to the registry.
        :returns: JSON-ready mapping.
        """
        config = dict(self.config)
        if mask_secrets:
            config = mask(self.driver_id, config)
        return {
            "id": self.provider_id,
            "driver": self.driver_id,
            "title": self.title or (self.driver.title if self.driver else ""),
            "enabled": self.enabled,
            "config": config,
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> "ProviderConfig":
        """Build a provider from its stored representation.

        :param data: Mapping as produced by :meth:`serialize`.
        :returns: The provider configuration.
        """
        return cls(
            provider_id=data["id"],
            driver_id=data["driver"],
            title=data.get("title", ""),
            enabled=data.get("enabled", True),
            config=data.get("config", {}),
        )

    def __repr__(self) -> str:
        """Return a debugging representation.

        :returns: Provider id and driver id.
        """
        return f"<ProviderConfig {self.provider_id} ({self.driver_id})>"


def _secret_fields(driver_id: str, config: dict[str, Any]) -> set[str]:
    """Return the config fields to treat as secret (I4).

    A known driver flags its own. For an unknown driver -- one whose add-on
    was removed while its provider record stayed behind -- *every* field
    counts. Both directions need that: :func:`mask` must not start publishing
    the client secret of a provider nobody can audit any more, and
    :func:`unmask` must restore every echoed sentinel rather than write a row
    of bullets over the stored configuration.

    :param driver_id: Driver id.
    :param config: The configuration being masked or unmasked.
    :returns: Names of the fields to treat as secret.
    """
    driver = get_driver(driver_id)
    if driver is None:
        logger.warning(
            "Unknown driver %r: treating every config value as secret",
            driver_id,
        )
        return set(config)
    return {
        name
        for name, descriptor in driver.config_schema().items()
        if descriptor.get("secret")
    }


def mask(driver_id: str, config: dict[str, Any]) -> dict[str, Any]:
    """Replace secret values with the sentinel (I4).

    When the driver is unknown, *every* set value is masked -- see
    :func:`_secret_fields`. Masking nothing would be the dangerous failure
    here: an add-on that removed its driver would start publishing its own
    client secrets through the control panel.

    :param driver_id: Driver id.
    :param config: Stored configuration.
    :returns: A copy safe to send outside the backend.
    """
    secrets = _secret_fields(driver_id, config)
    return {
        key: (SECRET_SENTINEL if key in secrets and value else value)
        for key, value in config.items()
    }


def unmask(
    driver_id: str, incoming: dict[str, Any], stored: dict[str, Any]
) -> dict[str, Any]:
    """Restore stored secrets that the caller echoed back unchanged.

    A control panel round-trip reads masked values and PATCHes them back; that
    must not overwrite the real secret with a row of bullets.

    :param driver_id: Driver id.
    :param incoming: Configuration as submitted.
    :param stored: Configuration currently in the registry.
    :returns: Configuration to store.
    """
    secrets = _secret_fields(driver_id, incoming)
    result = dict(incoming)
    for key in secrets:
        if result.get(key) == SECRET_SENTINEL:
            if key in stored:
                result[key] = stored[key]
            else:
                del result[key]
    return result


def get_providers() -> list[ProviderConfig]:
    """Return every configured provider, enabled or not.

    :returns: Providers in registry order.
    """
    raw = api.portal.get_registry_record(PROVIDERS_RECORD, default="") or ""
    if not raw:
        return []
    return [ProviderConfig.deserialize(entry) for entry in json.loads(raw)]


def get_provider(provider_id: str) -> ProviderConfig | None:
    """Return one configured provider.

    :param provider_id: Site-unique provider id.
    :returns: The provider, or ``None`` when it is not configured.
    """
    for provider in get_providers():
        if provider.provider_id == provider_id:
            return provider
    return None


def enabled_providers() -> list[ProviderConfig]:
    """Return the providers a user may actually log in with.

    A provider whose driver is missing is skipped: offering a login button
    that cannot work is worse than not offering it.

    :returns: Enabled providers with a registered driver.
    """
    return [p for p in get_providers() if p.enabled and p.driver is not None]


def set_providers(providers: list[ProviderConfig]) -> None:
    """Replace the stored provider list.

    :param providers: The providers to store.
    """
    payload = [p.serialize(mask_secrets=False) for p in providers]
    api.portal.set_registry_record(PROVIDERS_RECORD, json.dumps(payload))
