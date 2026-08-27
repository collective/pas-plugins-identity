"""Adding a user on a site that keeps its users as content.

Core can create the content object a user *is*, without knowing what type
that is. Two registry records say which portal type and where, and the type
has to provide ``IUserContent`` -- an interface core declares and an optional
layer's content type provides, which is the same direction every other
extension point here runs in.

The point of the design is what happens when those records are empty, which
is every site until somebody sets them. PAS walks the registered adders and
stops at the first that returns true, so declining is how a plugin says "not
mine" -- ``ZODBUserManager.doAddUser`` already returns ``False`` on a
duplicate id. An unconfigured site therefore behaves exactly as it did
before, and that is what most of this module asserts.

The stub type is built here rather than borrowed from the ``[content]``
extra on purpose: core must be able to do this for a type it has never heard
of, and a test that used ``Profile`` would prove only that core works with
the one type this package happens to ship.
"""

from .stubs import add_type
from .stubs import install_enumerator
from .stubs import IStubDocumentSchema
from .stubs import IStubUserSchema
from .stubs import NOT_A_USER
from .stubs import USER_TYPE
from .stubs import USERS
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.core.pas.plugin import USER_CONTAINER_PATH_RECORD
from pas.plugins.identity.core.pas.plugin import USER_CONTENT_TYPE_RECORD
from plone import api

import pytest


@pytest.fixture
def site(portal, acl_users):
    """A site with the stub types, a container and an enumerator.

    The enumerator is the half core does not provide, and without it PAS
    cannot find the user it just asked for -- see :mod:`.stubs`.

    :param portal: The Plone site.
    :param acl_users: The site's PAS instance.
    :returns: The Plone site.
    """
    with api.env.adopt_roles(["Manager"]):
        add_type(portal, USER_TYPE, f"{IStubUserSchema.__module__}.IStubUserSchema")
        add_type(
            portal, NOT_A_USER, f"{IStubDocumentSchema.__module__}.IStubDocumentSchema"
        )
        api.content.create(container=portal, type="Folder", id=USERS)
    install_enumerator(acl_users)
    return portal


@pytest.fixture
def configured(site):
    """The same site, told to keep its users as content.

    :param site: The Plone site.
    :returns: The Plone site.
    """
    api.portal.set_registry_record(USER_CONTENT_TYPE_RECORD, USER_TYPE)
    api.portal.set_registry_record(USER_CONTAINER_PATH_RECORD, USERS)
    return site


class TestAnUnconfiguredSite:
    """The default, and the one that must not change."""

    @pytest.fixture(autouse=True)
    def _setup(self, site, acl_users) -> None:
        self.portal = site
        self.plugin = acl_users[PLUGIN_ID]

    def test_the_plugin_declines(self):
        """No type configured, so this is somebody else's job."""
        assert self.plugin.doAddUser("alice", "secret") is False

    def test_a_user_is_still_created(self):
        """By source_users, exactly as before. The adder being registered
        must not break adding users on a site that ignores it."""
        with api.env.adopt_roles(["Manager"]):
            api.user.create(username="alice", email="alice@example.org")

        assert api.user.get(userid="alice") is not None

    def test_nothing_is_created_as_content(self):
        with api.env.adopt_roles(["Manager"]):
            api.user.create(username="alice", email="alice@example.org")

        assert USERS in self.portal
        assert len(self.portal[USERS]) == 0


class TestAConfiguredSite:
    @pytest.fixture(autouse=True)
    def _setup(self, configured, acl_users) -> None:
        self.portal = configured
        self.plugin = acl_users[PLUGIN_ID]

    def test_the_plugin_accepts(self):
        assert self.plugin.doAddUser("alice", "secret") is True

    def test_it_creates_the_content(self):
        self.plugin.doAddUser("alice", "secret")

        assert "alice" in self.portal[USERS]
        assert self.portal[USERS]["alice"].portal_type == USER_TYPE

    def test_it_records_the_userid_and_login(self):
        """The two attributes ``IUserContent`` promises, and the only two
        core writes."""
        self.plugin.doAddUser("alice", "secret")
        obj = self.portal[USERS]["alice"]

        assert obj.userid == "alice"
        assert obj.login == "alice"

    def test_the_api_reaches_this_plugin(self):
        """End to end. Calling doAddUser directly proves nothing about
        whether PAS ever asks this plugin, or about what happens next."""
        with api.env.adopt_roles(["Manager"]):
            api.user.create(username="alice", email="alice@example.org")

        assert "alice" in self.portal[USERS]

    def test_the_created_user_can_be_looked_up(self):
        """PAS looks the principal straight back up after adding it. A user
        that cannot be found is a user that was not really created."""
        with api.env.adopt_roles(["Manager"]):
            api.user.create(username="alice", email="alice@example.org")

        assert api.user.get(userid="alice") is not None

    def test_the_password_reaches_source_users(self):
        """Otherwise adding a user through the ordinary API would produce
        somebody who cannot sign in, which is a regression dressed as a
        feature."""
        self.plugin.doAddUser("alice", "hunter2")

        assert (
            self.portal.acl_users.source_users.authenticateCredentials({
                "login": "alice",
                "password": "hunter2",
            })
            is not None
        )

    def test_no_credential_is_stored_without_a_password(self):
        """An externally authenticated user has none, and a blank string is
        not a credential."""
        self.plugin.doAddUser("bob", "")

        assert "bob" not in self.portal.acl_users.source_users.getUserIds()
        assert "bob" in self.portal[USERS]

    def test_the_password_is_not_stored_on_the_content(self):
        """Core creates the record a user *is*. Where a credential lives is
        a separate decision, and a content object is not the default answer."""
        self.plugin.doAddUser("alice", "hunter2")
        obj = self.portal[USERS]["alice"]

        assert "hunter2" not in repr(obj.__dict__)


class TestAMisconfiguredSite:
    """Refusing beats creating something every later query has to tolerate."""

    @pytest.fixture(autouse=True)
    def _setup(self, site, acl_users) -> None:
        self.portal = site
        self.plugin = acl_users[PLUGIN_ID]
        api.portal.set_registry_record(USER_CONTAINER_PATH_RECORD, USERS)

    def test_a_type_that_is_not_a_user_is_refused(self):
        """A record naming a Document is a mistake, not an instruction."""
        api.portal.set_registry_record(USER_CONTENT_TYPE_RECORD, NOT_A_USER)

        assert self.plugin.doAddUser("alice", "secret") is False
        assert len(self.portal[USERS]) == 0

    def test_a_type_that_does_not_exist_is_refused(self):
        api.portal.set_registry_record(USER_CONTENT_TYPE_RECORD, "NoSuchType")

        assert self.plugin.doAddUser("alice", "secret") is False

    def test_a_container_that_does_not_resolve_is_refused(self):
        """Failing here beats failing at the moment somebody adds a user."""
        api.portal.set_registry_record(USER_CONTENT_TYPE_RECORD, USER_TYPE)
        api.portal.set_registry_record(USER_CONTAINER_PATH_RECORD, "nowhere")

        assert self.plugin.doAddUser("alice", "secret") is False

    def test_a_type_without_a_container_is_refused(self):
        """Both records or neither. One alone is a half-configured site."""
        api.portal.set_registry_record(USER_CONTENT_TYPE_RECORD, USER_TYPE)
        api.portal.set_registry_record(USER_CONTAINER_PATH_RECORD, "")

        assert self.plugin.doAddUser("alice", "secret") is False
