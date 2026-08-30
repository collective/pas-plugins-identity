"""``UserProfile`` -- the content object that is a user.

Only ``portal_type`` and ``payload`` are specific to this type; the fixtures
doing the work come from ``conftest.py``.
"""

from plone.dexterity.fti import DexterityFTI

import pytest


@pytest.fixture(scope="class")
def portal_type() -> str:
    """Return the type under test.

    :returns: The portal type id.
    """
    return "UserProfile"


@pytest.fixture(scope="class")
def payload(portal_type: str) -> dict:
    """Return what it takes to create one.

    ``userid`` and ``login`` are both required: a Profile that names nobody is
    a Profile PAS cannot answer with.

    :param portal_type: The type under test.
    :returns: A creation payload.
    """
    return {
        "type": portal_type,
        "id": "carol",
        "userid": "carol",
        "login": "carol@example.org",
        "fullname": "Carol Danvers",
    }


class TestTheFTI:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, portal_type: str, get_fti) -> None:
        self.portal = portal
        self.fti: DexterityFTI = get_fti(portal_type)

    @pytest.mark.parametrize(
        "attr,expected",
        [
            ("title", "User Profile"),
            ("klass", "pas.plugins.identity.core.contents.profile.UserProfile"),
            (
                "schema",
                "pas.plugins.identity.core.contents.profile.IUserProfileSchema",
            ),
            # Structurally addable anywhere, because the lock is the add
            # permission rather than global_allow: an operator who files
            # users under /intranet/people grants it there, and nothing in
            # this package has to know.
            ("global_allow", True),
            ("add_permission", "pas.plugins.identity.userprofile.add"),
            ("filter_content_types", True),
        ],
    )
    def test_fti(self, attr: str, expected):
        assert isinstance(self.fti, DexterityFTI)
        assert getattr(self.fti, attr) == expected

    @pytest.mark.parametrize(
        "idx,behavior",
        enumerate((
            "plone.shortname",
            "pas.plugins.identity.group_membership",
            "plone.versioning",
        )),
    )
    def test_behaviors(self, idx: int, behavior: str):
        """Present, and in this order.

        Deliberately short. The standard Dublin Core behaviours would add
        metadata nobody serves, and every behaviour field is a field the
        churn test has to keep consistent.
        """
        assert self.fti.behaviors[idx] == behavior

    def test_no_other_behaviors(self):
        """The list above is the whole list. Without this, a behaviour added
        at the end is a behaviour no test notices."""
        assert len(self.fti.behaviors) == 3

    def test_namefromtitle_is_absent(self):
        """``Title()`` here is computed from the full name, which is neither
        unique nor stable. Every Profile is created with an explicit id: the
        canonical userid."""
        assert "plone.namefromtitle" not in self.fti.behaviors


class TestVersioning:
    def test_versionable(self, portal_type: str, versionable_content_types):
        """Registered in ``portal_repository``, which is the half the FTI
        cannot show.

        ``plone.versioning`` in the behaviours marks the type versionable
        everywhere a person can see and does not register a policy. A type
        with the behaviour and no ``repositorytool.xml`` entry keeps no
        history at all, and nothing else in this suite would notice.
        """
        assert portal_type in versionable_content_types

    def test_create_initial_version_after_adding(self, last_version, content_instance):
        """Adding content creates version 0."""
        version = last_version(content_instance)

        assert version.comment.default == "Initial version"
        assert version.version_id == 0

    def test_create_version_on_save(
        self, notify_modified, history, last_version, content_instance
    ):
        """Modifying content creates a new version.

        The event matters: ``at_edit_autoversion`` reacts to
        ``ObjectModifiedEvent`` and not to attribute assignment, so mutating
        the object alone leaves the history at one entry.
        """
        from plone import api

        with api.env.adopt_roles(["Manager"]):
            content_instance.fullname = "Carol Danvers-Rambeau"
            notify_modified(content_instance)

        assert len(history(content_instance)) == 2
        version = last_version(content_instance)
        assert version.comment is None
        assert version.version_id == 1
