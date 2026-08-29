"""The required-information flow reaches a user who did not arrive federated.

Everything that mints a Profile or reconciles one used to hang off
``ExternalIdentityAuthenticated``, and only a federated sign-in fires that. So
a ``source_users`` account -- the site administrator's own login, anybody
created through ``@users`` before the layer was installed, anybody added in the
ZMI -- was never minted a Profile, was never reconciled, and therefore had
nothing for the gate to hold them for.

That made ``enforce_required_profile_fields`` a rule about where a user came
from rather than about what the site requires of them, which is not what it
says and not what it is for (Érico, 2026-08-28).
"""

from pas.plugins.identity.core.completeness import COMPLETE
from pas.plugins.identity.core.completeness import INCOMPLETE
from pas.plugins.identity.core.completeness import REQUIRED_FIELDS_RECORD
from pas.plugins.identity.core.subscribers import get_profile
from plone import api
from Products.PlonePAS.events import UserLoggedInEvent
from zope.event import notify

import pytest


def log_in(acl_users, userid: str) -> None:
    """Fire the event PAS fires when somebody logs in.

    :param acl_users: The site's PAS instance.
    :param userid: The user logging in.
    """
    notify(UserLoggedInEvent(acl_users.getUserById(userid)))


class TestALocalUserGetsAProfile:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users) -> None:
        self.portal = portal
        self.acl_users = acl_users
        acl_users.source_users.addUser("bob", "bob@example.com", "placeholder")

    def test_no_profile_before_logging_in(self):
        """The precondition, so the test below cannot pass vacuously."""
        assert get_profile("bob") is None

    def test_logging_in_mints_one(self):
        log_in(self.acl_users, "bob")

        assert get_profile("bob") is not None

    def test_it_records_the_login_name(self):
        log_in(self.acl_users, "bob")

        assert get_profile("bob").login == "bob@example.com"

    def test_logging_in_again_does_not_mint_a_second(self):
        log_in(self.acl_users, "bob")
        first = get_profile("bob")
        log_in(self.acl_users, "bob")

        assert get_profile("bob").UID() == first.UID()

    def test_the_zope_root_user_is_skipped(self):
        """It is not a member of this site, and filing the emergency account
        among the site's users would put it in every listing."""
        root = self.portal.getPhysicalRoot().acl_users.getUserById("admin")
        if root is None:  # pragma: no cover - depends on the test fixture
            pytest.skip("no Zope root user in this fixture")

        notify(UserLoggedInEvent(root))

        assert get_profile("admin") is None


class TestWhatTheProfileIsSeededWith:
    """A user the site has known for years is not asked to retype it."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users) -> None:
        self.portal = portal
        self.acl_users = acl_users
        acl_users.source_users.addUser("bob", "bob@example.com", "placeholder")
        api.user.get(userid="bob").setMemberProperties({
            "fullname": "Bob Example",
            "email": "bob@example.com",
            "location": "Lisbon",
        })

    def test_the_fullname_is_carried_over(self):
        log_in(self.acl_users, "bob")

        assert get_profile("bob").fullname == "Bob Example"

    def test_the_address_is_carried_over(self):
        log_in(self.acl_users, "bob")

        assert get_profile("bob").email == "bob@example.com"

    def test_the_other_fields_are_carried_over_too(self):
        log_in(self.acl_users, "bob")

        assert get_profile("bob").location == "Lisbon"


class TestReconciliationRuns:
    """The half that decides whether the gate holds them."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users) -> None:
        self.portal = portal
        self.acl_users = acl_users
        acl_users.source_users.addUser("bob", "bob@example.com", "placeholder")

    def test_a_seeded_profile_comes_out_complete(self):
        """Everything the site requires was already known, so the user is not
        held for information Plone had all along."""
        api.portal.set_registry_record(REQUIRED_FIELDS_RECORD, ("fullname",))
        api.user.get(userid="bob").setMemberProperties({"fullname": "Bob Example"})

        log_in(self.acl_users, "bob")

        assert api.content.get_state(get_profile("bob")) == COMPLETE

    def test_a_profile_missing_a_required_field_is_incomplete(self):
        """Which is what the gate reads."""
        api.portal.set_registry_record(REQUIRED_FIELDS_RECORD, ("location",))

        log_in(self.acl_users, "bob")

        assert api.content.get_state(get_profile("bob")) == INCOMPLETE

    def test_an_existing_profile_is_reconciled_on_login(self):
        """Not only minted ones: a profile whose required fields changed while
        the user was away is re-examined when they come back."""
        log_in(self.acl_users, "bob")
        profile = get_profile("bob")
        api.portal.set_registry_record(REQUIRED_FIELDS_RECORD, ("location",))
        api.content.transition(profile, to_state=COMPLETE)

        log_in(self.acl_users, "bob")

        assert api.content.get_state(profile) == INCOMPLETE
