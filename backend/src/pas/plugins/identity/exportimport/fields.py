"""The fields of a user beyond the shipped text fields, on the wire.

A property map may write any field of the site's user type -- see
:func:`~pas.plugins.identity.core.utils.propertymap.mappable_fields` -- and a
document carries what a login can fill, so those fields travel too, under
:data:`~pas.plugins.identity.exportimport.schema.USER_EXTRA_FIELDS`.

Through ``plone.restapi``'s field adapters, both ways. A behavior field need
not hold JSON, and the REST API already says what each kind of field looks
like as JSON and how to read it back; a second answer here would be one more
way for an export and the site's own API to disagree.
"""

from pas.plugins.identity.core.utils.propertymap import mappable_fields
from pas.plugins.identity.exportimport.schema import USER_FIELDS
from plone import api
from plone.restapi.interfaces import IFieldDeserializer
from plone.restapi.interfaces import IFieldSerializer
from typing import Any
from zope.component import getMultiAdapter
from zope.globalrequest import getRequest
from zope.interface import Invalid
from zope.schema.interfaces import IField


def _request():
    """Return the request the field adapters are looked up with.

    :returns: The current request, or the site's own when a script runs
        without one being set.
    """
    return getRequest() or api.portal.get().REQUEST


def extra_fields() -> dict[str, IField]:
    """Return the fields a document carries beside :data:`USER_FIELDS`.

    :returns: Field name to unbound field, in schema order.
    """
    return {
        name: field
        for name, field in mappable_fields().items()
        if name not in USER_FIELDS
    }


def export_extra_fields(profile) -> dict[str, Any]:
    """Serialize a Profile's extra fields.

    A field holding its missing value is left out, so a document from a site
    whose people never filled a behavior in carries nothing for it.

    :param profile: The Profile.
    :returns: Field name to JSON value.
    """
    request = _request()
    exported: dict[str, Any] = {}
    for name, field in extra_fields().items():
        bound = field.bind(profile)
        value = getattr(bound.interface(profile), name, None)
        if value in (None, bound.missing_value):
            continue
        serializer = getMultiAdapter((bound, profile, request), IFieldSerializer)
        exported[name] = serializer()
    return exported


def import_extra_fields(
    profile, userid: str, values: dict[str, Any], dry_run: bool
) -> list[str]:
    """Write a user's extra fields onto a Profile.

    :param profile: The Profile, or ``None`` on a dry run that would create
        it, which only reports.
    :param userid: The user, for the reasons reported.
    :param values: Field name to JSON value, as exported.
    :param dry_run: Whether to write.
    :returns: One reason per field not written.
    """
    fields = extra_fields()
    request = _request()
    skipped = []
    for name, value in (values or {}).items():
        field = fields.get(name)
        if field is None:
            skipped.append(
                f"user {userid}: field {name!r} is not a field this site's "
                f"user type lets a document write"
            )
            continue
        if dry_run:
            continue
        bound = field.bind(profile)
        deserializer = getMultiAdapter((bound, profile, request), IFieldDeserializer)
        try:
            deserialized = deserializer(value)
        except (Invalid, ValueError) as exc:
            skipped.append(f"user {userid}: field {name!r} refused {value!r}: {exc!r}")
            continue
        bound.set(bound.interface(profile), deserialized)
    return skipped


__all__ = [
    "export_extra_fields",
    "extra_fields",
    "import_extra_fields",
]
