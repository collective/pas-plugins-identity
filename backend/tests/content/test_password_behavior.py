"""Keeping a user's password on their Profile, when a site asks for it.

Off by default, and the tests that matter most are the ones asserting that.
Without the behavior a new user's password goes to ``source_users``, which is
where Plone has always kept one and where twenty years of scrutiny has been
aimed.

The hash is an annotation rather than a Dexterity field, because a field is
serialized by ``plone.restapi``, exported by GenericSetup, indexable and
snapshotted by versioning. Those four are asserted here, not argued: each one
would disclose the credential, and each would have to be remembered
separately if the storage were a field.

Authentication is core's, not this layer's. The layer serves properties,
enumeration and groups and must never become a way to log in -- see
``test_pas_plugin.TestInstallation.test_not_an_authentication_plugin`` -- so
core adapts the object to ``ICredentialStorage`` and answers.
"""

from . import PROFILE_ID
from pas.plugins.identity.content.behaviors import ANNOTATION_KEY
from pas.plugins.identity.content.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.interfaces import ICredentialStorage
from plone import api
from zope.annotation.interfaces import IAnnotations

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])

BEHAVIOR = "pas.plugins.identity.password"


@pytest.fixture
def enabled(portal):
    """Turn the behavior on for the Profile type.

    :param portal: The Plone site.
    :returns: The Plone site.
    """
    fti = portal.portal_types[PROFILE_PORTAL_TYPE]
    fti.behaviors = (*fti.behaviors, BEHAVIOR)
    return portal


class TestItIsOffByDefault:
    """The shipped answer, and the one most sites should keep."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_profile) -> None:
        self.portal = portal
        self.profile = make_profile("alice", email="alice@example.com")

    def test_the_behavior_is_not_enabled(self):
        fti = self.portal.portal_types[PROFILE_PORTAL_TYPE]

        assert BEHAVIOR not in fti.behaviors

    def test_the_profile_does_not_store_credentials(self):
        """Which is what makes core delegate to source_users."""
        assert ICredentialStorage(self.profile, None) is None


class TestStoringAPassword:
    @pytest.fixture(autouse=True)
    def _setup(self, enabled, make_profile) -> None:
        self.portal = enabled
        self.profile = make_profile("alice", email="alice@example.com")
        self.storage = ICredentialStorage(self.profile, None)

    def test_the_behavior_adapts(self):
        """Core asks for ICredentialStorage and gets an answer only here."""
        assert self.storage is not None

    def test_a_stored_password_validates(self):
        self.storage.set_password("hunter2!")

        assert self.storage.check_password("hunter2!") is True

    def test_a_wrong_password_does_not(self):
        self.storage.set_password("hunter2!")

        assert self.storage.check_password("nope") is False

    def test_nothing_stored_authenticates_nobody(self):
        """An account that has never had a password here must not be
        signable-in to with an empty one."""
        assert self.storage.check_password("") is False
        assert self.storage.check_password("anything") is False

    def test_an_empty_password_clears_rather_than_stores(self):
        """A hash of the empty string is a credential somebody can guess."""
        self.storage.set_password("hunter2!")
        self.storage.set_password("")

        assert self.storage.check_password("") is False
        assert self.storage.check_password("hunter2!") is False

    def test_the_plaintext_is_not_kept(self):
        self.storage.set_password("hunter2!")
        stored = IAnnotations(self.profile)[ANNOTATION_KEY]["hash"]

        assert b"hunter2!" not in stored
        assert stored.startswith(b"{")


class TestTheStorageIsNotAField:
    """The four paths a Dexterity field would leak through."""

    @pytest.fixture(autouse=True)
    def _setup(self, enabled, make_profile) -> None:
        self.portal = enabled
        self.profile = make_profile("alice", email="alice@example.com")
        ICredentialStorage(self.profile).set_password("hunter2!")

    def test_it_is_not_in_the_schema(self):
        """So plone.restapi cannot serialize it and GenericSetup cannot
        export it: neither walks annotations."""
        from pas.plugins.identity.content.profile import IUserProfileSchema

        assert "password" not in IUserProfileSchema.names()
        assert "hash" not in IUserProfileSchema.names()

    def test_the_rest_api_does_not_publish_it(self):
        from plone.restapi.interfaces import ISerializeToJson
        from zope.component import getMultiAdapter

        payload = getMultiAdapter(
            (self.profile, self.portal.REQUEST), ISerializeToJson
        )()

        assert not [k for k in payload if "password" in k.lower()]
        assert "hunter2!" not in str(payload)

    def test_it_is_not_catalog_metadata(self):
        from pas.plugins.identity.content.catalog import query_catalog

        brains = query_catalog().unrestrictedSearchResults(userid="alice")

        assert "hunter2!" not in str(brains[0].__record_schema__)


class TestCopyingAProfile:
    @pytest.fixture(autouse=True)
    def _setup(self, enabled, make_profile) -> None:
        self.portal = enabled
        self.profile = make_profile("alice", email="alice@example.com")
        ICredentialStorage(self.profile).set_password("hunter2!")

    def test_the_copy_carries_no_password(self):
        """Copy and paste is a normal thing to do to content. Doing it to a
        user must not hand the copy somebody else's credential."""
        container = self.profile.__parent__
        with api.env.adopt_roles(["Manager"]):
            copied = api.content.copy(
                source=self.profile, target=container, id="bob", safe_id=False
            )

        assert ICredentialStorage(copied).check_password("hunter2!") is False

    def test_the_original_keeps_its_own(self):
        container = self.profile.__parent__
        with api.env.adopt_roles(["Manager"]):
            api.content.copy(
                source=self.profile, target=container, id="bob", safe_id=False
            )

        assert ICredentialStorage(self.profile).check_password("hunter2!") is True


class TestSigningIn:
    """Core authenticates against it. The layer never does.

    Which plugin authenticates a userid is what ``@users`` reports as its
    source, so an optional property store must not change a site's answer to
    "where did this account come from".
    """

    @pytest.fixture(autouse=True)
    def _setup(self, enabled, make_profile) -> None:
        self.portal = enabled
        self.profile = make_profile("alice", email="alice@example.com", login="alice")
        ICredentialStorage(self.profile).set_password("hunter2!")

    def signin(self, login: str, password: str):
        """Authenticate the way PAS does.

        :param login: Login name.
        :param password: Password.
        :returns: Whatever PAS resolved to.
        """
        return self.portal.acl_users.authenticate(login, password, self.portal.REQUEST)

    def test_the_password_signs_the_user_in(self):
        assert self.signin("alice", "hunter2!")

    def test_a_wrong_password_does_not(self):
        assert not self.signin("alice", "nope")

    def test_an_unknown_login_does_not(self):
        assert not self.signin("nobody", "hunter2!")

    def test_a_deactivated_profile_cannot_sign_in(self):
        """The thing source_users cannot do: workflow as account suspension,
        without deleting anything and without touching a password."""
        with api.env.adopt_roles(["Manager"]):
            api.content.transition(obj=self.profile, to_state="deactivated")

        assert not self.signin("alice", "hunter2!")

    def test_reactivating_restores_it(self):
        """Suspension, not deletion."""
        with api.env.adopt_roles(["Manager"]):
            api.content.transition(obj=self.profile, to_state="deactivated")
            api.content.transition(obj=self.profile, to_state="complete")

        assert self.signin("alice", "hunter2!")
