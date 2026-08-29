"""Every address a provider reports lands on the Profile, and stays put.

This module replaces ``test_email_choice_login.py``, which held the opposite
behaviour in place: a provider offering several addresses picked none of them,
the Profile was minted without one, and the required-information gate held its
owner on a form until they chose. The list was the answer to a Profile that
had one address slot; it has a list now, so all of them go on and nothing is
withheld (Érico, 2026-08-29).

What the tests here are actually guarding is the *second* login. Filling a
fresh Profile is easy to get right; leaving an arranged one alone is where a
sync silently undoes somebody's editing.
"""

from . import DEX_IDENTITY
from pas.plugins.identity.core.pas import EXTRACTOR
from pas.plugins.identity.core.subscribers import get_profile
from plone import api

import pytest


PROVIDER, SUBJECT = DEX_IDENTITY

#: Three addresses, ordered as a driver orders them: primary first, then the
#: verified one, then the rest.
REPORTED = (
    {"address": "me@example.com", "verified": True, "primary": True},
    {"address": "work@example.com", "verified": True, "primary": False},
    {"address": "old@example.com", "verified": False, "primary": False},
)

CLAIMS = {
    "fullname": "Alice Liddell",
    "email": "me@example.com",
    "email_verified": True,
    "username": "alice",
    "raw": {},
    "emails": REPORTED,
}


class TestEveryAddressLands:
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

    def test_all_three_are_on_the_profile(self):
        """In the provider's order, which is the order they were offered."""
        userid = self.authenticate(dict(CLAIMS))

        assert get_profile(userid).emails == (
            "me@example.com",
            "work@example.com",
            "old@example.com",
        )

    def test_the_account_has_an_address(self):
        """The head of the list, so nothing is left waiting on a choice."""
        userid = self.authenticate(dict(CLAIMS))

        assert api.user.get(userid=userid).getProperty("email") == "me@example.com"

    def test_a_provider_sending_one_address_still_works(self):
        """Every provider but GitHub, and a driver older than ``emails``."""
        claims = {k: v for k, v in CLAIMS.items() if k != "emails"}
        userid = self.authenticate({**claims, "email": "plain@example.com"})

        assert get_profile(userid).emails == ("plain@example.com",)

    def test_a_second_login_changes_nothing(self):
        """The same addresses reported again are the same addresses."""
        userid = self.authenticate(dict(CLAIMS))
        self.authenticate(dict(CLAIMS))

        assert get_profile(userid).emails == (
            "me@example.com",
            "work@example.com",
            "old@example.com",
        )

    def test_a_new_address_is_appended(self):
        """At the end. The order above it is somebody's answer."""
        userid = self.authenticate(dict(CLAIMS))
        self.authenticate({
            **CLAIMS,
            "email": "new@example.com",
            "emails": (
                {"address": "new@example.com", "verified": True, "primary": True},
                *REPORTED[1:],
            ),
        })

        assert get_profile(userid).emails == (
            "me@example.com",
            "work@example.com",
            "old@example.com",
            "new@example.com",
        )

    def test_an_order_the_user_chose_survives_a_login(self):
        """Which is what picking a preferred address amounts to."""
        userid = self.authenticate(dict(CLAIMS))
        profile = get_profile(userid)
        profile.emails = ("old@example.com", "me@example.com", "work@example.com")

        self.authenticate(dict(CLAIMS))

        assert get_profile(userid).emails[0] == "old@example.com"

    def test_an_address_the_user_deleted_stays_deleted(self):
        """The provider offered it once. Offering it again is not new news."""
        userid = self.authenticate(dict(CLAIMS))
        profile = get_profile(userid)
        profile.emails = ("me@example.com", "work@example.com")

        self.authenticate(dict(CLAIMS))

        assert "old@example.com" not in get_profile(userid).emails
