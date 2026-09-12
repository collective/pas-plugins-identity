"""A first sign-in is what asks which verified address stands for a person.

Driven through ``authenticateCredentials``, the login path, because the
question here is which sign-ins reach the confirmation at all: a first one
with more than one verified address, while the site asks -- and no other.
"""

from . import DEX_IDENTITY
from pas.plugins.identity.core.confirmation import CONFIRM_RECORD
from pas.plugins.identity.core.confirmation import confirmation_pending
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.events import IdentityLinked
from pas.plugins.identity.core.pas import EXTRACTOR
from pas.plugins.identity.core.profiles import get_profile
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from plone import api
from zope.event import notify

import pytest


PROVIDER, SUBJECT = DEX_IDENTITY
FIRST = "ghost@plone.org"
SECOND = "ghost@gmail.com"


def entry(address: str, verified: bool = True) -> dict:
    """Build one address as a driver reports it.

    :param address: The address.
    :param verified: Whether the provider verified it.
    :returns: The address entry.
    """
    return {"address": address, "verified": verified, "primary": False}


def claims(*emails: dict) -> dict:
    """Build the claims of a sign-in reporting these addresses, in order.

    :param emails: The address entries.
    :returns: The claims.
    """
    head = emails[0]
    return {
        "fullname": "Ghost",
        "username": "ghost",
        "email": head["address"],
        "email_verified": head["verified"],
        "emails": tuple(emails),
        "raw": {},
    }


class TestAFirstSignIn:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin) -> None:
        self.portal = portal
        self.plugin = plugin
        api.portal.set_registry_record(CONFIRM_RECORD, True)
        self.configure()

    def configure(self, trust: bool = True) -> None:
        """Configure the provider.

        :param trust: Whether the site trusts its address verification.
        """
        set_providers([
            ProviderConfig(
                provider_id=PROVIDER,
                driver_id="oidc-generic",
                title="Dex",
                config={"trust_email_verification": trust},
            )
        ])

    def authenticate(self, *emails: dict):
        """Sign in with the identity reporting these addresses.

        :param emails: The address entries.
        :returns: The Profile signed in to.
        """
        userid, _ = self.plugin.authenticateCredentials({
            "extractor": EXTRACTOR,
            "provider": PROVIDER,
            "subject": SUBJECT,
            "claims": claims(*emails),
        })
        return get_profile(userid)

    def test_two_verified_addresses_are_asked_about(self):
        profile = self.authenticate(entry(FIRST), entry(SECOND))

        assert confirmation_pending(profile) is True
        assert api.content.get_state(obj=profile) == "incomplete"

    def test_one_verified_address_is_not(self):
        profile = self.authenticate(entry(FIRST), entry(SECOND, verified=False))

        assert confirmation_pending(profile) is False
        assert api.content.get_state(obj=profile) == "complete"

    def test_proving_a_second_address_later_does_not_ask(self):
        """Only a first sign-in that brought a choice is asked. Somebody who
        proves a second address afterwards was never asked, and is not now."""
        profile = self.authenticate(entry(FIRST), entry(SECOND, verified=False))

        self.plugin.link(profile.userid, EMAIL_PROVIDER, SECOND, {})

        assert confirmation_pending(profile) is False

    def test_a_provider_the_site_does_not_trust_asks_nothing(self):
        """Its word does not make an address verified here, so there is
        nothing verified to choose between."""
        self.configure(trust=False)

        profile = self.authenticate(entry(FIRST), entry(SECOND))

        assert confirmation_pending(profile) is False

    def test_a_site_that_does_not_ask_asks_nothing(self):
        api.portal.set_registry_record(CONFIRM_RECORD, False)

        profile = self.authenticate(entry(FIRST), entry(SECOND))

        assert confirmation_pending(profile) is False

    def test_a_later_sign_in_is_not_a_first_one(self):
        """Only first sign-ins made while the switch is on: turning it on
        does not hold everybody who already has a Profile."""
        api.portal.set_registry_record(CONFIRM_RECORD, False)
        self.authenticate(entry(FIRST), entry(SECOND))
        api.portal.set_registry_record(CONFIRM_RECORD, True)

        profile = self.authenticate(entry(FIRST), entry(SECOND))

        assert confirmation_pending(profile) is False

    def test_a_later_sign_in_does_not_answer(self):
        """Nothing but the answer releases a held Profile."""
        self.authenticate(entry(FIRST), entry(SECOND))

        profile = self.authenticate(entry(SECOND), entry(FIRST))

        assert confirmation_pending(profile) is True

    def test_linking_a_provider_is_not_a_sign_in(self):
        """Even when it is what mints the Profile."""
        notify(
            IdentityLinked(
                userid="erin",
                provider=PROVIDER,
                subject="erin-subject",
                claims=claims(entry(FIRST), entry(SECOND)),
            )
        )

        assert confirmation_pending(get_profile("erin")) is False
