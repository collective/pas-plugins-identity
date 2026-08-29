"""Pointing core's principal records at this layer, and keeping them pointed.

Core creates a user or a group as content by reading four registry records.
This layer sets them, and the interesting part is *when*: where Profiles live
is configurable, and a profile layered on top of this one sets the container's
parent and id after this package's install handler has run. A path written
once at install names the container the layered profile is about to move.

So the path is derived from the container settings and re-derived whenever
they change. These tests are mostly about that following, because a stale
path is the failure that looks like nothing at all: core declines, the stock
plugins add the user, and the site quietly stops minting Profiles.
"""

from pas.plugins.identity.core.catalog import GROUP_PORTAL_TYPE
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.container import ID_RECORD
from pas.plugins.identity.core.container import PARENT_RECORD
from pas.plugins.identity.core.pas.plugin import GROUP_CONTAINER_PATH_RECORD
from pas.plugins.identity.core.pas.plugin import GROUP_CONTENT_TYPE_RECORD
from pas.plugins.identity.core.pas.plugin import USER_CONTAINER_PATH_RECORD
from pas.plugins.identity.core.pas.plugin import USER_CONTENT_TYPE_RECORD
from pas.plugins.identity.core.subscribers.principals import container_path
from pas.plugins.identity.core.subscribers.principals import on_folder_added
from plone import api
from zope.component.hooks import setSite

import pytest


def record(name: str) -> str:
    """Read a registry record.

    :param name: Full dotted record name.
    :returns: The value.
    """
    return api.portal.get_registry_record(name)


class TestInstallPointsCoreHere:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_the_user_type_is_the_profile(self):
        assert record(USER_CONTENT_TYPE_RECORD) == PROFILE_PORTAL_TYPE

    def test_the_group_type_is_the_identity_group(self):
        assert record(GROUP_CONTENT_TYPE_RECORD) == GROUP_PORTAL_TYPE

    def test_both_paths_name_the_container(self):
        """One container holds both, so the two records agree by
        construction rather than by being edited together."""
        assert record(USER_CONTAINER_PATH_RECORD) == "identity-profiles"
        assert record(GROUP_CONTAINER_PATH_RECORD) == "identity-profiles"


class TestItFollowsTheContainer:
    """The reason this is a subscriber rather than a value in registry.xml."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_changing_the_id_moves_the_records(self):
        """What a layered profile does: set the id after this package's
        handler has already run."""
        api.portal.set_registry_record(ID_RECORD, "people")

        assert record(USER_CONTAINER_PATH_RECORD) == "people"
        assert record(GROUP_CONTAINER_PATH_RECORD) == "people"

    def test_changing_the_parent_moves_the_records(self):
        api.portal.set_registry_record(PARENT_RECORD, "intranet")

        assert record(USER_CONTAINER_PATH_RECORD) == "intranet/identity-profiles"

    def test_both_together(self):
        api.portal.set_registry_record(PARENT_RECORD, "intranet")
        api.portal.set_registry_record(ID_RECORD, "people")

        assert record(USER_CONTAINER_PATH_RECORD) == "intranet/people"

    def test_an_unrelated_record_changes_nothing(self):
        """Every registry write in the site fires this event, and the writes
        the handler makes would otherwise call it again."""
        before = record(USER_CONTAINER_PATH_RECORD)
        api.portal.set_registry_record("pas.plugins.identity.audit_max_days", 42)

        assert record(USER_CONTAINER_PATH_RECORD) == before


class TestThePathItself:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_a_parent_of_the_site_root_gives_a_bare_id(self):
        api.portal.set_registry_record(PARENT_RECORD, "")

        assert container_path() == "identity-profiles"

    def test_slashes_are_not_doubled(self):
        """The parent is stored with or without them depending on who typed
        it, and a doubled slash traverses to nothing."""
        api.portal.set_registry_record(PARENT_RECORD, "/intranet/")

        assert container_path() == "intranet/identity-profiles"

    def test_no_id_is_no_path(self):
        """Rather than a path naming the parent, which would put Profiles
        loose in somebody's folder."""
        api.portal.set_registry_record(ID_RECORD, "")

        assert container_path() == ""


