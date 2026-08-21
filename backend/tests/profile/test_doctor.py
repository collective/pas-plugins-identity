"""Every drift mode the consistency check claims to find, actually found.

The churn test proves the check stays quiet when nothing is wrong, which is
only half of it: a check that returns ``[]`` unconditionally would pass that
test too. These damage the catalog on purpose, one mode at a time.
"""

from pas.plugins.identity.profile import doctor
from pas.plugins.identity.profile.catalog import GROUP_PORTAL_TYPE
from pas.plugins.identity.profile.catalog import PROFILE_PORTAL_TYPE
from plone import api

import pytest


@pytest.fixture
def make_profile(portal):
    """Return a factory for Profiles, as a Manager.

    :param portal: The Plone site.
    :returns: Callable taking a userid and extra field values.
    """
    container = portal["identity-profiles"]

    def factory(userid: str, **kwargs) -> object:
        with api.env.adopt_roles(["Manager"]):
            return api.content.create(
                container=container,
                type=PROFILE_PORTAL_TYPE,
                id=kwargs.pop("id", userid),
                userid=userid,
                login=kwargs.pop("login", f"{userid}@example.com"),
                **kwargs,
            )

    return factory


def kinds(findings: list[dict[str, str]]) -> set[str]:
    """Return the set of finding kinds.

    :param findings: Findings from :func:`doctor.check`.
    :returns: Their kinds.
    """
    return {finding["kind"] for finding in findings}


class TestClean:
    def test_empty_site_is_clean(self, portal):
        """No Profiles, no findings."""
        assert doctor.check() == []

    def test_healthy_profile_is_clean(self, make_profile):
        """A Profile created through the normal path is consistent."""
        make_profile("alice", fullname="Alice Liddell")

        assert doctor.check() == []


class TestDrift:
    def test_missing_is_reported(self, catalog, make_profile):
        """A Profile the catalog never heard of."""
        profile = make_profile("alice")
        catalog.unindexObject(profile)

        findings = doctor.check()

        assert kinds(findings) == {doctor.MISSING}
        assert findings[0]["path"].endswith("/alice")

    def test_orphan_is_reported(self, catalog, make_profile):
        """A catalog entry whose object is gone."""
        make_profile("alice")
        catalog.catalog_object(
            make_profile("bob", id="bob"), "/plone/identity-profiles/ghost"
        )

        assert doctor.ORPHAN in kinds(doctor.check())

    def test_stale_metadata_is_reported(self, catalog, make_profile):
        """The object changed and nothing reindexed it."""
        profile = make_profile("alice", fullname="Alice Liddell")
        # Write straight to the object, bypassing the modified event that the
        # subscriber listens for. This is what a badly-behaved integration
        # does, and it is exactly the drift the check exists for.
        profile.fullname = "Alice Elsewhere"

        findings = doctor.check()

        assert kinds(findings) == {doctor.STALE}
        details = " ".join(finding["detail"] for finding in findings)
        assert "fullname" in details
        # Title is computed from the full name, so it goes stale with it.
        assert "Title" in details

    def test_cleared_field_is_reported(self, make_profile):
        """Clearing a field silently is drift too, and easier to miss."""
        profile = make_profile("alice", fullname="Alice Liddell")
        profile.fullname = None

        assert kinds(doctor.check()) == {doctor.STALE}

    def test_unset_field_is_not_drift(self, make_profile):
        """A field nobody filled in is not a finding."""
        make_profile("alice")

        assert doctor.check() == []

    def test_duplicate_userid_is_reported(self, make_profile):
        """Two Profiles for one userid breaks I1."""
        make_profile("alice", id="alice")
        make_profile("alice", id="alice-again", login="other@example.com")

        assert doctor.DUPLICATE_USERID in kinds(doctor.check())

    def test_duplicate_login_is_case_insensitive(self, make_profile):
        """Login names collide across case; the check has to fold too."""
        make_profile("alice", login="Alice@Example.com")
        make_profile("bob", login="alice@example.COM")

        assert doctor.DUPLICATE_LOGIN in kinds(doctor.check())

    def test_blank_login_is_not_a_duplicate(self, make_profile):
        """Two Profiles with nothing to compare are not two of the same."""
        make_profile("alice", login="")
        make_profile("bob", login="")

        assert doctor.DUPLICATE_LOGIN not in kinds(doctor.check())


@pytest.fixture
def make_group(portal):
    """Return a factory for Group content.

    :param portal: The Plone site.
    :returns: Callable taking a group id.
    """

    def factory(group_id: str, **kwargs) -> object:
        with api.env.adopt_roles(["Manager"]):
            return api.content.create(
                container=portal["identity-profiles"],
                type=GROUP_PORTAL_TYPE,
                id=kwargs.pop("id", group_id),
                group_id=group_id,
                title=kwargs.pop("title", group_id.title()),
                **kwargs,
            )

    return factory


class TestGroups:
    """The catalog holds both types, so the check has to cover both."""

    def test_a_healthy_group_is_clean(self, make_group):
        """A Group created through the normal path is consistent."""
        make_group("editors")

        assert doctor.check() == []

    def test_a_missing_group_is_reported(self, catalog, make_group):
        """Same drift mode, other type."""
        group = make_group("editors")
        catalog.unindexObject(group)

        assert doctor.MISSING in kinds(doctor.check())

    def test_stale_group_metadata_is_reported(self, make_group):
        """An edit that never reached the catalog."""
        group = make_group("editors", title="Site Editors")
        group.title = "Something Else"

        assert doctor.STALE in kinds(doctor.check())

    def test_duplicate_group_ids_are_reported(self, make_group):
        """Two groups answering to one id is never legitimate."""
        make_group("editors", id="editors")
        make_group("editors", id="editors-again")

        assert doctor.DUPLICATE_GROUP_ID in kinds(doctor.check())

    def test_a_profile_listing_an_unknown_group_is_reported(self, make_profile):
        """Almost always a renamed or deleted group nobody cleaned up after.

        Not fatal -- the groups plugin filters it out rather than granting
        anything -- but it is silent, which is exactly what the check is for.
        """
        make_profile("alice", group_ids=("ghosts",))

        findings = doctor.check()

        assert doctor.UNKNOWN_GROUP in kinds(findings)
        assert "ghosts" in " ".join(f["detail"] for f in findings)

    def test_a_known_group_is_not_reported(self, make_profile, make_group):
        """The other half."""
        make_group("editors")
        make_profile("alice", group_ids=("editors",))

        assert doctor.check() == []

    def test_profile_columns_are_not_checked_on_a_group(self, make_group):
        """One catalog schema, two types.

        A Group has no login and a Profile has no group_id; comparing the
        whole schema against both would report a dozen findings per object
        and bury the one that mattered.
        """
        make_group("editors")

        assert doctor.check() == []


class TestRebuildRepairs:
    def test_rebuild_fixes_missing(self, catalog, make_profile):
        """The repair the check points at actually repairs."""
        profile = make_profile("alice")
        catalog.unindexObject(profile)
        assert doctor.check() != []

        catalog.clearFindAndRebuild()

        assert doctor.check() == []

    def test_rebuild_fixes_orphans(self, catalog, make_profile):
        """A stale entry does not survive a rebuild."""
        profile = make_profile("alice")
        catalog.catalog_object(profile, "/plone/identity-profiles/ghost")
        assert doctor.ORPHAN in kinds(doctor.check())

        catalog.clearFindAndRebuild()

        assert doctor.check() == []
