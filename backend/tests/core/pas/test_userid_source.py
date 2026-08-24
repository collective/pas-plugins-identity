"""Minting a userid from what the provider says."""

from . import CLAIMS
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.pas import EXTRACTOR
from pas.plugins.identity.core.pas.plugin import mint_userid
from plone import api

import pytest


PROVIDER = "github"


def configure(source: str) -> None:
    """Store a provider minting userids from ``source``.

    :param source: One of the userid sources.
    """
    set_providers([
        ProviderConfig(
            provider_id=PROVIDER,
            driver_id="github",
            config={"userid_source": source},
        )
    ])


class TestMintUserid:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_defaults_to_a_random_id(self):
        userid = mint_userid()

        assert len(userid) == 32
        assert mint_userid() != mint_userid()

    def test_from_the_username(self):
        assert mint_userid("username", CLAIMS) == "ericof"

    def test_from_the_email(self):
        # Normalized, because an address is not a legal id as it stands.
        assert mint_userid("email", CLAIMS) == "erico-plone-org"

    def test_from_the_subject(self):
        assert mint_userid("subject", CLAIMS, subject="1234567") == "1234567"

    def test_normalizes_what_the_provider_sent(self):
        """A claim is free text; a userid is not."""
        claims = {**CLAIMS, "username": "Érico Andrei!"}

        assert mint_userid("username", claims) == "erico-andrei"

    def test_falls_back_when_the_claim_is_empty(self):
        """A provider that sent nothing usable must not stop the login."""
        claims = {**CLAIMS, "username": ""}

        assert len(mint_userid("username", claims)) == 32

    def test_falls_back_on_an_unknown_source(self):
        assert len(mint_userid("nonsense", CLAIMS)) == 32

    def test_never_hands_out_a_userid_somebody_holds(self):
        """The guard that matters: a provider account called `admin` must not
        be handed the site's admin userid and inherit its roles."""
        api.user.create(email="taken@example.org", username="ericof")

        assert mint_userid("username", CLAIMS) == "ericof-2"

    def test_suffixes_until_it_finds_a_free_one(self):
        api.user.create(email="a@example.org", username="ericof")
        api.user.create(email="b@example.org", username="ericof-2")

        assert mint_userid("username", CLAIMS) == "ericof-3"


class TestUseridSourceOnLogin:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin) -> None:
        self.portal = portal
        self.plugin = plugin

    def authenticate(self, subject="1234567"):
        """Sign in through the plugin.

        :param subject: The provider-side subject.
        :returns: The userid resolved to.
        """
        userid, _ = self.plugin.authenticateCredentials({
            "extractor": EXTRACTOR,
            "provider": PROVIDER,
            "subject": subject,
            "claims": CLAIMS,
        })
        return userid

    def test_a_provider_can_ask_for_a_readable_userid(self):
        configure("username")

        assert self.authenticate() == "ericof"

    def test_the_default_is_still_a_random_id(self):
        configure("uuid")

        assert len(self.authenticate()) == 32

    def test_an_unconfigured_provider_still_signs_in(self):
        """No provider record at all: fall back rather than refuse."""
        set_providers([])

        assert len(self.authenticate()) == 32

    def test_the_userid_is_stable_across_logins(self):
        """It is minted once and stored; a later claim change must not move
        an account to a different userid."""
        configure("username")
        first = self.authenticate()

        assert self.authenticate() == first

    def test_two_people_with_the_same_username_do_not_collide(self):
        """Different subjects are different people, whatever they call
        themselves."""
        configure("username")
        first = self.authenticate(subject="1")

        second = self.authenticate(subject="2")

        assert first == "ericof"
        assert second == "ericof-2"
