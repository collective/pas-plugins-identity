"""The Google driver."""

from . import GOOGLE_USERINFO
from pas.plugins.identity.core.drivers.google import GoogleDriver

import pytest


class TestGoogleDriver:
    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.driver = GoogleDriver()

    def test_subject_is_sub(self):
        """The OIDC subject, never the mutable email."""
        assert self.driver.subject(GOOGLE_USERINFO) == "104928374650192837465"

    @pytest.mark.parametrize(
        "key,expected",
        [
            ("fullname", "Érico Andrei"),
            ("email", "erico@plone.org"),
            ("email_verified", True),
            ("picture_url", "https://lh3.googleusercontent.com/a/ACg8ocK"),
        ],
    )
    def test_claims(self, key: str, expected):
        """Each documented claim is read from the right OIDC field."""
        assert self.driver.normalize_claims(GOOGLE_USERINFO)[key] == expected

    def test_hosted_domain_field_present(self):
        """Workspace restriction is configurable."""
        assert "hosted_domain" in self.driver.config_schema()
