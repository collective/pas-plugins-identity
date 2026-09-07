"""A login may be changed by a Manager, once the account exists.

``login`` is half of the case-folded index user enumeration queries, so
rewriting it moves an account away from every sign-in, every Sharing entry
written against the old name, and every provider that maps a user by it. It
was declared with the same write permission as ``fullname`` -- which the owner
of a profile holds on their own profile, because that is what self-service
means. Correcting your name and becoming somebody else were the same action.

The fix is a permission of its own, and the interesting half is *when* it
applies. An add form checks a field's write permission against the container;
an edit form checks it against the object (``plone.autoform.utils``, in
``_filter_fields_by_permission``). So the container grants it to whoever may
file a principal, and ``user_profile_workflow`` grants it to ``Manager`` alone
in every state -- which is "anybody who may create an account may name it, and
only a Manager may rename one afterwards".

These ask the security machinery rather than reading the schema: a
``write_permission`` nothing enforces satisfies a test that only checks the
declaration.
"""

from AccessControl import getSecurityManager
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from plone import api

import pytest


#: The permission that now guards the field.
EDIT_LOGIN = "pas.plugins.identity: Edit Profile Login"

#: The one that guards the ordinary fields, which the owner does hold.
EDIT = "pas.plugins.identity: Edit Profile"


@pytest.fixture
def alice(portal, acl_users):
    """A user with a profile of their own.

    :param portal: The Plone site.
    :param acl_users: The site's PAS instance.
    :returns: Alice's profile.
    """
    acl_users.source_users.addUser("alice", "alice", "placeholder-password")
    api.user.grant_roles(username="alice", roles=["Member"])
    return api.content.create(
        container=portal["identity-profiles"],
        type=PROFILE_PORTAL_TYPE,
        id="alice",
        userid="alice",
        login="alice@example.com",
        fullname="Alice Liddell",
        emails=("alice@example.com",),
    )


@pytest.fixture
def boss(acl_users):
    """A Site Administrator.

    :param acl_users: The site's PAS instance.
    :returns: The userid.
    """
    acl_users.source_users.addUser("boss", "boss", "placeholder-password")
    api.user.grant_roles(username="boss", roles=["Site Administrator"])
    return "boss"


def may(userid: str, permission: str, obj) -> bool:
    """Report whether a user holds a permission on an object.

    :param userid: The user to check as.
    :param permission: Permission title.
    :param obj: The object to check on.
    :returns: Whether the permission is held.
    """
    with api.env.adopt_user(username=userid):
        return bool(getSecurityManager().checkPermission(permission, obj))


class TestTheOwner:
    """Self-service stops at the login."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, alice) -> None:
        self.portal = portal
        self.profile = alice

    def test_may_not_change_their_own_login(self):
        assert may("alice", EDIT_LOGIN, self.profile) is False

    def test_but_may_still_edit_their_profile(self):
        """The half being kept. If this goes red the fence is too high."""
        assert may("alice", EDIT, self.profile) is True

    @pytest.mark.parametrize("transition", ["reopen", "deactivate"])
    def test_not_in_any_other_state_either(self, transition: str):
        """The workflow states the permission in all three states, so there
        is no state in which it falls back to being acquired -- and what it
        would acquire is the container's map, where a Site Administrator has
        it."""
        api.content.transition(obj=self.profile, transition=transition)

        assert may("alice", EDIT_LOGIN, self.profile) is False


class TestASiteAdministrator:
    """The role the split is about.

    A Site Administrator may create accounts and may not rename them, which
    is two different answers to the same permission depending on what it is
    asked about.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, alice, boss) -> None:
        self.portal = portal
        self.profile = alice
        self.container = portal["identity-profiles"]

    def test_may_not_change_a_login_on_an_existing_profile(self):
        """What an edit form asks."""
        assert may("boss", EDIT_LOGIN, self.profile) is False

    def test_may_name_one_being_created(self):
        """What an add form asks, and the reason for the container grant: a
        required field they could not fill would make the type unaddable to
        exactly the role meant to add it."""
        assert may("boss", EDIT_LOGIN, self.container) is True


class TestAManager:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, alice, acl_users) -> None:
        self.portal = portal
        self.profile = alice
        acl_users.source_users.addUser("root", "root", "placeholder-password")
        api.user.grant_roles(username="root", roles=["Manager"])

    def test_may_change_a_login(self):
        """Somebody has to be able to. An account whose login is wrong and
        unfixable is an account nobody can sign in to."""
        assert may("root", EDIT_LOGIN, self.profile) is True


class TestTheFieldIsGuardedByIt:
    """The declaration and the permission have to be the same one.

    Asserted rather than assumed, because the failure is silent: a field
    naming a permission nothing manages is a field whose answer depends on
    where the profile happens to be filed.
    """

    def test_login_names_the_new_permission(self):
        from pas.plugins.identity.core.contents.profile import IUserProfileSchema
        from plone.autoform.interfaces import WRITE_PERMISSIONS_KEY

        permissions = IUserProfileSchema.queryTaggedValue(WRITE_PERMISSIONS_KEY)

        assert permissions["login"] == "pas.plugins.identity.content.editlogin"

    def test_the_other_fields_still_name_the_ordinary_one(self):
        from pas.plugins.identity.core.contents.profile import IUserProfileSchema
        from plone.autoform.interfaces import WRITE_PERMISSIONS_KEY

        permissions = IUserProfileSchema.queryTaggedValue(WRITE_PERMISSIONS_KEY)

        assert permissions["fullname"] == "pas.plugins.identity.content.edit"


class TestCreationStillWorks:
    """The paths that mint an account do not go through a form.

    ``doAddUser`` elevates to ``Manager`` and writes ``login`` through the
    Dexterity factory, which setattrs what it is handed rather than consulting
    a field's write permission. If that stopped being true, every first login
    on the site would fail.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users) -> None:
        self.portal = portal
        self.acl_users = acl_users

    def test_api_user_create_still_makes_a_profile_with_a_login(self):
        api.user.create(
            email="dana@example.com",
            username="dana",
            password="dana-placeholder-password",
        )

        profile = self.portal["identity-profiles"]["dana"]

        assert profile.login == "dana"
