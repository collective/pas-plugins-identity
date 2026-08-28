"""What happens to an offered address list on a site that cannot ask.

A driver offered several addresses picks none of them and carries the list, so
the user can say which is theirs on their profile. That only works where there
*are* profiles. With the ``[content]`` layer absent there is no profile, no
form and no gate, so nobody is ever asked -- and the account would end up with
no address at all, which is worse than the guess the choice replaced.

Found by Érico installing the backend without the ``[content]`` extra
(2026-08-28): a GitHub sign-in produced a user with no email and nothing
asking for one.
"""

from ...content import PROFILE_ID as CONTENT_PROFILE
from . import DEX_IDENTITY
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


class TestASiteWithNowhereToAsk:
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

    def test_the_site_really_does_not_keep_users_as_content(self):
        """The premise. With the records set this test would prove nothing,
        and it is the same question the guard itself asks."""
        assert not self.plugin._users_are_content()

    def test_an_address_is_chosen(self):
        """The bug: no address at all, and nothing anywhere to ask for one."""
        userid = self.authenticate(dict(CLAIMS_WITH_CHOICES))

        assert api.user.get(userid=userid).getProperty("email") == "me@example.com"

    def test_the_first_offer_is_taken(self):
        """Which the driver already ordered: primary and verified first."""
        userid = self.authenticate({
            **CLAIMS_WITH_CHOICES,
            "email_choices": tuple(reversed(OFFERED)),
        })

        assert api.user.get(userid=userid).getProperty("email") == "old@example.com"

    def test_an_address_the_driver_sent_is_not_overridden(self):
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


@pytest.mark.portal(profiles=[CONTENT_PROFILE])
class TestASiteThatCanAsk:
    """Users as content: a profile is minted, and the gate holds its owner on
    the form that asks. The question survives to be answered.

    The real profile rather than the two registry records on their own:
    ``_keeps_users_as_content`` also checks the configured type is one this
    plugin may create a user in, and that type does not exist until the
    ``[content]`` profile has registered it.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin) -> None:
        self.portal = portal
        self.plugin = plugin

    def test_the_site_really_can_ask(self):
        """The premise, for the same reason as the class above."""
        assert self.plugin._users_are_content()

    def test_the_container_does_not_exist_yet(self):
        """Which is the point of asking `_users_are_content` instead: the
        container is created while the first profile is minted, so on the
        very first login to a fresh site it is not there."""
        assert not self.plugin._keeps_users_as_content()

    def test_the_choice_is_left_open(self):
        settled = self.plugin._settle_email(dict(CLAIMS_WITH_CHOICES))

        assert settled["email"] == ""
        assert settled["email_choices"] == OFFERED
