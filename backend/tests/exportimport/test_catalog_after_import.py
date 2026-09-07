"""What an import leaves in the identity catalog, rather than on the object.

The importer wrote fields and then called ``reindexObject()``, which maintains
``portal_catalog`` and nothing else. The identity catalog is maintained
entirely by the subscribers in ``core/indexers``, registered for
``IObjectModifiedEvent`` and three other events, and ``reindexObject()`` fires
none of them. So every object came out right and every brain stayed stale.

The visible cost was group membership: ``getGroupsForPrincipal`` reads
``group_ids`` off the *brain*, so an import wrote the membership and nobody
was in the group. Reported by Érico against 1.0.0a2 with 280 imported users
and 149 profiles whose brains all read ``()`` (issue #30).

Newly created principals were never affected: ``api.content.create`` fires
``ObjectAddedEvent``, which the catalog does listen for. It is only the
*subsequent field writes* that were lost -- which is every update path, and
``_apply_membership`` always.

Existing tests did not catch it because they assert the object, or a count.
The count was right; only the values were wrong. Every assertion here reads a
brain or asks PAS.
"""

from . import ADDRESS
from . import USERID
from pas.plugins.identity.core.catalog import all_brains
from pas.plugins.identity.core.catalog import get_catalog
from pas.plugins.identity.core.catalog import GROUP_PORTAL_TYPE
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.exportimport import import_site
from pas.plugins.identity.exportimport.schema import DOCUMENT_VERSION
from plone import api

import pytest


#: A second address, to prove an update reaches the catalog.
OTHER_ADDRESS = "erico@example.org"


def brain_for(portal_type: str, index: str, value: str):
    """Return one principal's brain from the identity catalog.

    :param portal_type: Which type to look for.
    :param index: The index naming it, ``userid`` or ``group_id``.
    :param value: The value to match.
    :returns: The brain, or ``None``.
    """
    results = get_catalog()(portal_type=portal_type, **{index: value})
    return results[0] if results else None


class TestMembershipReachesTheCatalog:
    """``_apply_membership``, and the symptom that was reported.

    The membership was on the object the whole time. Nothing that reads
    membership reads the object.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_group, make_user) -> None:
        self.portal = portal
        make_group("site-editors", "Site Editors")
        make_user(USERID)
        import_site({
            "version": DOCUMENT_VERSION,
            "groups": [
                {
                    "group_id": "site-editors",
                    "title": "Site Editors",
                    "group_ids": [],
                }
            ],
            "users": [
                {
                    "userid": USERID,
                    "login": "ericof",
                    "emails": [ADDRESS],
                    "fullname": "Érico Andrei",
                    "group_ids": ["site-editors"],
                    "identities": [],
                }
            ],
        })

    def test_the_object_carries_it(self):
        """The half that always worked, asserted so that a failure below is
        legible as a catalog problem rather than an import one."""
        profile = self.portal["identity-profiles"][USERID]

        assert profile.group_ids == ("site-editors",)

    def test_and_so_does_the_brain(self):
        brain = brain_for(PROFILE_PORTAL_TYPE, "userid", USERID)

        assert brain is not None
        assert brain.group_ids == ("site-editors",)

    def test_and_pas_answers_with_it(self):
        """The user-facing question. ``getGroupsForPrincipal`` is a single
        metadata read, so a stale brain is an empty answer."""
        groups = api.user.get(userid=USERID).getGroups()

        assert "site-editors" in groups


class TestAGroupNestedByImportIsFound:
    """The same call, for a group rather than a user."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_group) -> None:
        self.portal = portal
        make_group("everyone", "Everyone")
        make_group("site-editors", "Site Editors")
        import_site({
            "version": DOCUMENT_VERSION,
            "groups": [
                {"group_id": "everyone", "title": "Everyone", "group_ids": []},
                {
                    "group_id": "site-editors",
                    "title": "Site Editors",
                    "group_ids": ["everyone"],
                },
            ],
            "users": [],
        })

    def test_the_brain_carries_the_nesting(self):
        brain = brain_for(GROUP_PORTAL_TYPE, "group_id", "site-editors")

        assert brain is not None
        assert brain.group_ids == ("everyone",)


