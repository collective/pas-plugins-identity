"""Storing a provider icon the way this package stores one, wherever it is written.

``IProviderRecords.icon`` declares its SVG check as a field constraint, and
the control panel's form is held to it. Nothing else was.
``plone.registry`` stores a persistent copy of every field it registers, and a
persistent field will not carry a constraint at all -- a constraint is a
function, and a stored reference to a function breaks the day it moves. So a
record imported from a GenericSetup profile was validated against a ``Bytes``
field with no constraint, and any bytes were accepted.

That went wrong twice over. A document that is not an SVG was stored, and the
first read of the providers raised and took ``@login-providers`` down for every
provider on the site, with an error naming neither the provider nor the
profile it came from. And an SVG carrying a script was stored as it came:
sanitized when read, so the login page stayed safe, but the registry and every
later export held the dangerous version, which is the one thing sanitizing on
save exists to prevent.

So the record is checked and rewritten as it is written. A document that is
not an SVG fails the write and names the provider. Anything else is replaced
by the sanitized document, in the envelope the control panel stores, so a
provider imported from XML and a provider created in the control panel end up
as the same bytes.
"""

from pas.plugins.identity.core.controlpanel import PROVIDERS_PREFIX
from pas.plugins.identity.core.utils.svg import decode_upload
from pas.plugins.identity.core.utils.svg import encode_upload
from pas.plugins.identity.core.utils.svg import InvalidSVG
from pas.plugins.identity.core.utils.svg import sanitize


#: The last segment of the record holding a provider's icon.
ICON_LEAF = "icon"


def icon_provider(name: str) -> str | None:
    """Return the provider an icon record belongs to.

    A provider id cannot contain a dot, so everything after the first dot
    below the prefix is the field. A driver setting named ``icon`` is
    ``config.icon`` there, and is not this record.

    :param name: A registry record name.
    :returns: The provider id, or ``None`` when the record is not a
        provider's icon.
    """
    if not name.startswith(PROVIDERS_PREFIX):
        return None
    provider_id, _, leaf = name[len(PROVIDERS_PREFIX) :].partition(".")
    return provider_id if leaf == ICON_LEAF else None


def sanitize_icon_record(event) -> None:
    """Refuse or sanitize a provider's icon record as it is written.

    Registered for the added and the modified event both, because the two
    forms a profile can write reach the registry differently: a ``<record>``
    element creates the record with its value in one step, while a
    ``<records interface=...>`` element registers every field at its default
    and then assigns each value.

    Rewriting the value fires the modified event again, and that second pass
    finds the value already in its stored form and stops. The control panel's
    own writes stop on the first pass, because what it stores is already the
    envelope around a sanitized document.

    :param event: A ``plone.registry`` record added or modified event.
    :raises InvalidSVG: When the value is not an SVG document this package
        stores. The message names the provider.
    """
    record = event.record
    provider_id = icon_provider(getattr(record, "__name__", None) or "")
    if provider_id is None or not record.value:
        # Not an icon, or no icon at all: clearing one is an ordinary edit.
        return
    try:
        stored = encode_upload(sanitize(decode_upload(record.value)))
    except InvalidSVG as exc:
        raise InvalidSVG(f"Provider {provider_id!r}: {exc}") from exc
    if stored != record.value:
        record.value = stored


__all__ = [
    "ICON_LEAF",
    "icon_provider",
    "sanitize_icon_record",
]
