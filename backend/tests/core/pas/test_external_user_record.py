"""Where a first external login puts the user record.

An identity arrives, a userid is minted, and something has to become the
account the rest of Plone can see. That something is a content object, and
never a ``source_users`` row: the object is the account -- this plugin
enumerates it and ``_authenticate_content_password`` signs in against a
password held on it -- so a row beside it is a second record of the same
person. It turns up in the ZMI, nothing keeps it in step with the object, and
it outlives what it shadows. It used to be written on every federated first
login regardless, which is how the demo identity provider ended up with
``alice`` and ``ericof`` in both stores at once.

The plugin does not create the object itself. A subscriber to
``IExternalIdentityAuthenticated`` does, the same way ``doAddUser`` leaves the
credential to whoever owns one -- and the subscriber below is this module's
stand-in for the shipped one, with a stub type in place of ``UserProfile``.
Using the real type here would prove only that the plugin works with the one
type this package happens to ship; see ``tests/core/test_external_user_record.py``
for that half.
"""

from . import CLAIMS
from . import DEX_IDENTITY
from .stubs import add_type
from .stubs import install_enumerator
from .stubs import IStubDocumentSchema
from .stubs import IStubUserSchema
from .stubs import NOT_A_USER
from .stubs import USER_TYPE
from .stubs import USERS
from pas.plugins.identity.core.events import ExternalIdentityAuthenticated
from pas.plugins.identity.core.pas import EXTRACTOR
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.core.pas.plugin import USER_CONTAINER_PATH_RECORD
from pas.plugins.identity.core.pas.plugin import USER_CONTENT_TYPE_RECORD
from plone import api
from zope.component import getGlobalSiteManager

import pytest


@pytest.fixture
def credentials():
    """Return credentials as the callback view deposits them.

    :returns: The credentials mapping.
    """
    provider, subject = DEX_IDENTITY
    return {
        "extractor": EXTRACTOR,
        "provider": provider,
        "subject": subject,
        "claims": CLAIMS,
    }


@pytest.fixture
def site(portal, acl_users):
    """A site with the stub types, a container and an enumerator.

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


@pytest.fixture
def claiming(configured):
    """Register a subscriber that creates the user object, and remove it after.

    What the shipped subscriber does, reduced to the one line this module
    cares about. Registered here rather than assumed, because "core declines
    and somebody else creates" is the whole contract under test: without a
    claimant there is no account, which is the case its own test covers.

    :param configured: The configured Plone site.
    :returns: The Plone site.
    """

    def create(event) -> None:
        # Idempotent, like the shipped ``ensure_profile``: the event fires on
        # every login, not only the first.
        if event.userid in configured[USERS]:
            return
        with api.env.adopt_roles(["Manager"]):
            api.content.create(
                container=configured[USERS],
                type=USER_TYPE,
                id=event.userid,
                userid=event.userid,
                login=event.userid,
            )

    registry = getGlobalSiteManager()
    registry.registerHandler(create, (ExternalIdentityAuthenticated,))
    yield configured
    registry.unregisterHandler(create, (ExternalIdentityAuthenticated,))


class TestASiteWithAUserTypeOfItsOwn:
    """The bug: a second record of the same person, written every time."""

    @pytest.fixture(autouse=True)
    def _setup(self, claiming, acl_users, credentials) -> None:
        self.portal = claiming
        self.acl_users = acl_users
        self.plugin = acl_users[PLUGIN_ID]
        self.credentials = credentials

    def test_no_source_users_account_is_created(self):
        """What ``acl_users/source_users/manage_users`` was showing.

        Asserted on ``getUserIds``, which is that page's own listing.
        ``getUserById`` is not the question: PlonePAS's user manager answers
        it for a principal it does not hold, so it cannot show an absence.
        """
        userid, _ = self.plugin.authenticateCredentials(self.credentials)

        assert userid not in self.acl_users.source_users.getUserIds()

    def test_the_content_object_is_the_account(self):
        userid, _ = self.plugin.authenticateCredentials(self.credentials)

        assert self.portal[USERS][userid].userid == userid

    def test_the_user_is_still_retrievable(self):
        """Declining to write the row is only correct if the user exists
        anyway -- through the claimant's object and the enumerator."""
        userid, _ = self.plugin.authenticateCredentials(self.credentials)

        assert api.user.get(userid=userid) is not None

    def test_signing_in_again_is_unaffected(self):
        """The second login takes the ``touch`` branch, which never created
        an account. Asserted because "creates nothing" is easy to satisfy by
        breaking the whole path."""
        first, _ = self.plugin.authenticateCredentials(self.credentials)
        second, _ = self.plugin.authenticateCredentials(self.credentials)

        assert first == second
        assert first not in self.acl_users.source_users.getUserIds()


class TestNothingClaimsTheUser:
    """A site pointed at a user type with nothing creating one.

    The plugin writes nothing here and the login still succeeds, so the
    principal exists as an identity and as nothing else. It cannot be fixed
    from inside the plugin -- what would create the object is the part that is
    missing -- so it is said once, loudly, at the moment it becomes true.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, configured, acl_users, credentials) -> None:
        self.portal = configured
        self.acl_users = acl_users
        self.plugin = acl_users[PLUGIN_ID]
        self.credentials = credentials

    def test_no_account_is_invented(self):
        userid, _ = self.plugin.authenticateCredentials(self.credentials)

        assert userid not in self.acl_users.source_users.getUserIds()

    def test_it_is_reported(self, caplog):
        self.plugin.authenticateCredentials(self.credentials)

        assert "as an identity and as nothing else" in caplog.text

    def test_the_warning_names_the_type_that_was_not_created(self, caplog):
        """A site reading this has to know which record to look at."""
        self.plugin.authenticateCredentials(self.credentials)

        assert USER_TYPE in caplog.text
