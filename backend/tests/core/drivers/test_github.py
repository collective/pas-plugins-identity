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

    def test_the_primary_verified_address_wins(self):
        """An account may hold several."""
        merged = self.driver.merge_enrichment(
            {"id": 1, "login": "ghost"},
            [
                {"email": "old@example.com", "primary": False, "verified": True},
                {"email": "me@example.com", "primary": True, "verified": True},
            ],
        )

        assert merged["email"] == "me@example.com"

    def test_a_verified_address_beats_an_unverified_primary(self):
        merged = self.driver.merge_enrichment(
            {"id": 1, "login": "ghost"},
            [
                {
                    "email": "unconfirmed@example.com",
                    "primary": True,
                    "verified": False,
                },
                {"email": "real@example.com", "primary": False, "verified": True},
            ],
        )

        assert merged["email"] == "real@example.com"

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
