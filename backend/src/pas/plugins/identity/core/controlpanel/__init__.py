"""Provider configuration.

Every provider setting is its own registry record, named
``pas.plugins.identity.providers.<provider_id>.<field>``. Records are created
and removed as providers are, so a GenericSetup export lists the real fields
with the real types rather than one opaque blob of JSON, and the generic
registry editor can reach any single value.

The records for one provider are::

    ...providers.<id>.driver          the driver that handles it
    ...providers.<id>.title           label on the login button
    ...providers.<id>.enabled         whether it is offered
    ...providers.<id>.order           position among the providers
    ...providers.<id>.propertymap     claim path to user field
    ...providers.<id>.config.<key>    one per field the driver declares

``order`` exists because records live in a BTree and therefore read back in
alphabetical order. Provider order is visible -- it is the order of the
buttons on the login page -- so it is stored rather than inferred.

Config records are typed from the driver's own schema, so an ``int`` setting
round-trips as an ``int``. For a provider whose driver is gone there is no
schema to consult, and the type is inferred from the stored value instead.

Secrets are stored here but never leave the backend in readable form:
:func:`mask` replaces every field the driver flagged ``secret`` with
:data:`SECRET_SENTINEL`, and :func:`unmask` puts the stored value back when a
PATCH echoes the sentinel unchanged.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.drivers import get_driver
from pas.plugins.identity.core.drivers.base import BaseDriver
from pas.plugins.identity.core.interfaces import FlowError
from pas.plugins.identity.core.interfaces import JSONDict
from plone import api
from plone.registry import field as registry_field
from plone.registry.interfaces import IRegistry
from plone.registry.record import Record
from zope.component import getUtility

import re


#: Registry prefix under which every provider's records live.
PROVIDERS_PREFIX = "pas.plugins.identity.providers."

#: Separates a provider's driver-specific settings from its own fields.
CONFIG_SEGMENT = "config."

#: What a provider id may contain. The id becomes part of a record name, so a
#: dot would silently split into a further level and lose the setting.
PROVIDER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


class InvalidProviderId(ValueError):
    """Raised when a provider id cannot be used as part of a record name."""


#: Registry key holding the frontend route the provider redirects back to.
CALLBACK_URL_RECORD = "pas.plugins.identity.callback_url"

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
    :ivar propertymap: Claim path to Plone user field. Applied on every
        login -- see :mod:`pas.plugins.identity.core.propertymap`.
    """

    def __init__(
        self,
        provider_id: str,
        driver_id: str,
        title: str = "",
        enabled: bool = True,
        config: JSONDict | None = None,
        propertymap: dict[str, str] | None = None,
    ) -> None:
        """Build a provider configuration.

        :param provider_id: Site-unique provider id.
        :param driver_id: Driver that handles this provider.
        :param title: Label for the login button; defaults to the driver's.
        :param enabled: Whether the provider is offered.
        :param config: Driver-specific settings.
        :param propertymap: Claim path to Plone user field.
        """
        self.provider_id = provider_id
        self.driver_id = driver_id
        self.title = title
        self.enabled = enabled
        self.config = config or {}
        self.propertymap = dict(propertymap or {})

    @property
    def driver(self) -> BaseDriver | None:
        """Return the driver for this provider.

        :returns: The driver utility, or ``None`` when the driver named by
            this record is not registered -- e.g. an add-on was removed while
            its providers stayed configured.
        """
        return get_driver(self.driver_id)

    def serialize(self, mask_secrets: bool = True) -> JSONDict:
        """Render the provider for storage or for an API response.

        :param mask_secrets: Whether to replace secret values with the
            sentinel. Always true on the way out of the backend; false
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
            "propertymap": dict(self.propertymap),
        }

    @classmethod
    def deserialize(cls, data: JSONDict) -> "ProviderConfig":
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
            propertymap=data.get("propertymap", {}),
        )

    def __repr__(self) -> str:
        """Return a debugging representation.

        :returns: Provider id and driver id.
        """
        return f"<ProviderConfig {self.provider_id} ({self.driver_id})>"


def _secret_fields(driver_id: str, config: JSONDict) -> set[str]:
    """Return the config fields to treat as secret.

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


