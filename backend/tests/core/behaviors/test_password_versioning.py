"""What versioning does to a credential kept on the content object.

The password behavior stores its hash in an annotation rather than in a
Dexterity field, and three places in this package explain why in the same
terms: a field would be serialized by ``plone.restapi``, exported by
GenericSetup, indexable, and snapshotted by versioning, so an annotation is
invisible to all four.

Three of those four are true. Versioning is not: CMFEditions deep-copies
``__annotations__`` into the snapshot. Switching versioning on for
``UserProfile`` therefore reopened exactly the disclosure the annotation was
chosen to avoid, and in the worst available shape -- a superseded credential
accumulating in ``portal_repository``, where a password change no longer
retires the old hash and nothing says so.

:mod:`pas.plugins.identity.core.versioning` closes it. These are the tests
that say it stays closed, and the last one is the one that matters: it
switches the guard off and proves the leak comes back, because a test that
passes with the fix removed is not evidence of anything.
"""

from pas.plugins.identity.core.behaviors.password import ANNOTATION_KEY
from pas.plugins.identity.core.interfaces import ICredentialStorage
from pas.plugins.identity.core.versioning import MODIFIER_ID
from plone import api
from zope.annotation.interfaces import IAnnotations

import pytest


#: The behavior under test, off unless a site opts in.
BEHAVIOR = "pas.plugins.identity.password"


def hash_of(obj) -> bytes | None:
    """Return the stored hash, or ``None`` when there is none.

    :param obj: A Profile, or a version of one.
    :returns: The hash as bytes.
    """
    stored = dict(IAnnotations(obj)).get(ANNOTATION_KEY)
    return None if stored is None else bytes(stored["hash"])


@pytest.fixture
def enabled(portal):
    """Switch the password behavior on for ``UserProfile``.

    :param portal: The Plone site.
    """
    fti = api.portal.get_tool("portal_types")["UserProfile"]
    fti.behaviors = (*fti.behaviors, BEHAVIOR)
    yield
    fti.behaviors = tuple(b for b in fti.behaviors if b != BEHAVIOR)


