"""A logout upstream reaches the tokens this site issued downstream.

The seam between the two layers. Core receives the provider's back-channel
logout and fires ``SessionsRevoked``; this layer hears it and revokes the
refresh tokens it issued, because core cannot import ``server`` and has no
idea those tokens exist.

The event is fired directly here rather than driven through the endpoint. The
endpoint's job -- validating a provider's token and firing this event -- is
tested in ``tests/core/test_logout.py`` against a stubbed provider JWKS;
repeating that setup would test the stub twice and the subscriber once.
"""

from . import PROFILE_ID
from . import USERID
from pas.plugins.identity.core.events import SessionsRevoked
from pas.plugins.identity.server.pas import PLUGIN_ID
from zope.event import notify

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])

OTHER = "bob"


@pytest.fixture
def store(portal):
    """The refresh-token store."""
    return portal.acl_users[PLUGIN_ID].refresh


def logout(userid: str) -> None:
    """Fire the event core fires on a back-channel logout.

    :param userid: The user who was logged out upstream.
    """
    notify(
        SessionsRevoked(
            userid=userid,
            provider="upstream",
            subject="provider-subject",
            sessions_ended=True,
        )
    )


class TestRefreshTokensAreRevoked:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, store) -> None:
        self.portal = portal
        self.store = store

    def test_the_users_tokens_are_gone(self):
        """The point of the whole chain: a client cannot keep renewing
        access after the person behind it signed out somewhere else."""
        self.store.issue("app", USERID, "openid")

        logout(USERID)

        assert self.store.count() == 0

    def test_every_client_loses_them_not_just_one(self):
        """The logout was about the person, not about one application."""
        self.store.issue("app", USERID)
        self.store.issue("other-app", USERID)

        logout(USERID)

        assert self.store.count() == 0

    def test_another_user_is_untouched(self):
        self.store.issue("app", USERID)
        self.store.issue("app", OTHER)

        logout(USERID)

        assert self.store.count() == 1

    def test_a_user_with_no_tokens_is_not_an_error(self):
        logout("never-issued-anything")

        assert self.store.count() == 0

    def test_a_site_without_the_server_plugin_is_quiet(self):
        """Core fires this event on every site that receives a back-channel
        logout. Most of them are relying parties that never applied the
        server profile and have no tokens of their own to revoke."""
        self.portal.acl_users._delObject(PLUGIN_ID)

        logout(USERID)
