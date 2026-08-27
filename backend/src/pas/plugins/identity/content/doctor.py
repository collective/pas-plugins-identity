"""Consistency check for the identity catalog.

A dedicated catalog is a second copy of the truth, and a second copy drifts.
This module answers "has it?" without repairing anything: repair is
:meth:`~pas.plugins.identity.content.catalog.IdentityProfileCatalog.clearFindAndRebuild`,
and the two are kept apart on purpose so that a scheduled check can run
read-only and so the churn test asserts against findings rather than against
whatever a repair happened to leave behind.

The check is the churn test's oracle: every randomized sequence of
create / modify / transition / rename / move / delete ends with :func:`check`
and expects it to find nothing.

Findings are dicts rather than exceptions because a real site wants all of
them at once, not the first.

Profiles and Groups share the catalog, so every comparison is scoped by type.
A Profile has no ``group_id`` and a Group has no ``login``; comparing the
whole schema against both would report a dozen findings per object and bury
the one that mattered.
"""

from pas.plugins.identity.content.catalog import get_catalog
from pas.plugins.identity.content.catalog import group_brains
from pas.plugins.identity.content.catalog import GROUP_METADATA
from pas.plugins.identity.content.catalog import GROUP_PORTAL_TYPE
from pas.plugins.identity.content.catalog import profile_brains
from pas.plugins.identity.content.catalog import PROFILE_METADATA
from pas.plugins.identity.content.catalog import PROFILE_PORTAL_TYPE
from plone import api
from plone.dexterity.content import Container
from Products.ZCatalog.CatalogBrains import AbstractCatalogBrain


#: An object exists in the site but has no entry in the identity catalog.
MISSING = "missing"

#: The identity catalog holds an entry whose object is gone.
ORPHAN = "orphan"

#: A brain's metadata disagrees with the object it points at.
STALE = "stale"

#: Two Profiles claim the same userid. Never legitimate.
DUPLICATE_USERID = "duplicate-userid"

#: Two Profiles claim the same login name, case-insensitively.
DUPLICATE_LOGIN = "duplicate-login"

#: Two Groups claim the same group id.
DUPLICATE_GROUP_ID = "duplicate-group-id"

#: A Profile lists a group that does not exist. Not fatal -- the groups plugin
#: filters these out rather than granting anything -- but it is almost always
#: a renamed or deleted group nobody cleaned up after.
UNKNOWN_GROUP = "unknown-group"


def _finding(kind: str, path: str, detail: str) -> dict[str, str]:
    """Build one finding.

    :param kind: One of the module-level finding constants.
    :param path: Physical path the finding concerns.
    :param detail: Human-readable explanation.
    :returns: The finding.
    """
    return {"kind": kind, "path": path, "detail": detail}


def _site_objects(portal_type: str) -> dict[str, Container]:
    """Return every object of one type in the site, by physical path.

    Uses ``portal_catalog`` rather than a tree walk: the site catalog is the
    independent second opinion, which is exactly what a check of our catalog
    needs. An object absent from *both* is out of this function's reach and is
    the one drift mode the check cannot see -- stated here rather than left to
    be discovered.

    :param portal_type: The type to collect.
    :returns: Mapping of path to object.
    """
    portal_catalog = api.portal.get_tool("portal_catalog")
    return {
        brain.getPath(): brain._unrestrictedGetObject()
        for brain in portal_catalog.unrestrictedSearchResults(portal_type=portal_type)
    }


def _expected(obj: Container, column: str) -> object:
    """Return what a metadata column should hold for an object.

    :param obj: The catalogued object.
    :param column: Metadata column name.
    :returns: The value the brain should carry.
    """
    if column == "review_state":
        return api.content.get_state(obj)
    value = getattr(obj, column, None)
    # ZCatalog calls a callable attribute when it records metadata, so the
    # check has to call it too -- otherwise every computed column, Title
    # among them, reads as permanently stale.
    return value() if callable(value) else value