class PasswordVersioningCase:
    """A Profile holding a password, in a site that versions Profiles."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, enabled, make_profile) -> None:
        self.portal = portal
        self.profile = make_profile("alice", email="alice@example.com")
        self.repo = api.portal.get_tool("portal_repository")


class TestTheGuardIsInstalled(PasswordVersioningCase):
    def test_the_modifier_is_registered(self):
        """By the install handler, whether or not the behavior is enabled
        anywhere: a site switching it on later must not have to remember."""
        assert MODIFIER_ID in api.portal.get_tool("portal_modifier").objectIds()

    def test_the_modifier_is_enabled(self):
        """Registered and disabled would be the worst of both -- the guard
        visible in the ZMI and credentials going into history regardless."""
        modifier = api.portal.get_tool("portal_modifier").get(MODIFIER_ID)

        assert modifier.isEnabled() is True


class TestASupersededPasswordIsNotRecoverable(PasswordVersioningCase):
    def test_the_old_hash_is_not_in_the_version(self):
        """The whole point. Changing a password has to retire the old hash,
        and a copy in the version repository would mean it did not."""
        ICredentialStorage(self.profile).set_password("first-password!")
        old = hash_of(self.profile)
        self.repo.save(self.profile, comment="before the change")

        ICredentialStorage(self.profile).set_password("second-password!")

        assert hash_of(self.repo.retrieve(self.profile).object) != old

    def test_the_premise(self):
        """Two different passwords hash differently. Without this the test
        above would pass on a site where hashing did nothing."""
        ICredentialStorage(self.profile).set_password("first-password!")
        first = hash_of(self.profile)

        ICredentialStorage(self.profile).set_password("second-password!")

        assert first != hash_of(self.profile)


class TestAVersionDoesNotLockTheAccountOut(PasswordVersioningCase):
    """Skipping the credential on the way in leaves ``None`` in the snapshot,
    so a retrieved version has to be given the working copy's hash on the way
    out. Otherwise reverting a Profile would clear its password -- which is a
    silent account lockout, and version history is not where a site should be
    deciding that."""

    def test_the_current_password_still_works_on_a_retrieved_version(self):
        ICredentialStorage(self.profile).set_password("only-password!")
        self.repo.save(self.profile, comment="v0")
        self.profile.fullname = "Alice Renamed"

        recovered = self.repo.retrieve(self.profile).object

        assert ICredentialStorage(recovered).check_password("only-password!") is True

    def test_a_profile_with_no_password_retrieves_without_one(self):
        """The branch where there is nothing to carry across."""
        self.repo.save(self.profile, comment="v0")

        assert hash_of(self.repo.retrieve(self.profile).object) is None


class TestWithoutTheGuard(PasswordVersioningCase):
    """The mutation test. Every assertion above passes with the modifier
    removed unless this one fails with it removed."""

    @pytest.fixture(autouse=True)
    def _disabled(self, portal):
        """Switch the modifier off for the duration of the test.

        :param portal: The Plone site.
        """
        modifiers = api.portal.get_tool("portal_modifier")
        modifiers.edit(MODIFIER_ID, enabled=False)
        yield
        modifiers.edit(MODIFIER_ID, enabled=True)

    def test_the_old_hash_comes_back(self):
        ICredentialStorage(self.profile).set_password("first-password!")
        old = hash_of(self.profile)
        self.repo.save(self.profile, comment="before the change")

        ICredentialStorage(self.profile).set_password("second-password!")

        assert hash_of(self.repo.retrieve(self.profile).object) == old


class TestTheModifierIsDefensive:
    """CMFEditions calls the retrieve hook in more shapes than the happy path,
    and a modifier that raises takes the whole retrieval with it."""

    def test_no_working_copy_is_not_an_error(self, portal):
        """``RetainUIDs`` and the other standard modifiers guard the same way:
        the tool calls this with no working copy in some paths."""
        from pas.plugins.identity.core.versioning import SkipCredentialAnnotation

        assert SkipCredentialAnnotation().afterRetrieveModifier(None, object()) == (
            [],
            [],
            {},
        )

    def test_an_unannotatable_clone_is_not_an_error(self, portal, make_profile):
        """Nothing here can annotate a bare object, and asking is how you find
        out rather than how you crash."""
        from pas.plugins.identity.core.versioning import SkipCredentialAnnotation

        profile = make_profile("dora", email="dora@example.com")

        assert SkipCredentialAnnotation().afterRetrieveModifier(profile, object()) == (
            [],
            [],
            {},
        )

    def test_nothing_to_skip_when_there_is_no_credential(self, portal, make_profile):
        """A Profile on a site that never enabled the password behaviour has
        no annotation, and the clone hook says so rather than answering for an
        object that is not there."""
        from pas.plugins.identity.core.versioning import SkipCredentialAnnotation

        profile = make_profile("erin", email="erin@example.com")

        assert SkipCredentialAnnotation().getOnCloneModifiers(profile) is None


class TestUnregistering:
    def test_removing_it_twice_is_harmless(self, portal):
        """The uninstall profile can be reapplied, and a handler that raised
        the second time would make that a broken operation."""
        from pas.plugins.identity.core.versioning import unregister_modifier

        modifiers = api.portal.get_tool("portal_modifier")

        assert unregister_modifier(modifiers) is True
        assert unregister_modifier(modifiers) is False

    def test_registering_twice_is_harmless(self, portal):
        """Same reason, from the other side: reapplying the default profile
        must not add a second copy to the chain."""
        from pas.plugins.identity.core.versioning import register_modifier

        modifiers = api.portal.get_tool("portal_modifier")

        assert register_modifier(modifiers) is False
