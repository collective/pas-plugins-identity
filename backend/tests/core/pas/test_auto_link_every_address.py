"""Linking by email on every address a provider verified, not only the first.

A GitHub account holds several addresses, and ``auto_link_by_email`` used to
match the headline ``email`` alone. A person whose address verified here was
not the one their provider put first got a second account instead of the one
they had. Every verified address is tried now, in the order the site prefers
(#80), and the first one that belongs to an account decides.

Driven through ``authenticateCredentials``, which is the login path: the
claims arrive already ranked, because the callback service ranks them.
"""

from . import DEX_IDENTITY
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.pas import EXTRACTOR
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from plone import api

import logging
import pytest


PROVIDER, SUBJECT = DEX_IDENTITY
PREFERRED = "ghost@plone.org"
SECOND = "ghost@gmail.com"


def entry(address: str, verified: bool = True) -> dict:
    """Build one address as a driver reports it.

    :param address: The address.
    :param verified: Whether the provider verified it.
    :returns: The address entry.
    """
    return {"address": address, "verified": verified, "primary": False}


class AutoLinkCase:
    """A provider with both linking switches on, and helpers to sign in."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin) -> None:
        self.portal = portal
        self.plugin = plugin
        self.configure()

    def configure(self, **config) -> None:
        """Configure the provider, with both linking switches on by default.

        :param config: Settings to override.
        """
        set_providers([
            ProviderConfig(
                provider_id=PROVIDER,
                driver_id="oidc-generic",
                title="Dex",
                config={
                    "auto_link_by_email": True,
                    "trust_email_verification": True,
                    **config,
                },
            )
        ])

    def account(self, username: str, *addresses: str) -> str:
        """Create an account that has verified the given addresses here.

        :param username: The account's username, which is also its userid.
        :param addresses: The addresses to record as verified for it.
        :returns: The userid.
        """
        api.user.create(
            username=username,
            email=f"{username}@example.com",
            password="a-long-enough-password",
        )
        for address in addresses:
            self.plugin.store.add(EMAIL_PROVIDER, address, username, {})
        return username

    def authenticate(self, *emails: dict) -> str:
        """Sign in with a new identity reporting these addresses, in order.

        :param emails: The address entries, already in the site's order.
        :returns: The userid signed in as.
        """
        head = emails[0]
        userid, _ = self.plugin.authenticateCredentials({
            "extractor": EXTRACTOR,
            "provider": PROVIDER,
            "subject": SUBJECT,
            "claims": {
                "fullname": "Ghost",
                "username": "ghost",
                "email": head["address"],
                "email_verified": head["verified"],
                "emails": tuple(emails),
                "raw": {},
            },
        })
        return userid


def conflicts(caplog) -> list[str]:
    """Return the conflict messages logged at ``ERROR``.

    :param caplog: pytest's log capture.
    :returns: The messages.
    """
    return [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.ERROR
        and "a different account" in record.getMessage()
    ]


class TestEveryVerifiedAddressIsTried(AutoLinkCase):
    def test_the_first_address_still_links(self):
        """The case that already worked, so the change cannot pass by
        breaking it."""
        self.account("alice", PREFERRED)

        assert self.authenticate(entry(PREFERRED), entry(SECOND)) == "alice"

    def test_a_lower_ranked_address_links(self):
        """The bug: the address this site had verified was the second one,
        and the person got a second account."""
        self.account("alice", SECOND)

        assert self.authenticate(entry(PREFERRED), entry(SECOND)) == "alice"

    def test_an_address_the_provider_did_not_verify_is_not_matched(self):
        """The provider's word is what makes the address this person's."""
        self.account("alice", SECOND)

        userid = self.authenticate(entry(PREFERRED), entry(SECOND, verified=False))

        assert userid != "alice"

    def test_nothing_is_matched_without_trusting_the_provider(self):
        """Walking the list does not loosen the switch that guards it."""
        self.configure(trust_email_verification=False)
        self.account("alice", SECOND)

        assert self.authenticate(entry(PREFERRED), entry(SECOND)) != "alice"

    def test_a_login_nothing_matches_still_works(self):
        userid = self.authenticate(entry(PREFERRED), entry(SECOND))

        assert api.user.get(userid=userid) is not None

    def test_two_addresses_of_one_account_are_not_a_conflict(self, caplog):
        self.account("alice", PREFERRED, SECOND)

        with caplog.at_level(logging.ERROR, logger="pas.plugins.identity"):
            self.authenticate(entry(PREFERRED), entry(SECOND))

        assert conflicts(caplog) == []


class TestTwoAddressesBelongToTwoAccounts(AutoLinkCase):
    @pytest.fixture(autouse=True)
    def _accounts(self, _setup) -> None:
        self.account("alice", PREFERRED)
        self.account("bob", SECOND)

    def test_the_higher_ranked_address_decides(self):
        assert self.authenticate(entry(PREFERRED), entry(SECOND)) == "alice"

    def test_it_is_the_order_that_decides(self):
        """Not the account: the same two addresses the other way round."""
        assert self.authenticate(entry(SECOND), entry(PREFERRED)) == "bob"

    def test_the_conflict_is_logged_at_error(self, caplog):
        """One person with two accounts here is a merge an operator has to
        make, and nothing else would tell them."""
        with caplog.at_level(logging.ERROR, logger="pas.plugins.identity"):
            self.authenticate(entry(PREFERRED), entry(SECOND))

        assert len(conflicts(caplog)) == 1

    def test_the_error_names_both_accounts(self, caplog):
        with caplog.at_level(logging.ERROR, logger="pas.plugins.identity"):
            self.authenticate(entry(PREFERRED), entry(SECOND))

        (message,) = conflicts(caplog)
        assert "alice" in message
        assert "bob" in message

    def test_the_error_names_both_addresses(self, caplog):
        with caplog.at_level(logging.ERROR, logger="pas.plugins.identity"):
            self.authenticate(entry(PREFERRED), entry(SECOND))

        (message,) = conflicts(caplog)
        assert PREFERRED in message
        assert SECOND in message

    def test_nothing_moves_between_the_accounts(self):
        """The other account keeps the address it verified."""
        self.authenticate(entry(PREFERRED), entry(SECOND))

        assert self.plugin.store.userid_for(EMAIL_PROVIDER, SECOND) == "bob"


class TestAnAddressWhoseAccountIsGone(AutoLinkCase):
    """Skipped, and the walk goes on -- rather than ending in a fresh account
    while a lower-ranked address belongs to a live one."""

    @pytest.fixture(autouse=True)
    def _accounts(self, _setup) -> None:
        self.plugin.store.add(EMAIL_PROVIDER, PREFERRED, "deleted-user", {})
        self.account("alice", SECOND)

    def test_the_next_live_account_is_adopted(self):
        assert self.authenticate(entry(PREFERRED), entry(SECOND)) == "alice"

    def test_the_stale_address_is_still_reported(self, caplog):
        """An operator has a stale identity to remove, and this is the only
        place that notices it."""
        with caplog.at_level(logging.WARNING, logger="pas.plugins.identity"):
            self.authenticate(entry(PREFERRED), entry(SECOND))

        assert any(
            "has no account for" in record.getMessage()
            and PREFERRED in record.getMessage()
            for record in caplog.records
        )

    def test_it_is_not_a_conflict(self, caplog):
        """A userid with no account is nobody to choose between."""
        with caplog.at_level(logging.ERROR, logger="pas.plugins.identity"):
            self.authenticate(entry(PREFERRED), entry(SECOND))

        assert conflicts(caplog) == []