class TestTheSubscriberIsInertBeforeThereIsASite:
    """A Plone site is itself folderish, so ``on_folder_added`` fires while it
    is being added to the application root -- before ``plone.app.registry``
    has been applied and therefore before there is a registry to read.

    This is not hypothetical. It made every site creation fail with a
    traceback and a 500, in the demo stack, on a subscriber whose own tests
    were green. ``plone.app.testing`` builds its site in ``PLONE_FIXTURE``,
    before this package's ZCML is loaded, so the subscriber that breaks site
    creation is not registered when the suite creates one.

    Clearing the local site manager is what reproduces it: with no site, the
    registry utility cannot be looked up, which is exactly the state the
    application root is in.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.folder = api.content.create(
            container=portal, type="Folder", id="somewhere", title="Somewhere"
        )

    def test_it_does_not_raise_without_a_site(self):
        setSite(None)
        try:
            on_folder_added(self.folder, None)
        finally:
            setSite(self.portal)


class TestTheWholePoint:
    """What all of it was for: a user added by hand gets a Profile."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        from pas.plugins.identity.core.container import get_container

        self.portal = portal
        with api.env.adopt_roles(["Manager"]):
            self.container = get_container(create=True)

    def test_api_user_create_mints_a_profile(self):
        """The bug this started from. `api.user.create` went to source_users
        and only externally authenticated people ever got a Profile."""
        with api.env.adopt_roles(["Manager"]):
            api.user.create(username="alice", email="alice@example.org")

        assert "alice" in self.container
        assert self.container["alice"].portal_type == PROFILE_PORTAL_TYPE

    def test_the_profile_carries_the_userid_and_login(self):
        with api.env.adopt_roles(["Manager"]):
            api.user.create(username="alice", email="alice@example.org")
        profile = self.container["alice"]

        assert profile.userid == "alice"
        assert profile.login == "alice"

    def test_the_user_can_still_sign_in(self):
        """The credential goes to source_users, because a Dexterity field
        holding one is serialized, exported, indexable and versioned."""
        with api.env.adopt_roles(["Manager"]):
            api.user.create(
                username="alice", email="alice@example.org", password="hunter2!"
            )

        assert self.portal.acl_users.authenticate(
            "alice", "hunter2!", self.portal.REQUEST
        )

    def test_api_group_create_mints_an_identity_group(self):
        with api.env.adopt_roles(["Manager"]):
            api.group.create(groupname="editors", title="Editors")

        assert "editors" in self.container
        assert self.container["editors"].portal_type == GROUP_PORTAL_TYPE

    def test_api_group_add_user_records_membership(self):
        """Through ``api.group.add_user``, not ``addPrincipalToGroup``.

        The plugin-level tests in ``tests/core/pas/test_groupmanager.py``
        cannot tell whether PlonePAS's ``GroupTool`` ever reaches this
        plugin, which is the half that has already been wrong twice.
        """
        with api.env.adopt_roles(["Manager"]):
            api.user.create(username="alice", email="alice@example.org")
            api.group.create(groupname="editors", title="Editors")
            api.group.add_user(groupname="editors", username="alice")

        assert self.container["alice"].group_ids == ("editors",)

    def test_the_membership_is_visible_to_plone(self):
        """Written to the Profile *and* answered by the groups plugin.

        Recording it where nothing reads it would pass the test above.
        """
        with api.env.adopt_roles(["Manager"]):
            api.user.create(username="alice", email="alice@example.org")
            api.group.create(groupname="editors", title="Editors")
            api.group.add_user(groupname="editors", username="alice")

        groups = [g.id for g in api.group.get_groups(username="alice")]

        assert "editors" in groups

    def test_api_group_remove_user_takes_it_away(self):
        with api.env.adopt_roles(["Manager"]):
            api.user.create(username="alice", email="alice@example.org")
            api.group.create(groupname="editors", title="Editors")
            api.group.add_user(groupname="editors", username="alice")
            api.group.remove_user(groupname="editors", username="alice")

        assert self.container["alice"].group_ids == ()
        assert "editors" not in [g.id for g in api.group.get_groups(username="alice")]


@pytest.mark.no_profile_container
@pytest.mark.no_profile_container
class TestTheContainerIsMadeOnDemand:
    """The container is created lazily, on purpose: this package does not
    decide where Profiles live, and a layered profile moves them after
    install.

    It used to be a gap. Until something had made the container there was
    nowhere to put a user, so ``api.user.create`` on a site nobody had signed
    in to yet minted a ``source_users`` row and no Profile -- the one call
    most likely to be the first thing an operator does. The container is now
    made by whoever needs it first.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_the_user_is_added(self):
        with api.env.adopt_roles(["Manager"]):
            api.user.create(username="alice", email="alice@example.org")

        assert api.user.get(userid="alice") is not None

    def test_a_profile_is_minted(self):
        with api.env.adopt_roles(["Manager"]):
            api.user.create(username="alice", email="alice@example.org")

        assert "alice" in self.portal["identity-profiles"]
