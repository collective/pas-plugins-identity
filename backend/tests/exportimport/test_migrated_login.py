"""The question a migration is actually asked: does signing in afterwards
land on the account that was imported?

Everything else in this package tests that a document goes in and comes out.
None of it tests the thing an operator cares about, which happens *after* the
import and involves neither the exporter nor the importer: a real person
authenticating at the provider, and either arriving in the account that was
migrated for them or being handed a brand-new one beside it.

The join is ``(provider, subject)``. Both halves have to survive:

``subject``
    ``pas.plugins.authomatic`` stores the provider's own user id, and for
    Google that is the ``sub`` claim -- which is exactly what this package's
    Google driver reads (``subject_keys = ("sub",)``). Verified against a real
    authomatic 2.0.0 store: 17 identities, and the stored subject equalled the
    ``sub`` claim in all 17.

``provider``
    authomatic's provider *name* -- the key in its ``json_config`` -- becomes
    this package's provider *id*. Nothing enforces that, because nothing can:
    the provider is configured by an operator in a control panel, after the
    import, in a different site. Rename it and every migrated account is
    orphaned in favour of a new one, silently and at first login. That is what
    the second class here is for.
"""

from . import ADDRESS
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.pas import EXTRACTOR
from pas.plugins.identity.core.pas import PLUGIN_ID as CORE_PLUGIN_ID
from pas.plugins.identity.core.subscribers import get_profile
from pas.plugins.identity.exportimport import convert_authomatic
from pas.plugins.identity.exportimport import import_site
from pas.plugins.identity.exportimport.authomatic import SOURCE
from plone import api

import pytest


#: A Google ``sub``, which is what authomatic stores as the subject.
SUB = "112118000000000007423"

#: An opaque userid, as every one of authomatic's four factories produces.
USERID = "05963b92-1f0e-4f21-9a3f-8b5c2d7e4a10"

#: Shaped after a real dump: Google's own claim names, not Plone's.
DUMP = {
    "source": SOURCE,
    "users": [
        {
            "userid": USERID,
            "identities": [{"provider": "google", "subject": SUB}],
            "properties": {
                "sub": SUB,
                "name": "Érico Andrei",
                "email": ADDRESS,
                "email_verified": True,
                "given_name": "Érico",
                "family_name": "Andrei",
                "hd": "example.com",
            },
        }
    ],
    "groups": [{"group_id": "Team", "title": "Team", "members": [USERID, "admin"]}],
}


def claims() -> dict:
    """Return what the Google driver would hand the plugin at login.

    :returns: Normalized claims.
    """
    return {
        "fullname": "Érico Andrei",
        "email": ADDRESS,
        "email_verified": True,
        "emails": [{"address": ADDRESS, "verified": True}],
        "raw": {},
    }


class TestSigningInAfterAMigration:
    """The provider is named exactly as authomatic named it."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users) -> None:
        self.portal = portal
        self.plugin = acl_users[CORE_PLUGIN_ID]
        set_providers([
            ProviderConfig(provider_id="google", driver_id="google", title="Google")
        ])
        self.result = import_site(convert_authomatic(DUMP))
        assert not self.result.refused

    def authenticate(self, provider: str = "google") -> str:
        """Sign in the way the callback service does.

        :param provider: Provider id presented by the login.
        :returns: The userid PAS resolved to.
        """
        userid, _ = self.plugin.authenticateCredentials({
            "extractor": EXTRACTOR,
            "provider": provider,
            "subject": SUB,
            "claims": claims(),
        })
        return userid

    def test_the_login_lands_on_the_imported_account(self):
        """The whole point. Verified against a real authomatic store as well:
        17 of 17 people arrived in the account migrated for them."""
        assert self.authenticate() == USERID

    def test_no_second_account_is_minted(self):
        """The failure this prevents is not an error -- it is a duplicate."""
        self.authenticate()

        assert len(self.plugin.store.userids()) == 1

    def test_the_profile_is_the_migrated_one(self):
        """Not merely a userid: the object carrying their name."""
        profile = get_profile(self.authenticate())

        assert profile.fullname == "Érico Andrei"

    def test_the_group_membership_survives_the_login(self):
        """A login reconciles federated groups, and must not take away one
        the migration granted -- no provider granted it, so nothing may."""
        profile = get_profile(self.authenticate())

        assert profile.group_ids == ("Team",)

    def test_they_are_an_ordinary_plone_user(self):
        assert api.user.get(userid=self.authenticate()) is not None

    def test_a_member_who_is_not_in_the_dump_is_not_invented(self):
        """``admin`` is in the group's members and is the Zope root account,
        not an authomatic identity. It has no user record to attach to."""
        assert self.result.users == [USERID]


class TestWhenTheProviderWasRenamed:
    """The one thing that has to match, and the one thing nothing checks."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users) -> None:
        self.portal = portal
        self.plugin = acl_users[CORE_PLUGIN_ID]
        set_providers([
            ProviderConfig(
                provider_id="google-workspace",
                driver_id="google",
                title="Google Workspace",
            )
        ])
        import_site(convert_authomatic(DUMP))

    def test_the_migrated_account_is_orphaned(self):
        """Same person, same Google account, same subject -- and a new userid,
        because the left half of the identity key is a different string.

        Reproduced against the real dump: renaming the provider turned 17
        migrated accounts into 17 new ones and left 34 userids in the store.
        """
        userid, _ = self.plugin.authenticateCredentials({
            "extractor": EXTRACTOR,
            "provider": "google-workspace",
            "subject": SUB,
            "claims": claims(),
        })

        assert userid != USERID
        assert len(self.plugin.store.userids()) == 2

    def test_the_migrated_profile_is_left_behind_untouched(self):
        """It is not corrupted, which is what makes this hard to notice: the
        migrated account still exists, still has the name and the group, and
        simply belongs to nobody who can sign in."""
        self.plugin.authenticateCredentials({
            "extractor": EXTRACTOR,
            "provider": "google-workspace",
            "subject": SUB,
            "claims": claims(),
        })
        orphan = get_profile(USERID)

        assert orphan is not None
        assert orphan.fullname == "Érico Andrei"
        assert orphan.group_ids == ("Team",)
