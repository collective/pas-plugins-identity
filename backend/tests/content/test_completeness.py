"""Whether a profile carries what the site requires, and the state that says so.

The workflow state is the answer rather than a second store, so every test
here is ultimately about one thing: does `review_state` describe the profile
as it is now. It has to be true after a login from a generous provider, after
a login from a stingy one, after the user fills the form in, and after
somebody clears a field again.

Before this existed nothing ever fired `complete`, so every profile stayed
`incomplete` for ever and the frontend diverted every user on every login. A
test that only checks "a fresh profile is incomplete" passes just as well in
that world, which is why the tests below are all about transitions rather than
about initial state.
"""

from . import PROFILE_ID
from pas.plugins.identity.content import completeness
from pas.plugins.identity.content.completeness import is_complete
from pas.plugins.identity.content.completeness import missing_fields
from pas.plugins.identity.content.completeness import reconcile
from pas.plugins.identity.content.completeness import required_fields
from pas.plugins.identity.content.completeness import REQUIRED_FIELDS_RECORD
from plone import api
from zope.lifecycleevent import modified

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


def state(profile) -> str:
    """Return a profile's workflow state.

    :param profile: The profile.
    :returns: The review state.
    """
    return api.content.get_state(obj=profile)


class TestWhatIsRequired:
    """The registry record, and what it falls back to."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_profile) -> None:
        self.portal = portal
        self.profile = make_profile("alice", email="alice@example.com")

    def test_it_defaults_to_what_the_type_requires(self):
        """Read off the object, so a site with its own user type or an extra
        behavior gets the answer for the type it actually has."""
        assert set(required_fields(self.profile)) == {"login", "email"}

    def test_the_registry_record_wins(self):
        api.portal.set_registry_record(REQUIRED_FIELDS_RECORD, ("email", "location"))

        assert required_fields(self.profile) == ("email", "location")

    def test_an_empty_record_falls_back(self):
        """Empty means "ask the type", not "require nothing"."""
        api.portal.set_registry_record(REQUIRED_FIELDS_RECORD, ())

        assert set(required_fields(self.profile)) == {"login", "email"}

    def test_the_userid_is_never_required(self):
        """It is the object's own id. Asking a user for it would be asking
        them to name the form they are filling in."""
        api.portal.set_registry_record(REQUIRED_FIELDS_RECORD, ())

        assert "userid" not in required_fields(self.profile)


class TestWhatIsMissing:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_profile) -> None:
        self.portal = portal
        self.profile = make_profile("alice", email="alice@example.com")

    def test_a_filled_profile_is_missing_nothing(self):
        assert missing_fields(self.profile) == ()
        assert is_complete(self.profile) is True

    def test_an_empty_required_field_is_missing(self):
        self.profile.email = ""

        assert missing_fields(self.profile) == ("email",)
        assert is_complete(self.profile) is False

    def test_an_absent_attribute_is_missing(self):
        """A field the object has never been given a value for."""
        api.portal.set_registry_record(REQUIRED_FIELDS_RECORD, ("location",))

        assert missing_fields(self.profile) == ("location",)

    def test_whitespace_does_not_count_as_filled(self):
        """Otherwise a space bar satisfies the requirement."""
        self.profile.email = "   "

        assert missing_fields(self.profile) == ("email",)

    def test_an_empty_collection_is_missing(self):
        api.portal.set_registry_record(REQUIRED_FIELDS_RECORD, ("group_ids",))

        assert missing_fields(self.profile) == ("group_ids",)

    def test_a_falsy_value_that_is_a_value_is_not_missing(self):
        """``0`` and ``False`` are answers somebody gave.

        No shipped field holds one, which is exactly why this is worth
        pinning: the day a site adds a required numeric field, a truthiness
        test would call zero missing and never say why.
        """
        assert completeness._is_empty(0) is False
        assert completeness._is_empty(False) is False


class TestReconcile:
    """Bringing the state in line with the profile."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_profile) -> None:
        self.portal = portal
        self.profile = make_profile("alice", email="alice@example.com")

    def test_a_complete_profile_is_completed(self):
        api.content.transition(obj=self.profile, transition="reopen")

        assert reconcile(self.profile) == "complete"
        assert state(self.profile) == "complete"

    def test_an_incomplete_profile_is_reopened(self):
        """A site that adds a requirement reaches everybody who already
        exists, which is the only thing that makes adding one meaningful."""
        assert state(self.profile) == "complete"
        api.portal.set_registry_record(REQUIRED_FIELDS_RECORD, ("location",))

        assert reconcile(self.profile) == "reopen"
        assert state(self.profile) == "incomplete"

    def test_a_state_that_is_already_right_is_left_alone(self):
        """No transition means no reindex and no workflow history entry, on
        every write to every profile."""
        assert reconcile(self.profile) is None

    def test_a_deactivated_profile_is_never_touched(self):
        """Deactivation is an administrator's decision about an account, and
        "nothing is missing" is not an argument against it."""
        api.content.transition(obj=self.profile, transition="deactivate")

        assert reconcile(self.profile) is None
        assert state(self.profile) == "deactivated"

    def test_a_deactivated_profile_missing_a_field_is_also_left_alone(self):
        api.content.transition(obj=self.profile, transition="deactivate")
        self.profile.email = ""

        assert reconcile(self.profile) is None
        assert state(self.profile) == "deactivated"

    def test_it_does_not_need_the_caller_to_hold_anything(self):
        """The transitions are guarded by ``Modify portal content``, and the
        callers are a login subscriber and a write subscriber -- neither of
        which is reliably running as anybody in particular."""
        api.content.transition(obj=self.profile, transition="reopen")

        with api.env.adopt_roles(["Anonymous"]):
            assert reconcile(self.profile) == "complete"


class TestWritingToAProfileReconcilesIt:
    """The half that keeps a user out of a loop.

    Without it somebody who has just filled the form in stays ``incomplete``
    until their next sign-in, and is sent straight back to the form they have
    already completed.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_profile) -> None:
        self.portal = portal
        api.portal.set_registry_record(REQUIRED_FIELDS_RECORD, ("email", "location"))
        self.profile = make_profile("alice", email="alice@example.com")

    def test_it_starts_incomplete(self):
        """``location`` is required here and the profile has none."""
        assert state(self.profile) == "incomplete"

    def test_filling_the_last_field_in_completes_it(self):
        self.profile.location = "Oxford"
        modified(self.profile)

        assert state(self.profile) == "complete"

    def test_clearing_a_required_field_reopens_it(self):
        self.profile.location = "Oxford"
        modified(self.profile)

        self.profile.location = ""
        modified(self.profile)

        assert state(self.profile) == "incomplete"

    def test_a_group_is_not_put_through_any_of_this(self):
        """The subscriber is bound to the Profile marker, not the catalog one.

        A group has no ``complete`` transition, so firing one would be an
        error rather than a no-op.
        """
        group = api.content.create(
            container=self.portal["identity-profiles"],
            type="UserGroup",
            id="editors",
            group_id="editors",
            title="Editors",
        )

        modified(group)

        assert api.content.get_state(obj=group) == "active"
