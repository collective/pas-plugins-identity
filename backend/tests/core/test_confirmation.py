"""Asking a person with several verified addresses which one stands for them.

Driven against a Profile directly. Which sign-ins set the marker is a question
about the login path, and is driven through it in
``pas/test_confirm_at_first_sign_in.py``.
"""

from pas.plugins.identity.core.catalog import query_catalog
from pas.plugins.identity.core.completeness import is_complete
from pas.plugins.identity.core.completeness import REQUIRED_FIELDS_RECORD
from pas.plugins.identity.core.confirmation import ask_if_needed
from pas.plugins.identity.core.confirmation import confirm
from pas.plugins.identity.core.confirmation import CONFIRM_RECORD
from pas.plugins.identity.core.confirmation import confirmation_pending
from pas.plugins.identity.core.confirmation import confirmation_pending_on_brain
from pas.plugins.identity.core.confirmation import NotAVerifiedAddress
from pas.plugins.identity.core.confirmation import NothingToConfirm
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from pas.plugins.identity.core.subscribers.gate import incomplete_profile_url
from plone import api
from zope.lifecycleevent import modified

import pytest


USERID = "alice"
FIRST = "alice@example.com"
SECOND = "alice@example.org"
UNVERIFIED = "alice@example.net"


def state(profile) -> str:
    """Return a profile's workflow state.

    :param profile: The profile.
    :returns: The review state.
    """
    return api.content.get_state(obj=profile)


class ConfirmationCase:
    """A complete Profile holding two verified addresses and one unverified."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin, make_profile) -> None:
        self.portal = portal
        self.plugin = plugin
        api.portal.set_registry_record(CONFIRM_RECORD, True)
        self.profile = make_profile(USERID, fullname="Alice Liddell")
        self.verify(FIRST, SECOND)
        self.profile.emails = (FIRST, SECOND, UNVERIFIED)
        modified(self.profile)

    def verify(self, *addresses: str) -> None:
        """Record addresses as verified for the Profile's owner.

        :param addresses: The addresses.
        """
        for address in addresses:
            self.plugin.store.add(EMAIL_PROVIDER, address, USERID, {})

    def brain(self):
        """Return the Profile's brain.

        :returns: The brain.
        """
        return query_catalog().unrestrictedSearchResults(userid=USERID)[0]


def test_it_is_off_by_default(portal):
    """Holding somebody on a page to repeat what the address order already
    says is a site's choice to make."""
    assert api.portal.get_registry_record(CONFIRM_RECORD) is False


class TestTheSwitch(ConfirmationCase):
    def test_off_asks_nobody(self):
        api.portal.set_registry_record(CONFIRM_RECORD, False)

        assert ask_if_needed(self.profile) is False
        assert confirmation_pending(self.profile) is False

    def test_turning_it_off_releases_a_held_profile(self):
        """At the next write, exactly as a change to the required fields
        does, rather than leaving somebody held by a setting that is off."""
        ask_if_needed(self.profile)
        api.portal.set_registry_record(CONFIRM_RECORD, False)

        modified(self.profile)

        assert state(self.profile) == "complete"


class TestWhoIsAsked(ConfirmationCase):
    def test_two_verified_addresses_are_a_question(self):
        assert ask_if_needed(self.profile) is True
        assert confirmation_pending(self.profile) is True

    def test_the_profile_is_held(self):
        ask_if_needed(self.profile)

        assert state(self.profile) == "incomplete"

    def test_one_verified_address_is_not(self):
        """There is nothing to choose between."""
        self.plugin.store.remove(EMAIL_PROVIDER, SECOND)

        assert ask_if_needed(self.profile) is False
        assert state(self.profile) == "complete"

    def test_an_unverified_address_does_not_count(self):
        """Only addresses this site holds verified: one a provider reports but
        this site does not trust is not something to choose between."""
        self.plugin.store.remove(EMAIL_PROVIDER, SECOND)
        self.profile.emails = (FIRST, UNVERIFIED, SECOND)

        assert ask_if_needed(self.profile) is False

    def test_the_marker_reaches_the_catalog(self):
        """Where the gate and ``@my-profile`` read it."""
        ask_if_needed(self.profile)

        assert confirmation_pending_on_brain(self.brain()) is True

    def test_a_brain_answers_like_the_object_when_off(self):
        ask_if_needed(self.profile)
        api.portal.set_registry_record(CONFIRM_RECORD, False)

        assert confirmation_pending_on_brain(self.brain()) is False


