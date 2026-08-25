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
