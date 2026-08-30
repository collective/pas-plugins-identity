"""A provider this site trusts can verify an address on its own word.

The rule this holds in place, which is a rule about who decides rather than
about who is trustworthy: an address counts as verified here when this site
proved it with a magic link, **or** when a provider the operator marked
``trust_email_verification`` says it proved it. Nothing else has changed --
verification is still one ``email`` identity in the store and still not a
second flag, and a provider nobody marked is still worth nothing.

The switch is what these tests are about. Google and GitHub default to on
because they really do check; every other driver defaults to off; and an
operator overrules either way.
"""

from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.pas import PLUGIN_ID as CORE_PLUGIN_ID
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from pas.plugins.identity.core.subscribers import get_profile
from pas.plugins.identity.core.verification import record_verified_addresses
from pas.plugins.identity.core.verification import trusts_verification
from pas.plugins.identity.core.verification import verified_by_provider
from plone import api
from plone.app.testing import TEST_USER_ID

import pytest


TRUSTING = "trusting"
DOUBTING = "doubting"

MINE = "alice@example.com"
ALSO_MINE = "alice@example.org"
UNVERIFIED = "old@example.net"

CLAIMS = {
    "fullname": "Alice Liddell",
    "email": MINE,
    "email_verified": True,
    "username": "alice",
    "raw": {},
    "emails": (
        {"address": MINE, "verified": True, "primary": True},
        {"address": ALSO_MINE, "verified": True, "primary": False},
        {"address": UNVERIFIED, "verified": False, "primary": False},
    ),
}


class TestReadingTheClaim:
    """Which addresses a provider says it verified, before anyone asks
    whether that is worth anything."""

    def test_only_the_verified_ones(self):
        """The list carries the unverified ones too; they are still theirs."""
        assert verified_by_provider(CLAIMS) == (MINE, ALSO_MINE)

    def test_a_truthy_string_is_not_a_yes(self):
        """Several providers send ``"true"``, and it means nothing here."""
        claims = {"emails": ({"address": MINE, "verified": "true"},)}

        assert verified_by_provider(claims) == ()

    def test_the_same_address_twice_is_one_address(self):
        """GitHub can report a mailbox under two spellings; it is one
        mailbox, and linking it twice is a collision."""
        claims = {
            "emails": (
                {"address": MINE, "verified": True},
                {"address": MINE.upper(), "verified": True},
            )
        }

        assert verified_by_provider(claims) == (MINE,)

    def test_a_blank_address_is_not_an_address(self):
        """A provider vouching for nothing has vouched for nothing."""
        claims = {"emails": ({"address": "   ", "verified": True},)}

        assert verified_by_provider(claims) == ()

    def test_a_provider_sending_nothing_verifies_nothing(self):
        """No list, no addresses, no claim about any."""
        assert verified_by_provider({"email": MINE, "email_verified": True}) == ()