class TestAnUpdatedProfileIsReindexed:
    """``_import_user`` on the update path.

    ``login`` and ``emails`` are both indexed, and ``login`` is what user
    enumeration queries: a stale one is an account that cannot be found by the
    name it now signs in with.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_user) -> None:
        self.portal = portal
        make_user(USERID, login="old-login")
        import_site({
            "version": DOCUMENT_VERSION,
            "groups": [],
            "users": [
                {
                    "userid": USERID,
                    "login": "new-login",
                    "emails": [ADDRESS, OTHER_ADDRESS],
                    "fullname": "Érico Andrei",
                    "location": "Berlin",
                    "group_ids": [],
                    "identities": [],
                }
            ],
        })
        self.brain = brain_for(PROFILE_PORTAL_TYPE, "userid", USERID)

    def test_the_brain_carries_the_new_login(self):
        assert self.brain.login == "new-login"

    def test_the_brain_carries_the_new_addresses(self):
        assert set(self.brain.emails) == {ADDRESS, OTHER_ADDRESS}

    def test_the_brain_carries_the_other_updated_fields(self):
        assert self.brain.location == "Berlin"

    def test_and_the_account_is_findable_by_its_new_login(self):
        """What the stale index actually costs.

        ``searchUsers`` rather than ``api.user.get_users``: enumeration is
        what the login index serves, and it is the call the Sharing tab and
        every login make. ``get_users`` answers from a different place and
        would pass here whatever the index said.
        """
        acl_users = api.portal.get_tool("acl_users")

        found = acl_users.searchUsers(login="new-login")

        assert [entry["login"] for entry in found] == ["new-login"]

    def test_and_no_longer_by_the_old_one(self):
        """The other half: a stale index answers to a name the account has
        stopped using, which is an account findable twice."""
        acl_users = api.portal.get_tool("acl_users")

        assert acl_users.searchUsers(login="old-login") == ()


class TestAnUpdatedGroupIsReindexed:
    """``_import_group`` on the update path."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_group) -> None:
        self.portal = portal
        make_group("site-editors", "Old Title")
        import_site({
            "version": DOCUMENT_VERSION,
            "groups": [
                {
                    "group_id": "site-editors",
                    "title": "New Title",
                    "description": "The people who edit the site.",
                    "group_ids": [],
                }
            ],
            "users": [],
        })
        self.brain = brain_for(GROUP_PORTAL_TYPE, "group_id", "site-editors")

    def test_the_brain_carries_the_new_title(self):
        assert self.brain.Title == "New Title"

    def test_the_brain_carries_the_new_description(self):
        assert self.brain.description == "The people who edit the site."


class TestNoBrainDisagreesWithItsObject:
    """The general form, which is what the reproduction measured.

    A per-field assertion catches the fields somebody thought to name. This
    catches the next one, and it is the shape the consistency check would have
    reported had anything run it after an import.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_group, make_user) -> None:
        self.portal = portal
        make_group("everyone", "Everyone")
        make_group("site-editors", "Site Editors")
        for userid in ("alice", "bob"):
            make_user(userid, login=f"{userid}-old")
        import_site({
            "version": DOCUMENT_VERSION,
            "groups": [
                {"group_id": "everyone", "title": "Everyone", "group_ids": []},
                {
                    "group_id": "site-editors",
                    "title": "Site Editors",
                    "group_ids": ["everyone"],
                },
            ],
            "users": [
                {
                    "userid": userid,
                    "login": f"{userid}-new",
                    "emails": [f"{userid}@example.com"],
                    "fullname": userid.title(),
                    "group_ids": ["site-editors"],
                    "identities": [],
                }
                for userid in ("alice", "bob")
            ],
        })

    def test_every_group_ids_agrees(self):
        # `all_brains`, not `catalog()`: a ZCatalog query with no criteria
        # returns nothing rather than everything, so the loop would not run
        # and this would pass having looked at no records.
        brains = all_brains(get_catalog())
        assert brains, "the catalog answered with nothing, so this proves nothing"
        mismatched = []
        for brain in brains:
            obj = brain.getObject()
            if tuple(brain.group_ids or ()) != tuple(obj.group_ids or ()):
                mismatched.append((
                    brain.getId(),
                    tuple(brain.group_ids or ()),
                    tuple(obj.group_ids or ()),
                ))

        assert mismatched == []

    def test_every_login_agrees(self):
        catalog = get_catalog()
        mismatched = [
            (brain.getId(), brain.login, brain.getObject().login)
            for brain in catalog(portal_type=PROFILE_PORTAL_TYPE)
            if brain.login != brain.getObject().login
        ]

        assert mismatched == []