def _check_metadata(
    path: str,
    obj: Container,
    brain: AbstractCatalogBrain,
    columns: tuple[str, ...],
) -> list[dict[str, str]]:
    """Compare one brain's metadata against its object.

    :param path: Physical path of the object.
    :param obj: The catalogued object.
    :param brain: Its brain in the identity catalog.
    :param columns: The columns that mean something for this type.
    :returns: Zero or more ``STALE`` findings.
    """
    findings = []
    for column in columns:
        expected = _expected(obj, column)
        actual = getattr(brain, column, None)
        # Missing.Value, None and empty all read as "nothing stored"; a field
        # the user never filled in is not drift.
        if (expected or None) != (actual or None):
            findings.append(
                _finding(
                    STALE,
                    path,
                    f"{column}: catalog has {actual!r}, object has {expected!r}",
                )
            )
    return findings


def _check_duplicates(
    objects: dict[str, Container],
    kind: str,
    attribute: str,
    fold: bool = False,
) -> list[dict[str, str]]:
    """Report an identifying attribute claimed by more than one object.

    :param objects: Mapping of path to object.
    :param kind: Finding kind to report.
    :param attribute: Attribute that has to be unique.
    :param fold: Compare case-insensitively.
    :returns: Zero or more duplicate findings.
    """
    findings = []
    seen: dict[str, str] = {}
    for path in sorted(objects):
        value = getattr(objects[path], attribute, None)
        if not value:
            continue
        key = value.lower() if fold else value
        if key in seen:
            findings.append(
                _finding(
                    kind, path, f"{attribute} {value!r} is also used by {seen[key]}"
                )
            )
        else:
            seen[key] = path
    return findings


def _check_group_references(
    profiles: dict[str, Container], groups: dict[str, Container]
) -> list[dict[str, str]]:
    """Report Profiles listing groups that do not exist.

    :param profiles: Mapping of path to Profile.
    :param groups: Mapping of path to Group.
    :returns: Zero or more ``UNKNOWN_GROUP`` findings.
    """
    known = {
        getattr(group, "group_id", None)
        for group in groups.values()
        if getattr(group, "group_id", None)
    }
    findings = []
    for path in sorted(profiles):
        for group_id in getattr(profiles[path], "group_ids", None) or ():
            if group_id not in known:
                findings.append(
                    _finding(UNKNOWN_GROUP, path, f"no group has the id {group_id!r}")
                )
    return findings


def _check_type(
    portal_type: str,
    brains: list[AbstractCatalogBrain],
    columns: tuple[str, ...],
) -> tuple[dict[str, Container], list[dict[str, str]]]:
    """Compare one content type's objects against its brains.

    :param portal_type: The type to check.
    :param brains: The identity catalog's brains for that type.
    :param columns: Metadata columns that mean something for it.
    :returns: The objects found, and the findings.
    """
    objects = _site_objects(portal_type)
    by_path = {brain.getPath(): brain for brain in brains}

    findings = []
    for path in sorted(objects):
        brain = by_path.get(path)
        if brain is None:
            findings.append(
                _finding(MISSING, path, f"{portal_type} is not in the catalog")
            )
            continue
        findings.extend(_check_metadata(path, objects[path], brain, columns))

    for path in sorted(set(by_path) - set(objects)):
        findings.append(_finding(ORPHAN, path, "Catalog entry has no object behind it"))
    return objects, findings


def check() -> list[dict[str, str]]:
    """Compare the identity catalog against the site.

    :returns: All findings, empty when the catalog is consistent.
    """
    catalog = get_catalog()

    profiles, findings = _check_type(
        PROFILE_PORTAL_TYPE, profile_brains(catalog), PROFILE_METADATA
    )
    groups, group_findings = _check_type(
        GROUP_PORTAL_TYPE, group_brains(catalog), GROUP_METADATA
    )
    findings.extend(group_findings)

    findings.extend(_check_duplicates(profiles, DUPLICATE_USERID, "userid"))
    findings.extend(_check_duplicates(profiles, DUPLICATE_LOGIN, "login", fold=True))
    findings.extend(_check_duplicates(groups, DUPLICATE_GROUP_ID, "group_id"))
    findings.extend(_check_group_references(profiles, groups))
    return findings
