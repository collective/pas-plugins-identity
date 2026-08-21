"""Unit tests for the event contract (§4.3).

These classes are the package's public API: subscribers outside this codebase
bind to the interfaces and read the attributes, so the shape is tested here
rather than left to whichever caller happens to fire an event.
"""

from pas.plugins.identity.core.events import EmailVerified
from pas.plugins.identity.core.events import ExternalIdentityAuthenticated
from pas.plugins.identity.core.events import IdentityLinked
from pas.plugins.identity.core.events import IdentityUnlinked
from pas.plugins.identity.core.events import IEmailVerified
from pas.plugins.identity.core.events import IExternalIdentityAuthenticated
from pas.plugins.identity.core.events import IIdentityEvent
from pas.plugins.identity.core.events import IIdentityLinked
from pas.plugins.identity.core.events import IIdentityUnlinked
from pas.plugins.identity.core.events import IUserClaimsRefreshed
from pas.plugins.identity.core.events import UserClaimsRefreshed
from zope.interface.verify import verifyObject

import pytest


#: Normalized claims, as every event carries them.
CLAIMS = {
    "sub": "CgVlcmljbxIFbG9jYWw",
    "email": "erico@plone.org",
    "email_verified": True,
    "fullname": "Érico Andrei",
}


@pytest.fixture()
def authenticated() -> ExternalIdentityAuthenticated:
    """Return an authentication event for a first-time login."""
    return ExternalIdentityAuthenticated(
        userid="userid-1",
        provider="dex",
        subject="CgVlcmljbxIFbG9jYWw",
        claims=CLAIMS,
        is_new_user=True,
        is_new_identity=True,
    )


class TestEventContract:
    """Every event is an :class:`IIdentityEvent` and satisfies its own
    interface -- that is what a subscriber is allowed to rely on."""

    @pytest.mark.parametrize(
        "event,interface",
        [
            (
                ExternalIdentityAuthenticated(
                    "userid-1", "dex", "subject-1", CLAIMS, True, True
                ),
                IExternalIdentityAuthenticated,
            ),
            (
                IdentityLinked("userid-1", "github", "1234567", CLAIMS),
                IIdentityLinked,
            ),
            (
                IdentityUnlinked("userid-1", "github", "1234567"),
                IIdentityUnlinked,
            ),
            (
                EmailVerified("userid-1", "erico@plone.org"),
                IEmailVerified,
            ),
            (
                UserClaimsRefreshed("userid-1", "dex", CLAIMS),
                IUserClaimsRefreshed,
            ),
        ],
    )
    def test_provides_its_interface(self, event, interface):
        """The declared interface is actually satisfied."""
        assert verifyObject(interface, event)

    @pytest.mark.parametrize(
        "interface",
        [
            IExternalIdentityAuthenticated,
            IIdentityLinked,
            IIdentityUnlinked,
            IEmailVerified,
            IUserClaimsRefreshed,
        ],
    )
    def test_extends_the_base(self, interface):
        """A subscriber for ``IIdentityEvent`` sees every event."""
        assert interface.extends(IIdentityEvent)


class TestExternalIdentityAuthenticated:
    def test_carries_the_identity(self, authenticated):
        """Provider and subject together name the external identity."""
        assert authenticated.userid == "userid-1"
        assert authenticated.provider == "dex"
        assert authenticated.subject == "CgVlcmljbxIFbG9jYWw"

    def test_carries_claims(self, authenticated):
        """Claims travel with the event, unmodified."""
        assert authenticated.claims == CLAIMS

    def test_flags_a_first_login(self, authenticated):
        """A minted userid and a fresh identity are reported separately."""
        assert authenticated.is_new_user is True
        assert authenticated.is_new_identity is True

    def test_repeat_login_is_neither_new(self):
        """The same human logging in again is new in no sense (Gate 1)."""
        event = ExternalIdentityAuthenticated(
            "userid-1", "dex", "subject-1", CLAIMS, False, False
        )

        assert event.is_new_user is False
        assert event.is_new_identity is False


class TestIdentityLinked:
    def test_carries_provider_and_subject(self):
        """Linking names the identity that was attached."""
        event = IdentityLinked("userid-1", "github", "1234567", CLAIMS)

        assert event.userid == "userid-1"
        assert event.provider == "github"
        assert event.subject == "1234567"
        assert event.claims == CLAIMS


class TestIdentityUnlinked:
    def test_carries_no_claims(self):
        """Unlinking is a removal; there are no fresh claims to report."""
        event = IdentityUnlinked("userid-1", "github", "1234567")

        assert event.userid == "userid-1"
        assert event.provider == "github"
        assert event.subject == "1234567"
        assert not hasattr(event, "claims")


class TestEmailVerified:
    def test_carries_the_address(self):
        """The address is what makes the event useful."""
        event = EmailVerified("userid-1", "erico@plone.org")

        assert event.userid == "userid-1"
        assert event.address == "erico@plone.org"

    def test_address_is_lowercased(self):
        """Email subjects are lowercased everywhere, events included, so a
        subscriber can compare against the store without normalizing."""
        assert EmailVerified("userid-1", "Erico@Plone.ORG").address == (
            "erico@plone.org"
        )


class TestUserClaimsRefreshed:
    def test_carries_the_fresh_claims(self):
        """D2 refresh hands subscribers the new claims, not a diff."""
        event = UserClaimsRefreshed("userid-1", "dex", CLAIMS)

        assert event.userid == "userid-1"
        assert event.provider == "dex"
        assert event.claims == CLAIMS

    def test_carries_no_subject(self):
        """A refresh is about the user, not about one identity record."""
        assert not hasattr(UserClaimsRefreshed("userid-1", "dex", CLAIMS), "subject")