class TestRecording:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin) -> None:
        self.portal = portal
        self.plugin = plugin
        set_providers([
            ProviderConfig(
                TRUSTING,
                "oidc-generic",
                config={"trust_email_verification": True},
            ),
            ProviderConfig(
                DOUBTING,
                "oidc-generic",
                config={"trust_email_verification": False},
            ),
        ])

    def verified(self, userid: str = TEST_USER_ID) -> set[str]:
        """Return the addresses this site holds as verified for a user.

        Read from the store rather than from the Profile, because the store is
        where verification lives and the Profile only derives from it.

        :param userid: The owner.
        :returns: The verified addresses.
        """
        store = self.portal.acl_users[CORE_PLUGIN_ID].store
        return {
            record.subject
            for record in store.identities_for(userid)
            if record.provider == EMAIL_PROVIDER
        }

    def test_a_trusted_provider_verifies_its_addresses(self):
        """Both of the ones it vouched for, and not the one it did not."""
        record_verified_addresses(TEST_USER_ID, TRUSTING, CLAIMS)

        assert self.verified() == {MINE, ALSO_MINE}

    def test_an_untrusted_provider_verifies_nothing(self):
        """Its word is carried, shown, and acted on nowhere."""
        record_verified_addresses(TEST_USER_ID, DOUBTING, CLAIMS)

        assert self.verified() == set()

    def test_a_provider_this_site_no_longer_has_verifies_nothing(self):
        """An identity outlives its configuration; the safe answer is no."""
        record_verified_addresses(TEST_USER_ID, "deleted-provider", CLAIMS)

        assert self.verified() == set()

    def test_recording_twice_is_not_an_error(self):
        """Every login of a trusted provider runs this."""
        record_verified_addresses(TEST_USER_ID, TRUSTING, CLAIMS)
        second = record_verified_addresses(TEST_USER_ID, TRUSTING, CLAIMS)

        assert second == ()
        assert self.verified() == {MINE, ALSO_MINE}

    def test_somebody_elses_verified_address_is_refused(self):
        """Two people cannot both have proved one mailbox, and moving the
        identity would be one of them taking the other's account."""
        other = api.user.create(
            email="other@plone.org", username="other", password="s3cr3t-other"
        ).getId()
        self.portal.acl_users[CORE_PLUGIN_ID].link(
            other, EMAIL_PROVIDER, MINE, {"email": MINE}
        )

        recorded = record_verified_addresses(TEST_USER_ID, TRUSTING, CLAIMS)

        assert recorded == (ALSO_MINE,)
        assert self.verified(other) == {MINE}

    def test_the_email_provider_is_not_routed_through_here(self):
        """Redeeming the link is what writes the identity. There is nothing
        left to record, and recording it would write the row again."""
        assert record_verified_addresses(TEST_USER_ID, EMAIL_PROVIDER, CLAIMS) == ()


class TestTheDefaults:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    @pytest.mark.parametrize("driver_id", ["google", "github"])
    def test_a_provider_that_really_checks_is_trusted(self, driver_id):
        """Both refuse to call an address verified until the account has
        answered mail at it, so a site gets the sensible answer unconfigured."""
        set_providers([ProviderConfig("p", driver_id)])

        assert trusts_verification("p") is True

    def test_anything_else_is_not(self):
        """An operator running a permissive provider has to say so."""
        set_providers([ProviderConfig("p", "oidc-generic")])

        assert trusts_verification("p") is False


class TestAtLogin:
    """The whole path, because a correct module nothing calls is worth
    nothing."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin) -> None:
        self.portal = portal
        self.plugin = plugin
        set_providers([
            ProviderConfig(
                TRUSTING,
                "oidc-generic",
                config={"trust_email_verification": True},
            ),
        ])

    def test_a_login_leaves_the_addresses_verified(self):
        """On the Profile, which is where anyone reads them."""
        from pas.plugins.identity.core.pas import EXTRACTOR

        userid, _ = self.plugin.authenticateCredentials({
            "extractor": EXTRACTOR,
            "provider": TRUSTING,
            "subject": "alice-subject",
            "claims": dict(CLAIMS),
        })

        profile = get_profile(userid)
        assert profile.emails == (MINE, ALSO_MINE, UNVERIFIED)
        assert profile.verified_emails == (MINE, ALSO_MINE)

    def test_the_derived_address_is_a_verified_one(self):
        """Which is the point: nobody is asked to prove what Google proved."""
        from pas.plugins.identity.core.pas import EXTRACTOR

        userid, _ = self.plugin.authenticateCredentials({
            "extractor": EXTRACTOR,
            "provider": TRUSTING,
            "subject": "alice-subject",
            "claims": {
                **CLAIMS,
                "email": UNVERIFIED,
                "emails": (
                    {"address": UNVERIFIED, "verified": False, "primary": True},
                    {"address": MINE, "verified": True, "primary": False},
                ),
            },
        })

        assert get_profile(userid).email == MINE
