"""One modification event per object, however many passes wrote to it.

Each pass of :func:`~pas.plugins.identity.exportimport.import_site` used to
end in its own ``modified()``: the user pass, the membership pass, and on top
of them the identity pass's ``IdentityLinked``. Every one of them reconciled
the Profile, reindexed both catalogs and, with versioning on, cut a version --
four times for one account in a real sync of about 1,700 (issue #109).

Counted here at the event rather than at its consequences, because the event
is what the importer controls; what answers it is every subscriber's own
business.
"""

from . import ADDRESS
from . import PROVIDER
from . import SUBJECT
from . import USERID
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.events import IIdentityLinked
from pas.plugins.identity.core.interfaces import IUserGroup
from pas.plugins.identity.core.interfaces import IUserProfile
from pas.plugins.identity.exportimport import import_site
from pas.plugins.identity.exportimport.schema import DOCUMENT_VERSION
from plone import api
from zope.component import adapter
from zope.component import getGlobalSiteManager
from zope.lifecycleevent.interfaces import IObjectModifiedEvent

import pytest


def user_record(userid: str = USERID, **overrides) -> dict:
    """Return a user record naming one group and one identity.

    :param userid: The userid.
    :param overrides: Keys to replace.
    :returns: The record.
    """
    return {
        "userid": userid,
        "login": "ericof",
        "emails": [ADDRESS],
        "fullname": "Érico Andrei",
        "location": "Berlin",
        "group_ids": ["site-editors"],
        "identities": [
            {
                "provider": PROVIDER,
                "subject": SUBJECT,
                "claims": {"email": ADDRESS},
                "groups": [],
            }
        ],
        **overrides,
    }


def document(users: list, groups: list | None = None) -> dict:
    """Return a document.

    :param users: The user records.
    :param groups: The group records; one plain group by default.
    :returns: The document.
    """
    return {
        "version": DOCUMENT_VERSION,
        "groups": groups
        if groups is not None
        else [{"group_id": "site-editors", "title": "Site Editors", "group_ids": []}],
        "users": users,
    }


@pytest.fixture
def journal():
    """Record, in order, every modification of a principal and every link.

    :returns: A list of ``(kind, id)`` pairs.
    """
    entries = []

    @adapter(IUserProfile, IObjectModifiedEvent)
    def profile_modified(obj, event):
        entries.append(("modified", obj.userid))

    @adapter(IUserGroup, IObjectModifiedEvent)
    def group_modified(obj, event):
        entries.append(("modified", obj.group_id))

    @adapter(IIdentityLinked)
    def linked(event):
        entries.append(("linked", event.userid))

    gsm = getGlobalSiteManager()
    handlers = (profile_modified, group_modified, linked)
    for handler in handlers:
        gsm.registerHandler(handler)
    yield entries
    for handler in handlers:
        gsm.unregisterHandler(handler)


def modifications(journal: list, principal: str) -> int:
    """Count the modification events one principal received.

    :param journal: The recorded entries.
    :param principal: A userid or group id.
    :returns: How many.
    """
    return journal.count(("modified", principal))


class TestAProfile:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, journal) -> None:
        self.portal = portal
        self.journal = journal
        set_providers([
            ProviderConfig(provider_id=PROVIDER, driver_id="oidc-generic", title="Dex")
        ])

    def test_an_updated_one_is_modified_once(self, make_user, make_group):
        """The case that was reported: fields, membership and an identity,
        each a pass of its own, on an account the site already had."""
        make_group("site-editors", "Site Editors")
        make_user(USERID, login="old-login")
        self.journal.clear()

        import_site(document([user_record()]))

        assert modifications(self.journal, USERID) == 1

    def test_the_event_comes_after_the_identities(self, make_user, make_group):
        """So what the event reconciles is the finished Profile."""
        make_group("site-editors", "Site Editors")
        make_user(USERID, login="old-login")
        self.journal.clear()

        import_site(document([user_record()]))

        mine = [entry for entry in self.journal if entry[1] == USERID]
        assert mine[-1] == ("modified", USERID)
        assert ("linked", USERID) in mine

    def test_a_new_one_with_a_membership_is_modified_once(self):
        """Created, then written to by the membership pass: the creation
        event came before the membership existed, so it needs one more."""
        import_site(document([user_record(identities=[])]))

        assert modifications(self.journal, USERID) == 1

    def test_a_new_one_nothing_else_wrote_to_is_not_modified(self):
        """Its ``ObjectAddedEvent`` already saw everything it carries."""
        import_site(document([user_record(identities=[], group_ids=[])], groups=[]))

        assert modifications(self.journal, USERID) == 0

    def test_several_are_modified_once_each(self, make_user, make_group):
        make_group("site-editors", "Site Editors")
        for userid in ("alice", "bob"):
            make_user(userid, login=f"{userid}-old")
        self.journal.clear()

        import_site(
            document([
                user_record(userid, login=userid, emails=[f"{userid}@example.com"])
                | {"identities": []}
                for userid in ("alice", "bob")
            ])
        )

        assert modifications(self.journal, "alice") == 1
        assert modifications(self.journal, "bob") == 1

    def test_a_dry_run_modifies_nothing(self, make_user, make_group):
        make_group("site-editors", "Site Editors")
        make_user(USERID, login="old-login")
        self.journal.clear()

        import_site(document([user_record()]), dry_run=True)

        assert [entry for entry in self.journal if entry[0] == "modified"] == []


class TestAGroup:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, journal, make_group) -> None:
        self.portal = portal
        self.journal = journal
        make_group("everyone", "Everyone")
        make_group("site-editors", "Old Title")
        self.journal.clear()

    def test_an_updated_nested_one_is_modified_once(self):
        """Updated in the group pass and given a membership in its own."""
        import_site(
            document(
                [],
                groups=[
                    {"group_id": "everyone", "title": "Everyone", "group_ids": []},
                    {
                        "group_id": "site-editors",
                        "title": "New Title",
                        "group_ids": ["everyone"],
                    },
                ],
            )
        )

        assert modifications(self.journal, "site-editors") == 1


class TestTheMembershipIsReadableDuringTheImport:
    """The constraint issue #30 left behind.

    The membership pass no longer ends in an event, but ``getGroupsForPrincipal``
    reads membership off the identity catalog's brain, and the identity pass
    runs subscribers that ask it. So the membership has to be in the catalog
    before that pass, not only after the import.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_user, make_group) -> None:
        self.portal = portal
        set_providers([
            ProviderConfig(provider_id=PROVIDER, driver_id="oidc-generic", title="Dex")
        ])
        make_group("site-editors", "Site Editors")
        make_user(USERID, login="old-login")

    def test_a_link_subscriber_sees_the_imported_group(self):
        seen = []

        @adapter(IIdentityLinked)
        def ask(event):
            user = api.portal.get_tool("acl_users").getUserById(event.userid)
            seen.append(tuple(user.getGroups()))

        gsm = getGlobalSiteManager()
        gsm.registerHandler(ask)
        try:
            import_site(document([user_record()]))
        finally:
            gsm.unregisterHandler(ask)

        assert len(seen) == 1
        assert "site-editors" in seen[0]
