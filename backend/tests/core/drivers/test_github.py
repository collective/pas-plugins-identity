"""The GitHub driver."""

from . import GITHUB_USER
from . import GITHUB_USER_NO_NAME
from pas.plugins.identity.core.drivers.github import GitHubDriver

import pytest


class TestGitHubDriver:
    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.driver = GitHubDriver()

    def test_userid_defaults_to_the_login(self):
        """A GitHub login is unique on the provider and readable here, so it
        beats 32 hex characters as a Plone userid."""
        assert self.driver.config_schema()["userid_source"]["default"] == "username"

    def test_subject_is_numeric_id_as_string(self):
        """The numeric id is stringified so the store key is stable."""
        assert self.driver.subject(GITHUB_USER) == "1234567"

    def test_subject_falls_back_to_node_id(self):
        """A payload without ``id`` still yields a stable subject."""
        assert self.driver.subject({"node_id": "MDQ6VXNlcjE="}) == "MDQ6VXNlcjE="

    @pytest.mark.parametrize(
        "key,expected",
        [
            ("fullname", "Érico Andrei"),
            ("email", "erico@plone.org"),
            ("email_verified", True),
            ("username", "ericof"),
            (
                "picture_url",
                "https://avatars.githubusercontent.com/u/1234567?v=4",
            ),
        ],
    )
    def test_claims(self, key: str, expected):
        """Each documented claim is read from the right GitHub field."""
        assert self.driver.normalize_claims(GITHUB_USER)[key] == expected

    def test_email_is_lowercased(self):
        """GitHub echoes the address as typed; the claim is canonical."""
        assert GITHUB_USER["email"] == "Erico@Plone.ORG"
        assert self.driver.normalize_claims(GITHUB_USER)["email"] == "erico@plone.org"

    def test_fullname_falls_back_to_login(self):
        """An account with no display name is not created nameless."""
        claims = self.driver.normalize_claims(GITHUB_USER_NO_NAME)

        assert claims["fullname"] == "anon-dev"


class TestTheAddressComesFromASecondCall:
    """``/user`` is not the whole story, and this is the half that fixes it.

    GitHub omits the address of anybody who marked it private and never sends
    ``email_verified`` at all, so on ``/user`` alone a GitHub identity arrives
    with no address and can never be auto-linked by one. ``GET /user/emails``
    answers both, and the ``user:email`` scope needed to call it has always
    been requested.

    The driver still performs no I/O: it names the endpoint and merges the
    answer, and :mod:`pas.plugins.identity.core.flows` does the fetching.
    """

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.driver = GitHubDriver()
        self.metadata = {"emails_endpoint": "https://api.github.com/user/emails"}

    def test_the_endpoint_is_named(self):
        assert self.driver.enrichment_endpoint(self.metadata) == (
            "https://api.github.com/user/emails"
        )

    def test_no_endpoint_without_it_in_the_metadata(self):
        """A provider whose metadata predates this must not be asked for a
        URL the driver invented."""
        assert self.driver.enrichment_endpoint({}) == ""

    def test_a_private_address_arrives(self):
        """The case the driver could not serve before: `/user` carried no
        address at all."""
        payload = {"id": 1, "login": "ghost"}

        merged = self.driver.merge_enrichment(
            payload, [{"email": "ghost@example.com", "primary": True, "verified": True}]
        )

        assert self.driver.normalize_claims(merged)["email"] == "ghost@example.com"

    def test_a_verified_address_is_reported_as_verified(self):
        """Which is what link-by-verified-email reads, and what a GitHub
        identity could never satisfy before."""
        merged = self.driver.merge_enrichment(
            {"id": 1, "login": "ghost"},
            [{"email": "ghost@example.com", "primary": True, "verified": True}],
        )

        assert self.driver.normalize_claims(merged)["email_verified"] is True

    def test_the_address_is_lowercased(self):
        """Case-insensitive in practice, and the store keys identities on it."""
        merged = self.driver.merge_enrichment(
            {"id": 1, "login": "ghost"},
            [{"email": "Ghost@Example.COM", "primary": True, "verified": True}],
        )

        assert self.driver.normalize_claims(merged)["email"] == "ghost@example.com"

    def test_an_unverified_primary_is_still_used(self):
        """An address is worth having even when nobody will auto-link on it:
        it is what stops the profile being minted incomplete."""
        merged = self.driver.merge_enrichment(
            {"id": 1, "login": "ghost"},
            [{"email": "unconfirmed@example.com", "primary": True, "verified": False}],
        )

        assert merged["email"] == "unconfirmed@example.com"
        assert self.driver.normalize_claims(merged)["email_verified"] is False

    @pytest.mark.parametrize(
        "answer",
        [[], {}, None, "not a list", [{"verified": True}], [{"email": "   "}]],
        ids=["empty", "object", "null", "string", "no-address", "blank-address"],
    )
    def test_an_unusable_answer_leaves_the_payload_alone(self, answer):
        """A surprising shape must cost nothing rather than raise in the
        middle of a login."""
        payload = {"id": 1, "login": "ghost", "email": "from-user@example.com"}

        assert self.driver.merge_enrichment(payload, answer) == payload


