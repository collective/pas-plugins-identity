"""Userids minted from claims, on a site where the account is a ``source_users`` row.

On a site with Profiles, the minted userid becomes a content object, and the
only thing that can collide with it is another principal's id -- which
:func:`~pas.plugins.identity.core.pas.plugin.mint_userid` checks. Here the
userid becomes a ``source_users`` row, and that row has a *login* as well,
which ``source_users`` keeps unique on its own. The login is the userid. So a
userid nobody holds can still be a login somebody holds -- a local account
created with an address as its login, or one whose login was changed -- and
the provider's claim decides which.

Every claim below is something a provider can send. Whatever it is, the
person gets in, and gets an account of their own.
"""

from . import CLAIMS
from . import PROVIDER
from . import sign_in
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from plone import api

import pytest


pytestmark = pytest.mark.no_profile_container


@pytest.fixture
def source_users(core_only):
    """Return the site's ``source_users`` plugin.

    :param core_only: The core-only site.
    :returns: The ZODB user manager.
    """
    return api.portal.get_tool("acl_users").source_users


def mint_from(source: str) -> None:
    """Make the provider mint userids from ``source``.

    :param source: One of the userid sources.
    """
    set_providers([
        ProviderConfig(
            provider_id=PROVIDER,
            driver_id="oidc-generic",
            title="Dex",
            config={"userid_source": source},
        )
    ])


def as_user(username, **extra) -> dict:
    """Return :data:`CLAIMS` with another ``username``.

    :param username: The claim, whatever its type.
    :param extra: Further keys to replace.
    :returns: A fresh claims mapping.
    """
    return {**CLAIMS, "username": username, **extra}


class TestAUsernameSomebodyHolds:
    @pytest.fixture(autouse=True)
    def _setup(self, identity_plugin, source_users) -> None:
        self.plugin = identity_plugin
        self.source_users = source_users
        mint_from("username")

    def test_as_a_userid(self):
        api.user.create(email="other@example.org", username="ericof")

        userid = sign_in(self.plugin)

        assert userid == "ericof-2"

    def test_as_a_login(self):
        """The case the userid check alone cannot see: ``ericof`` is free as
        a userid and taken as a login."""
        self.source_users.addUser("a1b2c3", "ericof", "secret-secret")

        userid = sign_in(self.plugin)

        assert userid != "a1b2c3"
        assert api.user.get(userid=userid) is not None

    def test_as_a_login_the_holder_keeps_it(self):
        self.source_users.addUser("a1b2c3", "ericof", "secret-secret")

        sign_in(self.plugin)

        assert self.source_users.getLoginForUserId("a1b2c3") == "ericof"

    def test_the_site_owner(self):
        """A provider account called ``admin`` is the takeover the userid
        guard exists for."""
        userid = sign_in(self.plugin, claims=as_user("admin"))

        assert userid != "admin"

    def test_two_people_with_one_username(self):
        """Two providers, or one provider that reuses names."""
        first = sign_in(self.plugin, subject="one")
        second = sign_in(self.plugin, subject="two")

        assert first != second
        assert {first, second} <= set(self.source_users.getUserIds())


class TestUsernamesThatAreNotIds:
    @pytest.fixture(autouse=True)
    def _setup(self, identity_plugin) -> None:
        self.plugin = identity_plugin
        mint_from("username")

    @pytest.mark.parametrize(
        "username",
        [
            "Érico Andrei",
            "ericof@example.org",
            "../../etc/passwd",
            "<script>alert(1)</script>",
            "ericof\x00",
            "🦄",
            "   ",
            "x" * 1_000,
            42,
            ["ericof"],
            {"login": "ericof"},
            None,
            True,
        ],
        ids=[
            "accented",
            "address",
            "path",
            "markup",
            "control",
            "emoji",
            "blank",
            "long",
            "integer",
            "list",
            "object",
            "null",
            "true",
        ],
    )
    def test_the_person_gets_an_account(self, username):
        userid = sign_in(self.plugin, claims=as_user(username))

        assert api.user.get(userid=userid) is not None

    @pytest.mark.parametrize(
        "username",
        ["../../etc/passwd", "<script>alert(1)</script>", "ericof\x00", "a b"],
        ids=["path", "markup", "control", "space"],
    )
    def test_the_userid_is_an_id(self, username):
        """A userid ends up in URLs, in local roles and in the catalog."""
        userid = sign_in(self.plugin, claims=as_user(username))

        assert userid.replace("-", "").isalnum()


class TestAnAddressAsTheUserid:
    @pytest.fixture(autouse=True)
    def _setup(self, identity_plugin, source_users) -> None:
        self.plugin = identity_plugin
        self.source_users = source_users
        mint_from("email")

    def test_an_address_somebody_logs_in_with(self):
        """A site using addresses as logins holds the address as a login
        already; the minted userid is a normalized form, so both live."""
        self.source_users.addUser("a1b2c3", "erico@plone.org", "secret-secret")

        userid = sign_in(self.plugin)

        assert userid not in ("a1b2c3", "erico@plone.org")
        assert api.user.get(userid=userid) is not None

    @pytest.mark.parametrize(
        "email",
        ["", None, 42, ["erico@plone.org"]],
        ids=["empty", "null", "integer", "list"],
    )
    def test_no_usable_address(self, email):
        userid = sign_in(self.plugin, claims={**CLAIMS, "email": email})

        assert api.user.get(userid=userid) is not None
