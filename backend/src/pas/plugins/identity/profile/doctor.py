"""Consistency check for the Profile catalog (§4.7).

A dedicated catalog is a second copy of the truth, and a second copy drifts.
This module answers "has it?" without repairing anything: repair is
:meth:`~pas.plugins.identity.profile.catalog.IdentityProfileCatalog.clearFindAndRebuild`,
and the two are kept apart on purpose so that a scheduled check can run
read-only and so the churn test asserts against findings rather than against
whatever a repair happened to leave behind.

The check is the churn test's oracle (§8.3): every randomized sequence of
create / modify / transition / rename / move / delete ends with
:func:`check` and expects it to find nothing.

Findings are dicts rather than exceptions because a real site wants all of
them at once, not the first.
"""

from pas.plugins.identity.profile.catalog import all_brains
from pas.plugins.identity.profile.catalog import get_catalog
from pas.plugins.identity.profile.catalog import METADATA
from pas.plugins.identity.profile.catalog import PROFILE_PORTAL_TYPE
from plone import api
from typing import Any


#: A Profile exists in the site but has no entry in the Profile catalog.
MISSING = "missing"

#: The Profile catalog holds an entry whose object is gone.
ORPHAN = "orphan"

#: A brain's metadata disagrees with the object it points at.
STALE = "stale"

#: Two Profiles claim the same userid. Never legitimate (I1).
DUPLICATE_USERID = "duplicate-userid"

#: Two Profiles claim the same login name, case-insensitively.
DUPLICATE_LOGIN = "duplicate-login"


def _finding(kind: str, path: str, detail: str) -> dict[str, str]:
    """Build one finding.

    :param kind: One of the module-level finding constants.
    :param path: Physical path the finding concerns.
    :param detail: Human-readable explanation.
    :returns: The finding.
    """
    return {"kind": kind, "path": path, "detail": detail}


def _site_profiles() -> dict[str, Any]:
    """Return every Profile in the site, by physical path.

    Uses ``portal_catalog`` rather than a tree walk: the site catalog is the
    independent second opinion, which is exactly what a check of our catalog
    needs. A Profile absent from both is out of this function's reach and is
    the one drift mode the check cannot see -- stated here rather than left to
    be discovered.

    :returns: Mapping of path to Profile object.
    """
    portal_catalog = api.portal.get_tool("portal_catalog")
    profiles = {}
    for brain in portal_catalog.unrestrictedSearchResults(
        portal_type=PROFILE_PORTAL_TYPE
    ):
        profiles[brain.getPath()] = brain._unrestrictedGetObject()
    return profiles


def _check_metadata(path: str, obj: Any, brain: Any) -> list[dict[str, str]]:
    """Compare one brain's metadata against its object.

    :param path: Physical path of the Profile.
    :param obj: The Profile.
    :param brain: Its brain in the Profile catalog.
    :returns: Zero or more ``STALE`` findings.
    """
    findings = []
    for column in METADATA:
        if column == "review_state":
            expected = api.content.get_state(obj)
        else:
            expected = getattr(obj, column, None)
        actual = getattr(brain, column, None)
        # Missing.Value and None both read as "nothing stored"; a field the
        # user never filled in is not drift.
        if (expected or None) != (actual or None):
            findings.append(
                _finding(
                    STALE,
                    path,
                    f"{column}: catalog has {actual!r}, object has {expected!r}",
                )
            )
    return findings


def _check_duplicates(profiles: dict[str, Any]) -> list[dict[str, str]]:
    """Report userids and logins claimed by more than one Profile.

    :param profiles: Mapping of path to Profile.
    :returns: Zero or more duplicate findings.
    """
    findings = []
    for kind, attribute, fold in (
        (DUPLICATE_USERID, "userid", False),
        (DUPLICATE_LOGIN, "login", True),
    ):
        seen: dict[str, str] = {}
        for path in sorted(profiles):
            value = getattr(profiles[path], attribute, None)
            if not value:
                continue
            key = value.lower() if fold else value
            if key in seen:
                findings.append(
                    _finding(
                        kind,
                        path,
                        f"{attribute} {value!r} is also used by {seen[key]}",
                    )
                )
            else:
                seen[key] = path
    return findings


def check() -> list[dict[str, str]]:
    """Compare the Profile catalog against the site.

    :returns: All findings, empty when the catalog is consistent.
    """
    catalog = get_catalog()
    profiles = _site_profiles()
    brains = {brain.getPath(): brain for brain in all_brains(catalog)}

    findings = []
    for path in sorted(profiles):
        brain = brains.get(path)
        if brain is None:
            findings.append(
                _finding(MISSING, path, "Profile is not in the profile catalog")
            )
            continue
        findings.extend(_check_metadata(path, profiles[path], brain))

    for path in sorted(set(brains) - set(profiles)):
        findings.append(
            _finding(ORPHAN, path, "Catalog entry has no Profile behind it")
        )

    findings.extend(_check_duplicates(profiles))
    return findings
