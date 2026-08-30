"""Which store a *first* login writes to, on a site whose users are Profiles.

:mod:`tests.core.test_first_login` fires the events instead of logging in,
deliberately, because the subscriber is built against the event contract and a
test that logged in would be testing core's flow twice. This module is the one
place that rule has to be broken, and it is worth saying why: the bug these
tests exist for was not in either half. Both functions were correct. They were
called one step too early, and no test that fires the event itself can see the
order core calls things in.

The plugin made two writes at the end of a login -- the provider's mapped
claims, and the provider's avatar -- and both were fallbacks. Each asked
whether somebody else owned this user's data and wrote into
``portal_memberdata`` only when the answer was no.

On a first login both questions used to be asked before the Profile existed,
because the Profile is minted by a subscriber to the event core fires *after*
authenticating. So both were told "nobody owns this user", both wrote to
``portal_memberdata``, and the Profile -- which every reader consults first --
was left empty on the one login where it was being created.

Neither self-corrected. The property map skipped a field that already held a
value, and the avatar is refetched only when the provider changes its URL. One
badly-timed answer was permanent, which is what these tests exist to prevent
coming back.

Only the avatar is written here now: the mapped-claims fallback was removed
once it became unreachable, so the assertion below that nothing lands in
``portal_memberdata`` is about there being no such writer at all rather than
about it declining. Worth keeping either way -- it is the observable fact,
and it is what would notice a fallback coming back.

They drive the real plugin rather than the helpers underneath it: the bug was
entirely in the order two correct functions were called in, so a test that
calls either one directly cannot see it.
"""

from pas.plugins.identity.core import portraits
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.pas import EXTRACTOR
from pas.plugins.identity.core.pas import PLUGIN_ID as CORE_PLUGIN_ID
from pas.plugins.identity.core.subscribers import get_profile
from plone import api

import pytest


PROVIDER = "oidc-generic"
SUBJECT = "CgVlcmljbxIFbG9jYWw"
PICTURE_URL = "https://cdn.example.org/avatar.png"

#: The smallest valid PNG, so a test never carries a binary fixture file.
PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00"
    b"\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\n"
    b"IDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00"
    b"\x00IEND\xaeB`\x82"
)

CLAIMS = {
    "fullname": "Érico Andrei",
    "email": "erico@plone.org",
    "email_verified": True,
    "picture_url": PICTURE_URL,
    "username": "ericof",
    "raw": {"profile": "https://example.org/~ericof"},
}


def member_portrait(userid: str):
    """Return the stored member portrait, or ``None`` for the default.

    :param userid: The user to look at.
    :returns: The image, or ``None``.
    """
    from Products.PlonePAS.tools.membership import default_portrait

    portrait = api.portal.get_tool("portal_membership").getPersonalPortrait(userid)
    if portrait is None or portrait.getId() == default_portrait.split("/")[-1]:
        return None
    return portrait


class TestTheFirstLoginWritesToTheClaimedStore:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, monkeypatch) -> None:
        self.portal = portal
        self.plugin = acl_users[CORE_PLUGIN_ID]
        set_providers([
            ProviderConfig(
                provider_id=PROVIDER,
                driver_id="oidc-generic",
                title="Dex",
                propertymap={"profile": "home_page"},
            )
        ])
        api.portal.set_registry_record(portraits.ENABLED_RECORD, True)
        # No network, and no guard to satisfy: the fetch is not what is
        # under test here, only where its result is put.
        monkeypatch.setattr(portraits, "_fetch", lambda url, allow_http=False: PNG)

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

    def test_the_login_mints_a_profile(self):
        """The premise the rest of the module rests on."""
        assert get_profile(self.authenticate()) is not None

    def test_the_mapped_claim_lands_on_the_profile(self):
        """Which it did before the fix too -- the subscriber applies the
        same map from the event. This is the premise, not the symptom."""
        profile = get_profile(self.authenticate())

        assert profile.home_page == "https://example.org/~ericof"

    def test_the_mapped_claim_does_not_also_land_in_memberdata(self):
        """The symptom. Asked before the Profile existed, the ownership
        question answered "nobody", so core wrote a second copy that no
        reader consults and no later login corrects. Nothing writes it now;
        this is what says so from outside.

        Read through ``mutable_properties`` rather than through the member:
        the member merges every sheet, so it reports the Profile's value and
        cannot tell the two stores apart -- which is what let this hide.
        """
        userid = self.authenticate()
        member = api.user.get(userid=userid).getUser()
        sheet = self.portal.acl_users.mutable_properties.getPropertiesForUser(member)

        assert not sheet.getProperty("home_page", "")

    def test_the_avatar_lands_on_the_profile(self):
        """Same ordering, the other writer."""
        profile = get_profile(self.authenticate())

        assert profile.image is not None
        assert profile.image.data == PNG

    def test_the_member_portrait_is_left_empty(self):
        """One store per user. Two pictures are two things to disagree."""
        userid = self.authenticate()

        assert member_portrait(userid) is None

    def test_the_reader_finds_the_picture(self):
        """End to end: what ``@users`` reports after a single login."""
        from pas.plugins.identity.core.serializers.user import portrait_of

        profile = get_profile(userid := self.authenticate())

        assert portrait_of(userid) == f"{profile.absolute_url()}/@@images/image"

    def test_a_second_login_changes_nothing(self):
        """The fix must not turn every login into a second write."""
        self.authenticate()
        userid = self.authenticate()

        assert get_profile(userid).image.data == PNG
        assert member_portrait(userid) is None
