"""Provider configuration.

Every provider setting is its own registry record, named
``pas.plugins.identity.providers.<provider_id>.<field>``. Records are created
and removed as providers are, so a GenericSetup export lists the real fields
with the real types rather than one opaque blob of JSON, and the generic
registry editor can reach any single value.

The records for one provider are::

    ...providers.<id>.driver            the driver that handles it
    ...providers.<id>.title             label on the login button
    ...providers.<id>.enabled           whether it may be used at all
    ...providers.<id>.show_in_login     whether the login screen offers it
    ...providers.<id>.order             position among the providers
    ...providers.<id>.icon              SVG source, sanitized on the way in
    ...providers.<id>.background_color  button background, as a hex value
    ...providers.<id>.foreground_color  button foreground, as a hex value
    ...providers.<id>.propertymap       claim path to user field
    ...providers.<id>.groupmap          provider group name to local group id
    ...providers.<id>.config.<key>      one per field the driver declares

``enabled`` and ``show_in_login`` are two questions rather than one. The first
is whether the provider works at all; the second is whether the login screen
advertises it. A provider that is enabled but not shown is still linkable from
a user's own identities page and still signs in an account already linked to
it, which is what a staff-only or invitation-only provider looks like.

``order`` exists because records live in a BTree and therefore read back in
alphabetical order. Provider order is visible -- it is the order of the
buttons on the login page -- so it is stored rather than inferred.

Config records are typed from the driver's own schema, so an ``int`` setting
round-trips as an ``int``. For a provider whose driver is gone there is no
schema to consult, and the type is inferred from the stored value instead.

Secrets are stored here but never leave the backend in readable form:
:func:`mask` replaces every :class:`~zope.schema.Password` field in the
driver's schema with :data:`SECRET_SENTINEL`, and :func:`unmask` puts the
stored value back when a PATCH echoes the sentinel unchanged. The field type
*is* the flag -- there is no separate ``secret`` marker to forget.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.controlpanel.interfaces import IProviderRecords
from pas.plugins.identity.core.drivers import get_driver
from pas.plugins.identity.core.drivers.base import BaseDriver
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.interfaces import ProviderUnusable
from pas.plugins.identity.core.utils.svg import decode_upload
from pas.plugins.identity.core.utils.svg import encode_upload
from pas.plugins.identity.core.utils.svg import sanitize as sanitize_svg
from plone import api
from plone.registry import field as registry_field
from plone.registry.interfaces import IRegistry
from plone.registry.record import Record
from zope.component import getUtility
from zope.schema import getFieldsInOrder
from zope.schema.interfaces import IBool
from zope.schema.interfaces import ICollection
from zope.schema.interfaces import IInt
from zope.schema.interfaces import IPassword

import copy
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

#: Where the frontend listens when nothing else is configured. It is the
#: route this package's Volto add-on registers, so the default is right for
#: every site that installs both halves.
DEFAULT_CALLBACK_PATH = "/login-identity"

#: What a secret looks like once it has left the backend. A PATCH that sends
#: this back means "leave the stored value alone".
SECRET_SENTINEL = "•" * 8

#: What a stored colour may look like. Three, four, six or eight hex digits
#: behind a hash -- the CSS forms -- and nothing else. Anything looser would
#: let a colour field carry a CSS expression into the style attribute the
#: frontend builds from it.
HEX_COLOR_PATTERN = re.compile(r"^#(?:[0-9A-Fa-f]{3,4}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$")


class InvalidColor(ValueError):
    """Raised when a colour is not a hex value this package will store."""


def normalize_color(value: str) -> str:
    """Return a colour as it is stored, or refuse it.

    :param value: The colour as supplied, with or without its leading hash.
    :returns: The colour lowercased and hashed, or the empty string when
        nothing was supplied -- clearing a colour is a normal edit.
    :raises InvalidColor: When the value is not a CSS hex colour.
    """
    text = (value or "").strip()
    if not text:
        return ""
    if not text.startswith("#"):
        text = f"#{text}"
    if not HEX_COLOR_PATTERN.match(text):
        raise InvalidColor(f"{value!r} is not a hex colour such as #24292f")
    return text.lower()


def _settings_fields(driver_id: str) -> dict[str, object]:
    """Return a driver's settings fields, keyed by name.

    One place asks the schema what it holds, so the three functions below --
    coercion, defaults and masking -- cannot disagree about which fields exist
    or drift apart when the schema changes.

    :param driver_id: Driver that declares the schema.
    :returns: Field name to ``zope.schema`` field, empty when the driver is
        gone. An orphaned provider has no schema left to consult and each
        caller has its own safe answer for that.
    """
    driver = get_driver(driver_id)
    if driver is None:
        return {}
    return dict(getFieldsInOrder(driver.settings_schema))


def _stored_types(driver_id: str, config: JSONDict) -> JSONDict:
    """Coerce settings into the types their registry records accept.

    Only sequences need it today. A ``Tuple`` field is held in a ``Tuple``
    record, and JSON has one sequence type that decodes to a Python list -- so
    a scope arriving over the API is a list and the record refuses it. The
    refusal comes at write time, as a ``WrongType`` naming the value rather
    than the shape, well away from the request that caused it.

    :param driver_id: Driver that declares the schema.
    :param config: Settings as supplied.
    :returns: Those settings, with sequences as tuples.
    """
    fields = _settings_fields(driver_id)
    if not fields:
        # An orphan is stored as whatever it already was; there is no schema
        # left to say what any of it should be.
        return dict(config)
    return {
        name: tuple(value)
        if ICollection.providedBy(fields.get(name)) and isinstance(value, list)
        else value
        for name, value in config.items()
    }


def _with_driver_defaults(driver_id: str, config: JSONDict) -> JSONDict:
    """Fill in the settings the caller did not supply.

    Two sources, in this order. The schema's field defaults come first --
    ``picture_over_http`` is false, a magic link lives fifteen minutes -- and
    then the *driver's* own, because which scope GitHub needs and which userid
    source suits a peer are facts about a driver rather than about a field.
    A key that *is* present wins over both, empty or not: clearing a setting
    is a decision, and reinstating the default over it would be this function
    overruling an operator.

    It runs on the way in, not on the way out, so what a control panel shows
    and what the registry stores are the same values.

    :param driver_id: Driver that declares the schema.
    :param config: Settings as supplied.
    :returns: Those settings, with the missing ones defaulted.
    """
    driver = get_driver(driver_id)
    if driver is None:
        # No schema to consult -- the add-on that registered this driver is
        # gone. Whatever was stored is all there is.
        return dict(config)
    defaults = {
        # deepcopy because a sequence default is one object on the field, and
        # two providers sharing it would share every edit.
        name: copy.deepcopy(field.default)
        for name, field in _settings_fields(driver_id).items()
        if field.default is not None
    }
    defaults.update(_driver_defaults(driver))
    return _stored_types(driver_id, {**defaults, **config})


def _driver_defaults(driver: BaseDriver) -> JSONDict:
    """Return the settings this particular driver starts a provider with.

    Kept on the driver class rather than as field defaults: a subinterface
    changing a default would have to redeclare the field, and a redeclared
    field takes a fresh creation order -- so the price of GitHub wanting its
    own scope would be a scope box that jumps to the end of the form.

    Only the settings a driver actually has an opinion about. ``group_claim``
    is omitted entirely when the driver has none, so a provider with no groups
    to map does not carry an empty mapping nobody asked for.

    :param driver: The driver.
    :returns: Settings to seed, which may be empty.
    """
    seeded: JSONDict = {
        "scope": tuple(driver.default_scope),
        "userid_source": driver.default_userid_source,
        "trust_email_verification": driver.default_trust_email_verification,
    }
    if driver.default_group_claim:
        seeded["group_claim"] = driver.default_group_claim
    return seeded


class ProviderConfig:
    """One configured provider.

    :ivar provider_id: Site-unique id, used as the ``provider`` half of an
        identity key. Never reused for a different provider: doing so would
        silently re-point every stored identity.
    :ivar driver_id: Which driver handles it.
    :ivar title: Label shown on the login button.
    :ivar enabled: Whether it may be used at all -- to sign in, and to link.
    :ivar show_in_login: Whether the login screen offers it. Only meaningful
        while ``enabled``: a disabled provider is offered nowhere.
    :ivar icon: SVG source for the login button, sanitized on assignment.
    :ivar background_color: Button background as a hex value, or empty.
    :ivar foreground_color: Button foreground as a hex value, or empty.
    :ivar config: Driver-specific settings.
    :ivar propertymap: Claim path to Plone user field. Applied on every
        login -- see :mod:`pas.plugins.identity.core.utils.propertymap`.
    :ivar groupmap: Provider-side group name to local group id. Applied on
        every login -- see :mod:`pas.plugins.identity.core.utils.groupmap`. Empty
        by default, which is what makes a provider grant no groups at all
        until somebody says otherwise.
    """

    def __init__(
        self,
        provider_id: str,
        driver_id: str,
        title: str = "",
        enabled: bool = True,
        config: JSONDict | None = None,
        propertymap: dict[str, str] | None = None,
        groupmap: dict[str, str] | None = None,
        show_in_login: bool = True,
        icon: str = "",
        background_color: str = "",
        foreground_color: str = "",
    ) -> None:
        """Build a provider configuration.

        :param provider_id: Site-unique provider id.
        :param driver_id: Driver that handles this provider.
        :param title: Label for the login button; defaults to the driver's.
        :param enabled: Whether the provider may be used at all.
        :param config: Driver-specific settings.
        :param propertymap: Claim path to Plone user field.
        :param groupmap: Provider-side group name to local group id.
        :param show_in_login: Whether the login screen offers it.
        :param icon: SVG source for the login button.
        :param background_color: Button background as a hex value.
        :param foreground_color: Button foreground as a hex value.
        :raises InvalidSVG: When the icon is not a storable SVG document.
        :raises InvalidColor: When a colour is not a hex value.
        """
        self.provider_id = provider_id
        self.driver_id = driver_id
        self.title = title
        self.enabled = enabled
        self.show_in_login = show_in_login
        self.icon = icon
        self.background_color = background_color
        self.foreground_color = foreground_color
        self.config = _with_driver_defaults(driver_id, config or {})
        self.propertymap = dict(propertymap or {})
        self.groupmap = dict(groupmap or {})

    @property
    def icon(self) -> str:
        """Return the SVG source for this provider's button.

        :returns: The sanitized document, or the empty string.
        """
        return self._icon

    @icon.setter
    def icon(self, value: object) -> None:
        """Sanitize and store an icon, however it arrived.

        Two shapes, both ordinary: a form sends the ``filenameb64:…;datab64:…``
        envelope Plone's own file widgets produce -- the one ``site_logo`` is
        stored in -- while an import or a GenericSetup profile sends the SVG
        source itself. :func:`~pas.plugins.identity.core.utils.svg.decode_upload`
        tells them apart on the prefix, which is exact.

        Sanitized on assignment rather than on render, so what is stored is
        what is served: sanitizing on the way out would leave the dangerous
        version in the registry, in a GenericSetup export, and in whatever
        else reads a record directly.

        What is *kept* is the source rather than the envelope. Every reader
        here wants the document -- the login listing inlines it so it can take
        the button's colour -- and the envelope is put back on only at the two
        boundaries that need it: the registry record and the control panel's
        own form.

        :param value: The SVG document, or the envelope carrying one.
        :raises InvalidSVG: When it is not a storable SVG document.
        """
        self._icon = sanitize_svg(decode_upload(value))

    @property
    def background_color(self) -> str:
        """Return the button background.

        :returns: A hex colour, or the empty string.
        """
        return self._background_color

    @background_color.setter
    def background_color(self, value: str) -> None:
        """Normalize and store the button background.

        :param value: The colour as supplied.
        :raises InvalidColor: When it is not a hex colour.
        """
        self._background_color = normalize_color(value)

    @property
    def foreground_color(self) -> str:
        """Return the button foreground.

        :returns: A hex colour, or the empty string.
        """
        return self._foreground_color

    @foreground_color.setter
    def foreground_color(self, value: str) -> None:
        """Normalize and store the button foreground.

        :param value: The colour as supplied.
        :raises InvalidColor: When it is not a hex colour.
        """
        self._foreground_color = normalize_color(value)

    @property
    def usable(self) -> bool:
        """Report whether anything may sign in or link through this provider.

        :returns: Whether it is enabled and its driver is registered. A
            provider whose driver is gone is not usable however it is
            configured -- the add-on that knew how to talk to it was removed.
        """
        return bool(self.enabled) and self.driver is not None

    @property
    def offered_at_login(self) -> bool:
        """Report whether the login screen should draw a button for this.

        :returns: Whether it is usable *and* the operator asked for it to be
            shown.
        """
        return self.usable and bool(self.show_in_login)

    @property
    def config(self) -> JSONDict:
        """Driver-specific settings, in the types the registry stores.

        :returns: The settings.
        """
        return self._config

    @config.setter
    def config(self, value: JSONDict) -> None:
        """Store settings, coercing them to the stored types.

        A PATCH assigns here rather than building a provider, so this is the
        one place both routes pass through. It coerces without defaulting:
        filling a gap is a decision about a provider being *created*, and
        doing it on every edit would reinstate a setting an operator had
        just cleared.

        :param value: The settings to store.
        """
        self._config = _stored_types(self.driver_id, dict(value or {}))

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
            "show_in_login": self.show_in_login,
            # The envelope rather than the source: this is what the control
            # panel's form is built from, and its file widget round-trips the
            # value it was given. The login listing below sends the source,
            # because that is what gets inlined into a button.
            "icon": encode_upload(self.icon).decode("ascii"),
            "background_color": self.background_color,
            "foreground_color": self.foreground_color,
            "config": config,
            "propertymap": dict(self.propertymap),
            "groupmap": dict(self.groupmap),
        }

    def style(self) -> JSONDict:
        """Render just what a client needs to draw the button.

        Separate from :meth:`serialize`, which is the control panel's view and
        needs ``Manage portal``. This is public by construction -- it is on
        every login page -- so it carries the three presentation values and
        nothing else.

        :returns: JSON-ready mapping of icon and colours.
        """
        return {
            "icon": self.icon,
            "background_color": self.background_color,
            "foreground_color": self.foreground_color,
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
            # Absent means shown. Every provider stored before this setting
            # existed was offered at login, and a new key must not silently
            # take a site's login buttons away.
            show_in_login=data.get("show_in_login", True),
            icon=data.get("icon", "") or "",
            background_color=data.get("background_color", "") or "",
            foreground_color=data.get("foreground_color", "") or "",
            config=data.get("config", {}),
            propertymap=data.get("propertymap", {}),
            groupmap=data.get("groupmap", {}),
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
    fields = _settings_fields(driver_id)
    if not fields:
        logger.warning(
            "Unknown driver %r: treating every config value as secret",
            driver_id,
        )
        return set(config)
    return {name for name, field in fields.items() if IPassword.providedBy(field)}


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


def _field_for(declared: object | None, value: object):
    """Build the registry field a config value should be stored in.

    The driver's own schema field is the authority when there is one. Without
    it -- an orphaned provider, or a key the driver does not declare -- the
    type is taken from the value, so that an int or a bool still round-trips
    as itself rather than as its ``repr``.

    A registry field rather than the schema field itself: the two hierarchies
    look alike but a record needs ``plone.registry``'s persistent variety, and
    the schema field carries a title, a description and a vocabulary that have
    no business being copied into every provider's records.

    :param declared: The ``zope.schema`` field from the driver's settings
        schema, or ``None``.
    :param value: The value about to be stored.
    :returns: An unbound persistent field instance.
    """
    if IBool.providedBy(declared) or (declared is None and isinstance(value, bool)):
        return registry_field.Bool(title="", required=False)
    if IInt.providedBy(declared) or (declared is None and isinstance(value, int)):
        return registry_field.Int(title="", required=False)
    if ICollection.providedBy(declared) or (
        declared is None and isinstance(value, (list, tuple))
    ):
        return registry_field.Tuple(
            title="",
            required=False,
            value_type=registry_field.TextLine(title=""),
        )
    if IPassword.providedBy(declared):
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
        show_in_login=bool(own.get("show_in_login", True)),
        icon=own.get("icon") or "",
        background_color=own.get("background_color") or "",
        foreground_color=own.get("foreground_color") or "",
        config=config,
        propertymap=dict(own.get("propertymap") or {}),
        groupmap=dict(own.get("groupmap") or {}),
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
    """Return the providers that may be used at all.

    A provider whose driver is missing is skipped: it cannot work however it
    is configured, because the add-on that knew how to talk to it is gone.

    This is *availability*, not visibility. It is what the identities page
    offers to link, and what a sign-in through an already-linked identity is
    checked against. The login screen asks :func:`login_providers` instead.

    :returns: Enabled providers with a registered driver, in stored order.
    """
    return [p for p in get_providers() if p.usable]


def login_providers() -> list[ProviderConfig]:
    """Return the providers the login screen should offer.

    The usable ones the operator also asked to show. Everything enabled and
    hidden stays reachable through ``@identities`` -- that is the whole point
    of the two settings being two settings.

    :returns: Providers to draw login buttons for, in stored order.
    """
    return [p for p in get_providers() if p.offered_at_login]


def get_callback_url() -> str:
    """Return the frontend route the provider redirects back to.

    Accepts either form. A **path** -- the usual case, and the default -- is
    resolved against the portal URL, which under Volto is the public origin
    the browser already uses. An **absolute URL** is taken verbatim, for the
    deployment this setting was originally written for: the frontend and the
    backend need not share an origin, and no portal URL can describe an
    origin Plone is never reached on.

    Whichever form it takes, the result has to match the redirect URI
    registered with the provider byte for byte.

    :returns: The absolute URL to hand the provider.
    :raises ProviderUnusable: When the configured value is neither a path
        nor an absolute URL, which a provider would reject opaquely.
    """
    url = (
        api.portal.get_registry_record(CALLBACK_URL_RECORD, default="") or ""
    ).strip() or DEFAULT_CALLBACK_PATH

    if url.startswith("/"):
        return f"{api.portal.get().absolute_url()}{url}"
    if "://" not in url:
        raise ProviderUnusable(
            f"{CALLBACK_URL_RECORD} is {url!r}, which is neither a path "
            "starting with '/' nor an absolute URL"
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
        ``enabled``, ``show_in_login``, ``order``, ``icon``,
        ``background_color``, ``foreground_color``, ``propertymap``,
        ``groupmap``, or ``config.<key>`` for a driver setting.
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
    fields = _settings_fields(provider.driver_id)

    # The same interface a profile's registry XML binds to, registered under
    # the same prefix, so a provider created here and a provider imported from
    # XML are the identical set of records. Doing it the other way -- building
    # the five fields by hand -- is what made a profile have to restate a
    # field type it could have inherited.
    #
    # Every value is assigned below rather than left at the schema default:
    # ``registerInterface`` hands each new record the default *object*, so two
    # providers that both fell back to the empty ``propertymap`` would share
    # one dict.
    registry.registerInterface(IProviderRecords, prefix=prefix.rstrip("."))

    registry[f"{prefix}driver"] = provider.driver_id
    registry[f"{prefix}title"] = provider.title
    registry[f"{prefix}enabled"] = bool(provider.enabled)
    registry[f"{prefix}show_in_login"] = bool(provider.show_in_login)
    registry[f"{prefix}order"] = int(order)
    registry[f"{prefix}icon"] = encode_upload(provider.icon)
    registry[f"{prefix}background_color"] = provider.background_color
    registry[f"{prefix}foreground_color"] = provider.foreground_color
    registry[f"{prefix}propertymap"] = dict(provider.propertymap)
    registry[f"{prefix}groupmap"] = dict(provider.groupmap)

    for key, value in provider.config.items():
        registry.records[f"{prefix}{CONFIG_SEGMENT}{key}"] = Record(
            _field_for(fields.get(key), value),
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