class TestNothingButTheAnswerReleases(ConfirmationCase):
    @pytest.fixture(autouse=True)
    def _asked(self, _setup) -> None:
        ask_if_needed(self.profile)

    def test_it_is_not_complete(self):
        assert is_complete(self.profile) is False

    def test_saving_another_field_does_not(self):
        """A save made to fill something else in has not answered."""
        self.profile.location = "Oxford"
        modified(self.profile)

        assert state(self.profile) == "incomplete"
        assert confirmation_pending(self.profile) is True

    def test_reordering_the_addresses_does_not(self):
        """A login's own address sync writes this list too, so a changed
        order is not evidence anybody was asked."""
        self.profile.emails = (SECOND, FIRST, UNVERIFIED)
        modified(self.profile)

        assert state(self.profile) == "incomplete"


class TestTheAnswer(ConfirmationCase):
    @pytest.fixture(autouse=True)
    def _asked(self, _setup) -> None:
        ask_if_needed(self.profile)

    def test_the_address_moves_to_the_front(self):
        confirm(self.profile, SECOND)

        assert self.profile.emails == (SECOND, FIRST, UNVERIFIED)

    def test_it_becomes_the_email(self):
        confirm(self.profile, SECOND)

        assert self.profile.email == SECOND

    def test_the_profile_is_released(self):
        confirm(self.profile, SECOND)

        assert confirmation_pending(self.profile) is False
        assert state(self.profile) == "complete"

    def test_the_first_address_is_an_answer_too(self):
        """The order was right; somebody has now said so."""
        confirm(self.profile, FIRST)

        assert self.profile.emails == (FIRST, SECOND, UNVERIFIED)
        assert state(self.profile) == "complete"

    def test_the_address_is_normalized(self):
        assert confirm(self.profile, f"  {SECOND.upper()} ") == SECOND
        assert self.profile.emails[0] == SECOND

    def test_an_unverified_address_is_refused(self):
        """It would not become ``email`` even at the front of the list."""
        with pytest.raises(NotAVerifiedAddress):
            confirm(self.profile, UNVERIFIED)

        assert self.profile.emails == (FIRST, SECOND, UNVERIFIED)
        assert state(self.profile) == "incomplete"

    def test_somebody_elses_address_is_refused(self):
        """Verified, but not for this person."""
        self.plugin.store.add(EMAIL_PROVIDER, "bob@example.com", "bob", {})

        with pytest.raises(NotAVerifiedAddress):
            confirm(self.profile, "bob@example.com")

    def test_an_empty_address_is_refused(self):
        with pytest.raises(NotAVerifiedAddress):
            confirm(self.profile, " ")


class TestNothingToConfirm(ConfirmationCase):
    def test_a_profile_nobody_asked(self):
        """Not a second way to reorder addresses."""
        with pytest.raises(NothingToConfirm):
            confirm(self.profile, SECOND)

        assert self.profile.emails == (FIRST, SECOND, UNVERIFIED)

    def test_a_site_that_stopped_asking(self):
        ask_if_needed(self.profile)
        api.portal.set_registry_record(CONFIRM_RECORD, False)

        with pytest.raises(NothingToConfirm):
            confirm(self.profile, SECOND)


class TestOnlyWhileThereIsAChoice(ConfirmationCase):
    """A Profile left with one verified address has nothing to choose between.

    Holding it would send its owner to a question with nothing to answer it
    with, and the page that asks has no way to release them.
    """

    @pytest.fixture(autouse=True)
    def _asked(self, _setup) -> None:
        ask_if_needed(self.profile)

    def test_removing_an_address_releases_it(self):
        """Straight away, rather than at the owner's next write."""
        self.plugin.unlink(USERID, EMAIL_PROVIDER, SECOND)

        assert confirmation_pending(self.profile) is False
        assert state(self.profile) == "complete"

    def test_the_brain_agrees(self):
        self.plugin.unlink(USERID, EMAIL_PROVIDER, SECOND)

        assert confirmation_pending_on_brain(self.brain()) is False

    def test_there_is_then_nothing_to_confirm(self):
        self.plugin.unlink(USERID, EMAIL_PROVIDER, SECOND)

        with pytest.raises(NothingToConfirm):
            confirm(self.profile, FIRST)


class TestTheAuthorizationEndpointAgrees(ConfirmationCase):
    """``@@oauth-authorize`` pauses at the edit form, which cannot answer."""

    def test_a_profile_waiting_only_on_an_answer_is_not_paused(self):
        ask_if_needed(self.profile)

        assert incomplete_profile_url(USERID) is None

    def test_a_missing_field_still_is(self):
        ask_if_needed(self.profile)
        api.portal.set_registry_record(REQUIRED_FIELDS_RECORD, ("location",))
        modified(self.profile)

        assert incomplete_profile_url(USERID) == f"{self.profile.absolute_url()}/edit"
