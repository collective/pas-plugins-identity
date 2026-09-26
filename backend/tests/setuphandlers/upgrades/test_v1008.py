"""Version 1008: the column the profile gate explains a hold from.

Unlike the column v1007 added, an empty one here is not harmless. A brain
reads a column nothing has indexed into as ``Missing.Value``, which
``missing_from_brain`` treats as "not asked yet" and answers by scanning
columns for emptiness -- the behaviour the column exists to replace. So the
step has to populate it, and a site whose users are all complete would
otherwise wait for a write that never comes.
"""

from Missing import Value as MISSING_VALUE

import pytest


class TestWhatIsMissingIsRecorded:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, catalog, upgrade_from, make_profile) -> None:
        self.catalog = catalog
        self.upgrade_from = upgrade_from
        self.make_profile = make_profile

    def test_the_column_exists_after_the_upgrade(self):
        # Removed first, so this tests the upgrade rather than the install.
        self.catalog.delColumn("missing_fields")
        assert "missing_fields" not in self.catalog.schema()

        self.upgrade_from("1007")

        assert "missing_fields" in self.catalog.schema()

    def test_the_column_is_filled_rather_than_merely_created(self):
        """The half no XML can carry, and the half that matters: read as
        ``Missing.Value`` the column sends every caller back to the old scan,
        with nothing to say it did."""
        profile = self.make_profile("alice", fullname="Alice Liddell")
        profile.fullname = ""
        self.catalog.delColumn("missing_fields")

        self.upgrade_from("1007")

        brain = self.catalog.unrestrictedSearchResults(userid="alice")[0]
        assert brain.missing_fields is not MISSING_VALUE
        assert "fullname" in brain.missing_fields
