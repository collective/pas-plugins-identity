"""``UserGroup`` -- the content object that is a group.

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
    return "UserGroup"


@pytest.fixture(scope="class")
def payload(portal_type: str) -> dict:
    """Return what it takes to create one.

    :param portal_type: The type under test.
    :returns: A creation payload.
    """
    return {
        "type": portal_type,
        "id": "reviewers",
        "group_id": "reviewers",
        "title": "Reviewers",
    }


class TestTheFTI:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, portal_type: str, get_fti) -> None:
        self.portal = portal
        self.fti: DexterityFTI = get_fti(portal_type)

    @pytest.mark.parametrize(
        "attr,expected",
        [
            ("title", "User Group"),
            ("klass", "pas.plugins.identity.core.contents.group.UserGroup"),
            ("schema", "pas.plugins.identity.core.contents.group.IUserGroupSchema"),
            ("global_allow", True),
            ("add_permission", "pas.plugins.identity.usergroup.add"),
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

        ``group_membership`` is on the group as well as on the Profile, which
        is what nesting is: a group that is a member of another group.
        """
        assert self.fti.behaviors[idx] == behavior

    def test_no_other_behaviors(self):
        """The list above is the whole list."""
        assert len(self.fti.behaviors) == 3


class TestVersioning:
    def test_versionable(self, portal_type: str, versionable_content_types):
        """Registered in ``portal_repository``, which is the half the FTI
        cannot show. See the same test on ``UserProfile`` for why it exists."""
        assert portal_type in versionable_content_types

    def test_create_initial_version_after_adding(self, last_version, content_instance):
        """Adding content creates version 0."""
        version = last_version(content_instance)

        assert version.comment.default == "Initial version"
        assert version.version_id == 0

    def test_create_version_on_save(
        self, notify_modified, history, last_version, content_instance
    ):
        """Modifying content creates a new version."""
        from plone import api

        with api.env.adopt_roles(["Manager"]):
            content_instance.title = "Peer Reviewers"
            notify_modified(content_instance)

        assert len(history(content_instance)) == 2
        version = last_version(content_instance)
        assert version.comment is None
        assert version.version_id == 1