def mask(driver_id: str, config: JSONDict) -> JSONDict:
    """Replace secret values with the sentinel.

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


def unmask(driver_id: str, incoming: JSONDict, stored: JSONDict) -> JSONDict:
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


def validate_provider_id(provider_id: str) -> str:
    """Check that a provider id can be part of a record name.

    :param provider_id: The candidate id.
    :returns: The id unchanged.
    :raises InvalidProviderId: When it contains anything but letters,
        digits, ``-`` or ``_``. A dot in particular would split into a
        further record level and lose the setting silently.
    """
    if not PROVIDER_ID_PATTERN.match(provider_id or ""):
        raise InvalidProviderId(
            f"{provider_id!r} is not a usable provider id: letters, digits, "
            "'-' and '_' only"
        )
    return provider_id


def _registry():
    """Return the site's registry.

    :returns: The ``IRegistry`` utility.
    """
    return getUtility(IRegistry)


def _field_for(descriptor: JSONDict | None, value: object):
    """Build the registry field a config value should be stored in.

    The driver's descriptor is the authority when there is one. Without it
    -- an orphaned provider, or a key the driver does not declare -- the
    type is taken from the value, so that an int or a bool still round-trips
    as itself rather than as its ``repr``.

    :param descriptor: The driver's schema entry, or ``None``.
    :param value: The value about to be stored.
    :returns: An unbound persistent field instance.
    """
    declared = (descriptor or {}).get("type")
    if declared == "bool" or (declared is None and isinstance(value, bool)):
        return registry_field.Bool(title="", required=False)
    if declared == "int" or (declared is None and isinstance(value, int)):
        return registry_field.Int(title="", required=False)
    if (descriptor or {}).get("secret"):
        # Marks it as a secret wherever the record is inspected. It is not
        # encryption: a GS export still carries the value, exactly as the
        # single JSON record did before.
        return registry_field.Password(title="", required=False)
    return registry_field.TextLine(title="", required=False)


def _provider_ids() -> set[str]:
    """Return the id of every provider that has records.

    :returns: Provider ids, unordered.
    """
    registry = _registry()
    names = registry.records.keys(PROVIDERS_PREFIX, PROVIDERS_PREFIX + "\uffff")
    return {name[len(PROVIDERS_PREFIX) :].split(".", 1)[0] for name in names}


def _read_provider(provider_id: str) -> tuple[ProviderConfig, int]:
    """Read one provider back out of its records.

    :param provider_id: The provider to read.
    :returns: The provider and its stored order.
    """
    registry = _registry()
    prefix = f"{PROVIDERS_PREFIX}{provider_id}."
    own: JSONDict = {}
    config: JSONDict = {}
    for name in provider_record_names(provider_id):
        leaf = name[len(prefix) :]
        value = registry.records[name].value
        if leaf.startswith(CONFIG_SEGMENT):
            config[leaf[len(CONFIG_SEGMENT) :]] = value
        else:
            own[leaf] = value
    provider = ProviderConfig(
        provider_id=provider_id,
        driver_id=own.get("driver") or "",
        title=own.get("title") or "",
        enabled=bool(own.get("enabled", True)),
        config=config,
        propertymap=dict(own.get("propertymap") or {}),
    )
    return provider, int(own.get("order") or 0)


def get_providers() -> list[ProviderConfig]:
    """Return every configured provider, enabled or not.

    :returns: Providers in their stored order.
    """
    read = [_read_provider(pid) for pid in _provider_ids()]
    # Records read back alphabetically, so the stored order is what puts the
    # login buttons back in the order the operator arranged them. The id is
    # the tie-break so the result is stable whatever the orders happen to be.
    read.sort(key=lambda pair: (pair[1], pair[0].provider_id))
    return [provider for provider, _ in read]


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


def get_callback_url() -> str:
    """Return the frontend route the provider redirects back to.

    This is the exact string registered with the provider as the redirect
    URI, so it is configuration rather than something derived from the portal
    URL: with Volto the frontend and the backend need not share an origin,
    and providers match the redirect URI exactly.

    :returns: The configured absolute URL.
    :raises FlowError: When no callback URL has been configured, which would
        otherwise surface as an opaque rejection from the provider.
    """
    url = (
        api.portal.get_registry_record(CALLBACK_URL_RECORD, default="") or ""
    ).strip()
    if not url:
        raise FlowError(
            "No login callback URL is configured; set "
            f"{CALLBACK_URL_RECORD} to the frontend route the provider "
            "redirects to"
        )
    return url


def provider_record_names(provider_id: str | None = None) -> list[str]:
    """Return the names of the records that back a provider.

    Reading the layout rather than reconstructing it: a caller checking what
    was stored should not have to know that the records live under a prefix,
    nor build the prefix itself.

    :param provider_id: One provider, or ``None`` for every provider's
        records.
    :returns: Record names, in registry order.
    """
    prefix = PROVIDERS_PREFIX
    if provider_id is not None:
        prefix = f"{PROVIDERS_PREFIX}{provider_id}."
    return list(_registry().records.keys(prefix, prefix + "\uffff"))


def get_provider_record(provider_id: str, field: str, default: object = None) -> object:
    """Read one of a provider's records.

    The counterpart of :func:`plone.api.portal.get_registry_record` for this
    package's layout: the caller names the provider and the field rather than
    assembling a dotted record name.

    :param provider_id: The provider.
    :param field: The record below it -- one of ``driver``, ``title``,
        ``enabled``, ``order``, ``propertymap``, or ``config.<key>`` for a
        driver setting.
    :param default: Returned when no such record exists.
    :returns: The stored value, or ``default``.
    """
    record = _registry().records.get(f"{PROVIDERS_PREFIX}{provider_id}.{field}")
    return default if record is None else record.value


def _forget_provider(provider_id: str) -> None:
    """Remove every record belonging to one provider.

    :param provider_id: The provider to forget.
    """
    registry = _registry()
    for name in provider_record_names(provider_id):
        del registry.records[name]


def _write_provider(provider: ProviderConfig, order: int) -> None:
    """Write one provider out as records.

    :param provider: The provider to store.
    :param order: Its position among the providers.
    """
    registry = _registry()
    prefix = f"{PROVIDERS_PREFIX}{provider.provider_id}."
    driver = provider.driver
    schema = driver.config_schema() if driver is not None else {}

    registry.records[f"{prefix}driver"] = Record(
        registry_field.TextLine(title="Driver", required=False),
        provider.driver_id,
    )
    registry.records[f"{prefix}title"] = Record(
        registry_field.TextLine(title="Title", required=False),
        provider.title,
    )
    registry.records[f"{prefix}enabled"] = Record(
        registry_field.Bool(title="Enabled", required=False),
        bool(provider.enabled),
    )
    registry.records[f"{prefix}order"] = Record(
        registry_field.Int(title="Order", required=False),
        int(order),
    )
    # One record rather than one per row: the keys are claim paths an
    # operator types, so a record each would mean creating and deleting
    # records as the map is edited. A Dict is still a typed record that
    # exports as real XML elements.
    registry.records[f"{prefix}propertymap"] = Record(
        registry_field.Dict(
            title="Property map",
            key_type=registry_field.TextLine(title="Claim"),
            value_type=registry_field.TextLine(title="User field"),
            required=False,
        ),
        dict(provider.propertymap),
    )
    for key, value in provider.config.items():
        registry.records[f"{prefix}{CONFIG_SEGMENT}{key}"] = Record(
            _field_for(schema.get(key), value),
            value,
        )


def set_providers(providers: list[ProviderConfig]) -> None:
    """Replace the stored provider list.

    Providers absent from the new list have their records removed, so the
    registry never keeps a half-deleted provider around.

    :param providers: The providers to store, in the order they should
        appear.
    :raises InvalidProviderId: When any id cannot be part of a record name.
    """
    for provider in providers:
        validate_provider_id(provider.provider_id)
    for provider_id in _provider_ids():
        _forget_provider(provider_id)
    for order, provider in enumerate(providers):
        _write_provider(provider, order)
