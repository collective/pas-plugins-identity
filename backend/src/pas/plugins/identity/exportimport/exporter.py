"""A site's principals, as a document.

Reads the two content types and the identity store, and writes the format
:mod:`~pas.plugins.identity.exportimport.schema` describes. Nothing here
writes to the site, so an export is safe to run against production -- it is
the one half of this package that cannot go wrong in a way that costs
anything.

**Through the objects rather than the catalog.** The catalog would be faster
and it holds most of these columns, but an export is the wrong place to trade
completeness for speed: a brain carries what the catalog was configured to
keep, and a field added to the Profile without a matching metadata column
would go missing from every backup taken until somebody noticed. Waking the
objects costs a few seconds once and cannot be wrong.
"""

from Acquisition import aq_inner
from Acquisition import aq_parent
from datetime import datetime
from datetime import UTC
from pas.plugins.identity import logger
from pas.plugins.identity.core.behaviors.roles import IGlobalRoles
from pas.plugins.identity.core.catalog import GROUP_PORTAL_TYPE
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.catalog import query_catalog
from pas.plugins.identity.core.interfaces import IGroupContent
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.exportimport.schema import DOCUMENT_VERSION
from pas.plugins.identity.exportimport.schema import ExportImportError
from pas.plugins.identity.exportimport.schema import GENERATOR
from pas.plugins.identity.exportimport.schema import GROUP_FIELDS
from pas.plugins.identity.exportimport.schema import GROUP_ROLES_FIELD
from pas.plugins.identity.exportimport.schema import USER_FIELDS
from plone import api
from typing import Any


def _text(value: object) -> str:
    """Render a field as the text a document carries.

    :param value: Whatever the field holds.
    :returns: The value as text, empty for ``None``.
    """
    return "" if value is None else str(value)


def _stamp(value: datetime | None) -> str | None:
    """Render a timestamp for the document.

    :param value: The moment, or ``None``.
    :returns: An ISO-8601 string, or ``None``.
    """
    return value.isoformat() if value is not None else None


def _identity_store():
    """Return the identity store, refusing when the add-on is not installed.

    :returns: The store.
    :raises ExportImportError: When this site has no identity plugin, which
        for an export means the answer would be an empty document rather than
        an error -- and an empty document that looks like a backup is worse
        than a refusal.
    """
    plugin = api.portal.get_tool("acl_users").get(PLUGIN_ID)
    if plugin is None:
        raise ExportImportError(
            "This site has no identity plugin, so there is nothing to export. "
            "Install pas.plugins.identity here first."
        )
    return plugin.store


def _objects_of_type(portal_type: str) -> list:
    """Return every object of a portal type this package files.

    :param portal_type: The type to find.
    :returns: The objects, in catalog order.
    :raises ExportImportError: When the catalog is missing.
    """
    catalog = query_catalog()
    if catalog is None:
        raise ExportImportError(
            "This site has no identity catalog, so its principals cannot be "
            "enumerated. Install pas.plugins.identity here first."
        )
    brains = catalog.unrestrictedSearchResults(portal_type=portal_type)
    return [brain._unrestrictedGetObject() for brain in brains]


def export_group(group) -> dict[str, Any]:
    """Render one group.

    :param group: A ``UserGroup`` object.
    :returns: The group as plain data.
    """
    exported = {"group_id": _text(getattr(group, "group_id", "") or group.getId())}
    for name in GROUP_FIELDS:
        exported[name] = _text(getattr(group, name, ""))
    # Through the adapter, because the behavior stores nothing on the object:
    # ``getattr(group, "global_roles")`` would answer with a shadow attribute
    # or an AttributeError, never with what the site actually granted.
    roles = IGlobalRoles(group, None)
    exported[GROUP_ROLES_FIELD] = list(roles.global_roles) if roles is not None else []
    # The groups this group is nested inside. Applied last on the way in,
    # because it can name a group that comes later in the list.
    exported["group_ids"] = list(getattr(group, "group_ids", None) or ())
    # The other way of writing the same edge: the group this one is filed
    # inside, when that is a group rather than a folder. Carried separately
    # rather than folded into ``group_ids`` because the two are not the same
    # thing on the way back in -- one is a field to write, the other is a
    # place to put the object -- and an import that turned a hierarchy into a
    # flat list of equivalent memberships would round-trip the access while
    # silently discarding the structure somebody built.
    exported["container_group"] = _text(_containing_group_id(group))
    return exported


def _containing_group_id(group) -> str:
    """Return the id of the group this one is filed inside, if any.

    :param group: A ``UserGroup`` object.
    :returns: The containing group's id, or an empty string when this group
        is not filed inside a group.
    """
    parent = aq_parent(aq_inner(group))
    if parent is None or not IGroupContent.providedBy(parent):
        return ""
    return str(getattr(parent, "group_id", "") or parent.getId())


def export_user(profile, store) -> dict[str, Any]:
    """Render one user, with the identities that reach them.

    :param profile: A ``UserProfile`` object.
    :param store: The identity store to read the join from.
    :returns: The user as plain data.
    """
    userid = _text(profile.userid)
    exported: dict[str, Any] = {
        "userid": userid,
        "login": _text(profile.login),
        "emails": list(profile.emails or ()),
    }
    for name in USER_FIELDS:
        exported[name] = _text(getattr(profile, name, ""))
    exported["group_ids"] = list(getattr(profile, "group_ids", None) or ())
    exported["identities"] = [
        {
            "provider": record.provider,
            "subject": record.subject,
            "created": _stamp(record.created),
            "last_login": _stamp(record.last_login),
            "groups": list(record.groups),
            "claims": dict(record.claims),
        }
        for record in store.identities_for(userid)
    ]
    return exported


def export_site(dry_run: bool = False) -> dict[str, Any]:
    """Render this site's principals as a document.

    ``dry_run`` is accepted and ignored, because an export writes nothing
    either way. It exists so that a script can pass the same flag to both
    halves without branching on which one it is calling.

    :param dry_run: Ignored; see above.
    :returns: The document.
    :raises ExportImportError: When this site has no identity plugin.
    """
    store = _identity_store()
    groups = [export_group(obj) for obj in _objects_of_type(GROUP_PORTAL_TYPE)]
    users = [export_user(obj, store) for obj in _objects_of_type(PROFILE_PORTAL_TYPE)]

    orphaned = sorted(set(store.userids()) - {user["userid"] for user in users})
    if orphaned:
        # Deleting a user leaves the identity records behind on purpose; see
        # the reference docs. They are reported rather than exported, because
        # a document is a set of accounts and these have none.
        logger.warning(
            "%d identity records belong to userids with no profile and are "
            "not in this export: %s",
            len(orphaned),
            ", ".join(orphaned),
        )

    return {
        "version": DOCUMENT_VERSION,
        "generator": GENERATOR,
        "created": datetime.now(UTC).isoformat(),
        "site": api.portal.get().getId(),
        "groups": groups,
        "users": users,
    }


__all__ = ["export_group", "export_site", "export_user"]
