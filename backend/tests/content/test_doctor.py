"""Every drift mode the consistency check claims to find, actually found.

The churn test proves the check stays quiet when nothing is wrong, which is
only half of it: a check that returns ``[]`` unconditionally would pass that
test too. These damage the catalog on purpose, one mode at a time.
"""

from . import PROFILE_ID
from pas.plugins.identity.content import doctor
from plone import api

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


def kinds(findings: list[dict[str, str]]) -> set[str]:
    """Return the set of finding kinds.

    :param findings: Findings from :func:`doctor.check`.
    :returns: Their kinds.
    """
    return {finding["kind"] for finding in findings}


class TestClean:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, catalog, make_profile) -> None:
        self.portal = portal
        self.catalog = catalog
        self.make_profile = make_profile

    def test_empty_site_is_clean(self):
        """No Profiles, no findings."""
        assert doctor.check() == []

    def test_healthy_profile_is_clean(self):
        """A Profile created through the normal path is consistent."""
        self.make_profile("alice", fullname="Alice Liddell")

        assert doctor.check() == []


class TestDrift:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, catalog, make_profile, allow_principals) -> None:
        self.portal = portal
        self.allow_principals = allow_principals
        self.catalog = catalog
        self.make_profile = make_profile

    def test_missing_is_reported(self):
        """A Profile the self.catalog never heard of."""
        profile = self.make_profile("alice")
        self.catalog.unindexObject(profile)

        findings = doctor.check()

        assert kinds(findings) == {doctor.MISSING}
        assert findings[0]["path"].endswith("/alice")

    def test_orphan_is_reported(self):
        """A self.catalog entry whose object is gone."""
        self.make_profile("alice")
        self.catalog.catalog_object(
            self.make_profile("bob", id="bob"), "/plone/identity-profiles/ghost"
        )

        assert doctor.ORPHAN in kinds(doctor.check())

    def test_stale_metadata_is_reported(self):
        """The object changed and nothing reindexed it."""
        profile = self.make_profile("alice", fullname="Alice Liddell")
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

    def test_cleared_field_is_reported(self):
        """Clearing a field silently is drift too, and easier to miss."""
        profile = self.make_profile("alice", fullname="Alice Liddell")
        profile.fullname = None

        assert kinds(doctor.check()) == {doctor.STALE}

    def test_unset_field_is_not_drift(self):
        """A field nobody filled in is not a finding."""
        self.make_profile("alice")

        assert doctor.check() == []

    def test_duplicate_userid_is_reported(self):
        """Two Profiles for one userid is never legitimate.

        Reachable only from separate containers now that the userid is the
        object id: one container cannot hold two objects called ``alice``.
        The catalog is not scoped to the configured container, though, so a
        Profile filed somewhere else still counts -- which is exactly the
        case this check is left in place for.
        """
        elsewhere = self.allow_principals(
            api.content.create(container=self.portal, type="Folder", id="elsewhere")
        )
        self.make_profile("alice", id="alice")
        self.make_profile(
            "alice", id="alice", container=elsewhere, login="other@example.com"
        )

        assert doctor.DUPLICATE_USERID in kinds(doctor.check())

    def test_duplicate_login_is_case_insensitive(self):
        """Login names collide across case; the check has to fold too."""
        self.make_profile("alice", login="Alice@Example.com")
        self.make_profile("bob", login="alice@example.COM")

        assert doctor.DUPLICATE_LOGIN in kinds(doctor.check())

    def test_blank_login_is_not_a_duplicate(self):
        """Two Profiles with nothing to compare are not two of the same."""
        self.make_profile("alice", login="")
        self.make_profile("bob", login="")

        assert doctor.DUPLICATE_LOGIN not in kinds(doctor.check())


class TestGroups:
    """The self.catalog holds both types, so the check has to cover both."""

    @pytest.fixture(autouse=True)
    def _setup(
        self, portal, catalog, make_group, make_profile, allow_principals
    ) -> None:
        self.portal = portal
        self.allow_principals = allow_principals
        self.catalog = catalog
        self.make_group = make_group
        self.make_profile = make_profile

    def test_a_healthy_group_is_clean(self):
        """A Group created through the normal path is consistent."""
        self.make_group("editors")

        assert doctor.check() == []

    def test_a_missing_group_is_reported(self):
        """Same drift mode, other type."""
        group = self.make_group("editors")
        self.catalog.unindexObject(group)

        assert doctor.MISSING in kinds(doctor.check())

    def test_stale_group_metadata_is_reported(self):
        """An edit that never reached the self.catalog."""
        group = self.make_group("editors", title="Site Editors")
        group.title = "Something Else"

        assert doctor.STALE in kinds(doctor.check())

    def test_duplicate_group_ids_are_reported(self):
        """Two groups answering to one id is never legitimate.

        As with a duplicate userid, this now takes two containers.
        """
        elsewhere = self.allow_principals(
            api.content.create(
                container=self.portal, type="Folder", id="elsewhere-groups"
            )
        )
        self.make_group("editors", id="editors")
        self.make_group("editors", id="editors", container=elsewhere)

        assert doctor.DUPLICATE_GROUP_ID in kinds(doctor.check())

    def test_a_profile_listing_an_unknown_group_is_reported(self):
        """Almost always a renamed or deleted group nobody cleaned up after.

        Not fatal -- the groups plugin filters it out rather than granting
        anything -- but it is silent, which is exactly what the check is for.
        """
        self.make_profile("alice", group_ids=("ghosts",))

        findings = doctor.check()

        assert doctor.UNKNOWN_GROUP in kinds(findings)
        assert "ghosts" in " ".join(f["detail"] for f in findings)

    def test_a_known_group_is_not_reported(self):
        """The other half."""
        self.make_group("editors")
        self.make_profile("alice", group_ids=("editors",))

        assert doctor.check() == []

    def test_profile_columns_are_not_checked_on_a_group(self):
        """One self.catalog schema, two types.

        A Group has no login and a Profile has no group_id; comparing the
        whole schema against both would report a dozen findings per object
        and bury the one that mattered.
        """
        self.make_group("editors")

        assert doctor.check() == []


class TestRebuildRepairs:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, catalog, make_profile) -> None:
        self.portal = portal
        self.catalog = catalog
        self.make_profile = make_profile

    def test_rebuild_fixes_missing(self):
        """The repair the check points at actually repairs."""
        profile = self.make_profile("alice")
        self.catalog.unindexObject(profile)
        assert doctor.check() != []

        self.catalog.clearFindAndRebuild()

        assert doctor.check() == []

    def test_rebuild_fixes_orphans(self):
        """A stale entry does not survive a rebuild."""
        profile = self.make_profile("alice")
        self.catalog.catalog_object(profile, "/plone/identity-profiles/ghost")
        assert doctor.ORPHAN in kinds(doctor.check())

        self.catalog.clearFindAndRebuild()

        assert doctor.check() == []
