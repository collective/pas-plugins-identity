"""An identity that outlived the account behind it.

Auto-link-by-verified-email attaches a new provider identity to whichever
account proved that address to this site with a magic link. It looked the
owner up and adopted it, and nothing asked whether that account still
existed.

When it does not -- an account deleted after its address was verified, a
store restored beside a different one -- the login *succeeds* and returns a
userid nothing resolves. No properties, no roles, invisible to every search,
and a traceback from whichever line touches the user first. Érico hit exactly
that signing in with Google after verifying an address (2026-08-28): the
account behind the identity was gone, Google adopted it anyway, and the
callback died in `mint_token`.

Minting a fresh account instead is not what the operator configured, but it
is a working login and it is recoverable: the stale identity is one `remove`
away from letting the next attempt link properly.
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
ADDRESS = "ericof@plone.org"

CLAIMS = {
    "fullname": "Erico",
    "email": ADDRESS,
    "email_verified": True,
    "username": "ericof",
    "raw": {},
}


class TestAdoptingAnAccountThatIsGone:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin) -> None:
        self.portal = portal
        self.plugin = plugin
        set_providers([
            ProviderConfig(
                provider_id=PROVIDER,
                driver_id="oidc-generic",
                title="Dex",
                config={
                    "auto_link_by_email": True,
                    # Both switches, because auto-linking needs the address
                    # this provider just sent to be worth something.
                    "trust_email_verification": True,
                },
            )
        ])

    def verify_for(self, userid: str) -> None:
        """Record that *userid* proved the address with a magic link.

        :param userid: The account that owns the verified address.
        """
        self.plugin.store.add(EMAIL_PROVIDER, ADDRESS, userid, {})

    def authenticate(self) -> str:
        """Sign in with the provider and return the resolved userid.

        :returns: The Plone userid.
        """
        userid, _ = self.plugin.authenticateCredentials({
            "extractor": EXTRACTOR,
            "provider": PROVIDER,
            "subject": SUBJECT,
            "claims": dict(CLAIMS),
        })
        return userid

    def test_a_live_account_is_still_adopted(self):
        """The feature itself, so the guard below cannot pass by breaking it."""
        with api.env.adopt_roles(["Manager"]):
            api.user.create(
                username="live-user", email=ADDRESS, password="a-long-enough-password"
            )
        self.verify_for("live-user")

        assert self.authenticate() == "live-user"

    def test_a_dead_account_is_not_adopted(self):
        """The bug: signed in as a userid nothing resolves."""
        self.verify_for("deleted-user")

        assert self.authenticate() != "deleted-user"

    def test_the_login_still_works(self):
        """Refusing to adopt must not refuse the sign-in."""
        self.verify_for("deleted-user")

        assert self.authenticate()

    def test_the_user_it_signs_in_as_exists(self):
        """Which is the whole point: a working login, not a phantom."""
        self.verify_for("deleted-user")

        userid = self.authenticate()

        assert api.user.get(userid=userid) is not None

    def test_it_says_so(self, caplog):
        """An operator has a stale identity to remove and no way to know it
        unless this is said: the login now succeeds, so nothing else shows."""
        self.verify_for("deleted-user")

        with caplog.at_level(logging.WARNING, logger="pas.plugins.identity"):
            self.authenticate()

        assert any("has no account for" in r.getMessage() for r in caplog.records)

    def test_the_message_names_the_address(self, caplog):
        """Which is what an operator removes the stale identity by."""
        self.verify_for("deleted-user")

        with caplog.at_level(logging.WARNING, logger="pas.plugins.identity"):
            self.authenticate()

        assert any(ADDRESS in r.getMessage() for r in caplog.records)


class TestAKnownIdentityWhoseAccountIsGone:
    """The state Érico's instance was actually in.

    His store held two userids: `ericof`, with a GitHub identity and a
    verified address, resolving fine -- and a uuid holding one Google
    identity and nothing else, with no account anywhere. Auto-linking was
    off, so the Google identity had been minted fresh and its account had
    since gone away.

    That never recovers on its own. The identity is *found*, so the branch
    that creates a user is not taken, and every login through it resolves to
    a userid nothing can serve. It is not a first login, it is not a link,
    and nothing else looks.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin) -> None:
        self.portal = portal
        self.plugin = plugin
        set_providers([
            ProviderConfig(provider_id=PROVIDER, driver_id="oidc-generic", title="Dex")
        ])
        # A login that worked once, and an account removed afterwards.
        self.userid = self.authenticate()
        with api.env.adopt_roles(["Manager"]):
            api.user.delete(username=self.userid)

    def authenticate(self) -> str:
        """Sign in with the provider and return the resolved userid.

        :returns: The Plone userid.
        """
        userid, _ = self.plugin.authenticateCredentials({
            "extractor": EXTRACTOR,
            "provider": PROVIDER,
            "subject": SUBJECT,
            "claims": dict(CLAIMS),
        })
        return userid

    def test_the_account_really_is_gone(self):
        """The premise. Without it everything below passes vacuously."""
        assert api.user.get(userid=self.userid) is None

    def test_the_identity_is_still_held(self):
        """Which is why nothing recreates the account: the login is not a
        first one any more."""
        assert self.plugin.store.userid_for(PROVIDER, SUBJECT) == self.userid

    def test_signing_in_again_restores_it(self):
        """The bug: it resolved to the same dead userid for ever."""
        self.authenticate()

        assert api.user.get(userid=self.userid) is not None

    def test_the_same_userid_is_kept(self):
        """Not a fresh one: it is what the identity points at and what
        anything this person owns is owned by."""
        assert self.authenticate() == self.userid

    def test_the_restored_account_carries_the_claims(self):
        """Restored, not merely present."""
        self.authenticate()

        assert api.user.get(userid=self.userid).getProperty("email") == ADDRESS

    def test_it_says_so(self, caplog):
        """An account reappearing is not what an operator who deleted one
        expects, and removing the identity is what makes it stick.

        The Profile is put back by a subscriber that runs on every login and
        cannot say anything, so this is the one place that can tell an
        ordinary sign-in from a restoration.
        """
        with caplog.at_level(logging.WARNING, logger="pas.plugins.identity"):
            self.authenticate()

        assert any("has no account" in r.getMessage() for r in caplog.records)

    def test_a_live_account_is_left_alone(self, caplog):
        """The guard must not fire on the ordinary login it sits in front of:
        it runs on every sign-in through an identity already known."""
        self.authenticate()
        caplog.clear()

        with caplog.at_level(logging.WARNING, logger="pas.plugins.identity"):
            self.authenticate()

        assert not [r for r in caplog.records if "restoring it" in r.getMessage()]
