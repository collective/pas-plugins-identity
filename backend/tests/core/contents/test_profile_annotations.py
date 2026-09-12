"""Every Profile keeps its own annotations.

``zope.annotation`` stores an object's annotations in whatever
``__annotations__`` attribute it finds on it. A type annotation anywhere in the
Profile class body gives the *class* one -- a plain dict -- and every Profile
then reads and writes that single, non-persistent mapping. Nothing raises: what
a provider last wrote for one person is read back for the next, and their
sign-in stops syncing a name it believes the user edited.
"""

from pas.plugins.identity.core.contents.profile import UserProfile
from zope.annotation.interfaces import IAnnotations

import pytest


KEY = "pas.plugins.identity.tests.annotation"


class TestAnnotationsAreEachProfilesOwn:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_profile) -> None:
        self.alice = make_profile("alice")
        self.bob = make_profile("bob")

    def test_the_class_has_no_annotations_of_its_own(self):
        """The cause, checked directly, so a failure names it."""
        assert "__annotations__" not in vars(UserProfile)

    def test_one_profiles_annotation_is_not_anothers(self):
        IAnnotations(self.alice)[KEY] = "alice's"

        assert KEY not in IAnnotations(self.bob)
