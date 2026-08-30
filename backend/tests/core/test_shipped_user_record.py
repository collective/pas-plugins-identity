"""A federated first login on a site whose users are Profiles.

The configuration the demo identity provider runs, and the one where the
defect was visible: every first login wrote a ``source_users`` account beside
the Profile, so ``acl_users/source_users/manage_users`` listed everybody
twice over -- once as a row nothing keeps in step, once as the object that is
actually the user.

Core declines that row on a site that keeps its users as content, and the
shipped subscriber creates the Profile from the login event.
:mod:`tests.core.pas.test_external_user_record` proves core's half against a
stub type and a stand-in subscriber; this module is the shipped pair, because
a plugin that declines correctly and a layer that claims correctly can still
fail to add up to a user.

Named apart from that module rather than beside it. The two used to share the
basename ``test_external_user_record.py`` in different directories, which put
the whole of one of them a single mistyped path away from being overwritten
by a tool that reports "updated" rather than refusing.
"""

from pas.plugins.identity.core.pas import EXTRACTOR
from pas.plugins.identity.core.pas import PLUGIN_ID as CORE_PLUGIN_ID
from pas.plugins.identity.core.subscribers import get_profile
from plone import api

import pytest


PROVIDER = "oidc-generic"
SUBJECT = "CgVlcmljbxIFbG9jYWw"

CLAIMS = {
    "fullname": "Érico Andrei",
    "email": "erico@plone.org",
    "email_verified": True,
    "picture_url": "",
    "username": "ericof",
    "raw": {},
}


class TestAFederatedFirstLogin:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.plugin = acl_users[CORE_PLUGIN_ID]

    def authenticate(self) -> str:
        """Run one login, as PAS does.

        :returns: The Plone userid it resolved to.
        """
        userid, _ = self.plugin.authenticateCredentials({
            "extractor": EXTRACTOR,
            "provider": PROVIDER,
            "subject": SUBJECT,
            "claims": CLAIMS,
        })
        return userid

    def test_the_profile_is_the_only_record(self):
        """The defect: a ``source_users`` row beside the Profile, on every
        federated first login.

        Asserted on ``getUserIds``, which is what the ZMI page lists.
        ``getUserById`` answers for a principal that manager does not hold,
        so it cannot show an absence.
        """
        userid = self.authenticate()

        assert get_profile(userid) is not None
        assert userid not in self.acl_users.source_users.getUserIds()

    def test_the_user_is_retrievable(self):
        """Declining the row is only right if the person is still a user:
        the layer's plugin enumerates the Profile."""
        userid = self.authenticate()

        assert api.user.get(userid=userid) is not None

    def test_the_fullname_comes_from_the_profile(self):
        """And through the ordinary API, not by reading the object. A user
        whose only record is content still has to answer like a user."""
        userid = self.authenticate()

        assert api.user.get(userid=userid).getProperty("fullname") == "Érico Andrei"

    def test_a_second_login_finds_the_same_user(self):
        first = self.authenticate()
        second = self.authenticate()

        assert first == second
        assert second not in self.acl_users.source_users.getUserIds()
