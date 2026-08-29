"""The code loaded, the add-on not installed here.

This used to be ``tests/content/test_not_installed.py``, and it was about a
site that had not applied the optional layer's profile. There is no optional
layer any more, and the state it described has not gone anywhere: a Zope
instance serves more than one Plone site, this package's subscribers and
indexers are registered instance-wide, and a site next door has never heard of
it. Nothing here may raise there.

The site is uninstalled inside the fixture rather than left uninstalled by the
layer, because the layer installs the add-on for the whole suite now.
Integration testing rolls the transaction back afterwards, so the next module
gets its site back.
"""

from pas.plugins.identity import PACKAGE_NAME
from pas.plugins.identity import setuphandlers
from pas.plugins.identity.core import indexers
from pas.plugins.identity.core import subscribers
from pas.plugins.identity.core.catalog import CATALOG_ID
from pas.plugins.identity.core.catalog import query_catalog
from pas.plugins.identity.core.events import ExternalIdentityAuthenticated
from pas.plugins.identity.core.pas.profile import IdentityProfilePlugin
from pas.plugins.identity.core.pas.profile import PLUGIN_ID
from pas.plugins.identity.core.services import groups as group_services
from pas.plugins.identity.core.services import useraccount as account_services
from pas.plugins.identity.core.services.groups.get import GroupMembersGet
from pas.plugins.identity.core.services.useraccount.get import UserAccountGet
from pas.plugins.identity.core.subscribers.gate import enforcing
from pas.plugins.identity.core.subscribers.gate import incomplete_profile_url
from pas.plugins.identity.core.utils import emails
from pas.plugins.identity.setuphandlers.plugins import uninstall_profile_plugin
from plone import api
from plone.app.testing import TEST_USER_ID

import pytest


pytestmark = pytest.mark.no_profile_container


@pytest.fixture(autouse=True)
def uninstalled(portal, installer):
    """Take the add-on back out of this site.

    :param portal: The Plone site.
    :param installer: plone.app.testing's installer.
    :returns: The Plone site.
    """
    installer.uninstall_product(PACKAGE_NAME)
    return portal


class FakeEvent:
    """Stand-in for a lifecycle event.

    The handlers only ever read ``oldParent`` and ``newParent``; building a
    real event would need a real containment change, which is the thing under
    test rather than a precondition of it.
    """

    def __init__(self, old_parent=None, new_parent=None) -> None:
        """Record the two parents.

        :param old_parent: Where the object was.
        :param new_parent: Where the object is going.
        """
        self.oldParent = old_parent
        self.newParent = new_parent


class TestCatalogLookup:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_no_catalog(self):
        """The tool simply is not there."""
        assert CATALOG_ID not in self.portal.objectIds()

    def test_query_catalog_answers_none(self):
        """ "Not installed here" is an answer, not an exception."""
        assert query_catalog() is None

    def test_get_catalog_still_raises(self):
        """Code that requires the add-on should hear about it."""
        with pytest.raises(api.exc.InvalidParameterError):
            api.portal.get_tool(CATALOG_ID)


class TestIndexingSubscribersAreInert:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_moved_is_a_no_op(self):
        """A Profile appearing here indexes nowhere, quietly."""
        indexers.profile_moved(self.portal, FakeEvent(new_parent=self.portal))

    def test_will_be_moved_is_a_no_op(self):
        """Same on the way out."""
        indexers.profile_will_be_moved(self.portal, FakeEvent(old_parent=self.portal))

    def test_modified_is_a_no_op(self):
        """Same on edit."""
        indexers.profile_modified(self.portal, FakeEvent())


class TestTheGateIsInert:
    """It is bound to ``IPubAfterTraversal``, which fires for every published
    request in the instance -- including the ones that never reach a site
    running this add-on."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_nothing_is_enforced(self):
        """The record does not exist here, and its absence is the answer."""
        assert enforcing() is False

    def test_nobody_is_held_anywhere(self):
        """Which is what the authorization endpoint asks before it refuses to
        release claims about somebody."""
        assert incomplete_profile_url("alice") is None


class TestPluginIsInert:
    """The plugin class itself, in a site that never installed the add-on.

    It is not registered there, so these instantiate it directly: the point is
    that the code answers "nothing here" rather than raising, which is what a
    misconfigured site -- plugin left behind, profile removed -- would hit.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_enumeration_returns_nothing(self):
        """No catalog, no users to enumerate."""
        assert IdentityProfilePlugin().enumerateUsers() == ()

    def test_group_enumeration_returns_nothing(self):
        """No catalog, no groups."""
        assert IdentityProfilePlugin().enumerateGroups() == ()

    def test_group_ids_are_empty(self):
        """Introspection answers, rather than raising."""
        assert IdentityProfilePlugin().getGroupIds() == []

    def test_group_members_are_empty(self):
        """Including the query-shaped one."""
        assert IdentityProfilePlugin().getGroupMembers("editors") == ()

    def test_properties_return_none(self):
        """And no property sheet to offer."""
        plugin = IdentityProfilePlugin()

        assert (
            plugin.getPropertiesForUser(self.portal.acl_users.getUserById(TEST_USER_ID))
            is None
        )

    def test_deleting_declines(self):
        """There is no Profile here to be the account, so this is not its
        deletion to claim."""
        with pytest.raises(KeyError):
            IdentityProfilePlugin().doDeleteUser("alice")

    def test_the_ui_is_not_offered_a_delete(self):
        """Asked once per row by the users listing, in every site."""
        assert IdentityProfilePlugin().allowDeletePrincipal("alice") is False


