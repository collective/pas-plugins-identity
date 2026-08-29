"""An offered address list survives the login that carried it.

A driver offered several addresses picks none of them and carries the list, so
the user can say which is theirs on their profile. Nothing in the login path
may quietly settle it: the choice decides which identity the person is here
as, and -- where the operator enabled auto-linking -- which existing account a
verified-email link would attach to.

There used to be a second half to this module, for a site with no profiles to
ask on: it took the first offer rather than leaving the account with no
address at all. Found by Érico installing the backend without the content
extra (2026-08-28), and gone with the extra itself -- every site has profiles
now, so every site can ask.
"""

from . import DEX_IDENTITY
from pas.plugins.identity.core.emailchoices import offered_addresses
from pas.plugins.identity.core.pas import EXTRACTOR
from plone import api

import pytest


PROVIDER, SUBJECT = DEX_IDENTITY

#: Two addresses and no answer, ordered as the driver ordered them.
OFFERED = (
    {"address": "me@example.com", "verified": True, "primary": True},
    {"address": "old@example.com", "verified": False, "primary": False},
)

CLAIMS_WITH_CHOICES = {
    "fullname": "Alice Liddell",
    "email": "",
    "email_verified": False,
    "username": "alice",
    "raw": {},
    "email_choices": OFFERED,
}


class TestTheChoiceIsLeftOpen:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin) -> None:
        self.portal = portal
        self.plugin = plugin

    def authenticate(self, claims) -> str:
        """Run a login and return the userid it resolved to.

        :param claims: Claims to authenticate with.
        :returns: The Plone userid.
        """
        userid, _ = self.plugin.authenticateCredentials({
            "extractor": EXTRACTOR,
            "provider": PROVIDER,
            "subject": SUBJECT,
            "claims": claims,
        })
        return userid

    def test_no_address_is_chosen(self):
        """The account is left without one, on purpose: the profile is
        ``incomplete`` and the gate holds its owner on the form that asks."""
        userid = self.authenticate(dict(CLAIMS_WITH_CHOICES))

        assert not api.user.get(userid=userid).getProperty("email")

    def test_the_offers_reach_the_form(self):
        """Both of them, so the form renders a choice rather than a box."""
        userid = self.authenticate(dict(CLAIMS_WITH_CHOICES))

        addresses = [offer["address"] for offer in offered_addresses(userid)]
        assert addresses == ["me@example.com", "old@example.com"]

    def test_an_address_the_driver_sent_is_used(self):
        """One address is an answer, and the driver already used it."""
        userid = self.authenticate({
            **CLAIMS_WITH_CHOICES,
            "email": "sent@example.com",
        })

        assert api.user.get(userid=userid).getProperty("email") == "sent@example.com"

    def test_a_login_with_no_choices_is_untouched(self):
        """Every provider but GitHub."""
        claims = {k: v for k, v in CLAIMS_WITH_CHOICES.items() if k != "email_choices"}
        userid = self.authenticate({**claims, "email": "plain@example.com"})

        assert api.user.get(userid=userid).getProperty("email") == "plain@example.com"
