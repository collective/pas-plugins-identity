"""Take a site to profile version 1004.

A property map's target is a ``Choice`` over the fields a login can actually
write. A site configured before that was true may hold rows naming anything at
all: the control panel offered a free-text box, and
``pas.plugins.identity``'s own default map seeded ``email`` into every new
provider.

Such a row has never done anything. :func:`claim_fields` filtered it out on
every login, and it is filtered still, so this step is not what makes those
sites correct -- it is what makes them *editable*. The field refuses the whole
map on write, so an operator who opens a provider carrying one and presses save
gets a refusal about a row they did not add, on a form that no longer has a box
to remove it in.

Removed rather than reported, and the removal is logged per row: nothing is
lost, because nothing was ever applied.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.controlpanel import PROVIDERS_PREFIX
from pas.plugins.identity.core.utils.propertymap import MAPPABLE_FIELDS
from plone.registry.interfaces import IRegistry
from Products.GenericSetup.tool import SetupTool
from zope.component import getUtility


#: The record below each provider that this step rewrites.
RECORD = "propertymap"


def usable(propertymap: dict) -> dict:
    """Return the rows of a map a login would actually apply.

    :param propertymap: The stored map.
    :returns: The same map without the rows naming an unwritable field.
    """
    return {
        path: field
        for path, field in (propertymap or {}).items()
        if field in MAPPABLE_FIELDS
    }


def drop_unmappable_rows(context: SetupTool) -> None:
    """Remove property map rows naming a field no login ever wrote.

    Written through the registry rather than into its value mapping, so the
    result is validated by the same field an operator's edit goes through: a
    map this step leaves behind is one the control panel can save.

    :param context: The setup tool running the upgrade.
    """
    registry = getUtility(IRegistry)
    suffix = f".{RECORD}"
    names = [
        name
        for name in registry.records
        if name.startswith(PROVIDERS_PREFIX) and name.endswith(suffix)
    ]
    for name in names:
        stored = registry.records[name].value or {}
        kept = usable(stored)
        if kept == stored:
            continue
        provider_id = name[len(PROVIDERS_PREFIX) : -len(suffix)]
        for path, field in stored.items():
            if path not in kept:
                logger.info(
                    "Provider %r: dropping property map row %r -> %r, which no "
                    "login has ever applied.",
                    provider_id,
                    path,
                    field,
                )
        registry[name] = kept