class TestProfileHelpersAreInert:
    """A login in a site without the add-on must not go looking for a
    container."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_get_profile_answers_none(self):
        """Nothing to find, and no exception on the way to finding nothing."""
        assert subscribers.get_profile("alice") is None

    def test_profile_url_answers_none(self):
        """Which is what ``@users`` serializes for such a user."""
        assert subscribers.profile_url("alice") is None

    def test_ensure_profile_creates_nothing(self):
        """A login here must not mint content."""
        assert subscribers.ensure_profile("alice", "alice", {}) is None
        assert "identity-profiles" not in self.portal.objectIds()

    def test_an_authentication_event_is_survivable(self):
        """The whole handler, not just the helper under it.

        A consumer of this package's event contract may fire one in a site
        that never installed the add-on -- and the handler now does three
        things after minting a profile rather than one, each of which has to
        cope with there being no profile to do it to.
        """
        event = ExternalIdentityAuthenticated(
            "alice",
            "somewhere",
            "subject-1",
            {
                "fullname": "Alice",
                "email": "alice@example.com",
                "email_verified": True,
                "emails": (
                    {
                        "address": "alice@example.com",
                        "verified": True,
                        "primary": True,
                    },
                ),
                "raw": {},
            },
            True,
            True,
        )

        subscribers.on_authenticated(event)

        assert "identity-profiles" not in self.portal.objectIds()


class TestAddressHelpersAreInert:
    """``email`` is derived from the identity store, and there is no store
    here. A Profile carried over from an export must still be readable."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_nothing_is_verified(self):
        """Not an exception, and not everything: no store means no proof."""
        assert emails.verified_addresses("alice", ("alice@example.com",)) == ()

    def test_the_preferred_address_is_still_the_first(self):
        """Which is what keeps a first login working before any link has been
        clicked, here and on a site that does have the plugin."""
        assert (
            emails.preferred_address("alice", ("a@example.com", "b@example.com"))
            == "a@example.com"
        )

    def test_no_userid_is_no_proof(self):
        """An object being read outside any request has nobody to prove an
        address for."""
        assert emails.verified_addresses("", ("alice@example.com",)) == ()


class TestGroupAndAccountServicesAreInert:
    """Both look their plugin up by id, and neither may raise without it."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_) -> None:
        self.portal = portal
        self.request = request_

    def test_the_group_plugin_is_absent(self):
        assert group_services.get_profile_plugin() is None

    def test_the_account_plugin_is_absent(self):
        assert account_services.identity_plugin() is None

    def test_a_group_listing_is_a_404(self):
        """Rather than a traceback: a frontend asking every site the same
        question deserves an answer."""
        service = GroupMembersGet(self.portal, self.request)
        service.segments = ["staff"]

        service.reply()

        assert self.request.response.getStatus() == 404

    def test_member_brains_without_a_catalog(self):
        """The catalog is the tool the uninstall removes."""
        assert group_services.member_brains("staff", None) == []

    def test_an_account_carries_no_addresses(self):
        """No catalog, so no brain to read them off."""
        service = UserAccountGet(self.portal, self.request)

        assert service._addresses(TEST_USER_ID) == []


class TestSyncingTheCoreRecords:
    """The subscriber behind these runs on *every* registry write in the site,
    including the writes that create the records it wants to update."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_syncing_records_that_do_not_exist_is_a_no_op(self):
        """It used to raise, and the profile's own ``registry.xml`` is what
        reached it: the container settings and the records derived from them
        belonged to two profiles until they were merged, so the core half was
        always already in place. Merging inverted the order and the demo
        stack refused to start."""
        from pas.plugins.identity.core.subscribers.principals import sync_core_records

        sync_core_records()

    def test_the_records_are_still_absent(self):
        """Declining, not creating them somewhere along the way."""
        assert (
            api.portal.get_registry_record(
                "pas.plugins.identity.user_content_type", default=None
            )
            is None
        )


class TestUninstallWithoutAPlugin:
    def test_removing_an_absent_plugin_is_a_no_op(self):
        """Re-running the uninstall profile must not fail on the second pass."""
        acl_users = api.portal.get_tool("acl_users")

        uninstall_profile_plugin(acl_users)

        assert PLUGIN_ID not in acl_users.objectIds()


class TestRebuildStep:
    def test_rebuild_without_a_catalog_is_a_no_op(self):
        """The profile can be applied in a site that has since uninstalled."""

        class Context:
            """Minimal GenericSetup import context."""

            def readDataFile(self, name: str) -> str:
                """Pretend this package's profile is being imported.

                :param name: Marker file name.
                :returns: Marker content.
                """
                return "marker"

        setuphandlers.rebuild_catalog(Context())
