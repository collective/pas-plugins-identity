"""Version 1009: the column ``@users`` reads a Profile picture from.

Populated rather than merely created: read as ``Missing.Value`` the column
says "no picture", and every Profile picture would drop out of ``@users`` and
the ``picture`` claim until that Profile's next write.
"""

from ... import PNG
from plone.namedfile.file import NamedBlobImage

import pytest


class TestWhoHasAPictureIsRecorded:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, catalog, upgrade_from, make_profile) -> None:
        self.catalog = catalog
        self.upgrade_from = upgrade_from
        profile = make_profile("alice", fullname="Alice Liddell")
        profile.image = NamedBlobImage(data=PNG, filename="alice.png")

    def test_the_column_is_filled_after_the_upgrade(self):
        # Removed first, so this tests the upgrade rather than the install.
        self.catalog.delColumn("image_scales")
        assert "image_scales" not in self.catalog.schema()

        self.upgrade_from("1008")

        brain = self.catalog.unrestrictedSearchResults(userid="alice")[0]
        assert "image" in brain.image_scales