class TestSeveralAddressesAreAQuestion:
    """One address is an answer; several are a question.

    Picking the primary, or the first verified one, is a guess made on the
    user's behalf about which identity they are here as -- and the address
    decides which existing account a verified-email link would attach to. So
    an account with more than one usable address has none of them chosen
    here: the list is carried forward and the user is asked on their profile,
    which the required-information gate holds them on until they answer.
    """

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.driver = GitHubDriver()
        self.several = [
            {"email": "noreply@users.noreply.github.com", "verified": True},
            {"email": "me@example.com", "primary": True, "verified": True},
            {"email": "old@example.com", "verified": False},
        ]

    def claims(self, addresses):
        """Run a payload and an address list through both steps.

        :param addresses: What ``GET /user/emails`` answered.
        :returns: The normalized claims.
        """
        merged = self.driver.merge_enrichment({"id": 1, "login": "ghost"}, addresses)
        return self.driver.normalize_claims(merged)

    def test_no_address_is_chosen(self):
        """The bug this replaces: `me@example.com` used to win here."""
        assert self.claims(self.several)["email"] == ""

    def test_nothing_is_reported_as_verified_either(self):
        """An unanswered question cannot satisfy link-by-verified-email."""
        assert self.claims(self.several)["email_verified"] is False

    def test_every_address_is_offered(self):
        choices = self.claims(self.several)["email_choices"]

        assert {choice["address"] for choice in choices} == {
            "me@example.com",
            "noreply@users.noreply.github.com",
            "old@example.com",
        }

    def test_the_primary_is_offered_first(self):
        """A hint for ordering the choice, not a decision: it is presented
        first and still has to be picked."""
        assert self.claims(self.several)["email_choices"][0]["address"] == (
            "me@example.com"
        )

    def test_verified_addresses_are_offered_before_unverified(self):
        choices = self.claims(self.several)["email_choices"]

        assert [choice["verified"] for choice in choices] == [True, True, False]

    def test_the_provider_order_survives_within_a_group(self):
        """`sorted` is stable, so a list that does not change at the provider
        does not reorder itself between two logins."""
        addresses = [
            {"email": "b@example.com", "verified": True},
            {"email": "a@example.com", "verified": True},
        ]

        choices = self.claims(addresses)["email_choices"]

        assert [choice["address"] for choice in choices] == [
            "b@example.com",
            "a@example.com",
        ]

    def test_a_single_address_is_not_a_question(self):
        """Nothing to decide, so it is used exactly as a provider that sent
        one address would be -- and the user is never asked."""
        claims = self.claims([{"email": "only@example.com", "verified": True}])

        assert claims["email"] == "only@example.com"
        assert claims.get("email_choices", ()) == ()

    def test_a_repeated_address_is_not_a_choice(self):
        """Offering the same address twice is a question with one answer."""
        claims = self.claims([
            {"email": "me@example.com", "primary": True, "verified": True},
            {"email": "ME@example.com", "verified": False},
        ])

        assert claims["email"] == "me@example.com"
        assert claims.get("email_choices", ()) == ()

    def test_the_carrier_key_does_not_leak_into_raw(self):
        """`raw` is documented as the untouched provider payload, and the key
        used to carry the list between the two steps is this package's."""
        raw = self.claims(self.several)["raw"]

        assert GitHubDriver.ADDRESSES_KEY not in raw
        assert not any(key.startswith("_pas_plugins") for key in raw)

    def test_an_account_with_no_addresses_offers_no_choice(self):
        claims = self.claims([])

        assert claims.get("email_choices", ()) == ()
