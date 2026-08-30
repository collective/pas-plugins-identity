"""Writing a document into a site that does not already have it.

The round-trip test next door exports and re-imports the same site, so every
object it writes already exists and the importer only ever takes the update
path. This module is the other one: a hand-written document, a site holding
none of it, and the question of whether the accounts arrive.
"""

from . import ADDRESS
from . import PROVIDER
from . import SUBJECT
from . import USERID
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.subscribers import get_profile
from pas.plugins.identity.exportimport import import_site
from pas.plugins.identity.exportimport.schema import DOCUMENT_VERSION
from plone import api

import pytest


def document(**overrides) -> dict:
    """Return a minimal valid document.

    :param overrides: Keys to replace at the top level.
    :returns: The document.
    """
    return {
        "version": DOCUMENT_VERSION,
        "groups": [
            {"group_id": "site-editors", "title": "Site Editors", "group_ids": []}
        ],
        "users": [
            {
                "userid": USERID,
                "login": "ericof",
                "emails": [ADDRESS],
                "fullname": "Érico Andrei",
                "location": "Berlin",
                "group_ids": ["site-editors"],
                "identities": [
                    {
                        "provider": PROVIDER,
                        "subject": SUBJECT,
                        "claims": {"email": ADDRESS},
                        "groups": [],
                    }
                ],
            }
        ],
        **overrides,
    }


class TestRestoringIntoAnEmptySite:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin) -> None:
        self.portal = portal
        self.plugin = plugin
        # The importer refuses a document naming a provider this site does
        # not have; that guard has its own module, and these are about the
        # writing that happens once it is satisfied.
        set_providers([
            ProviderConfig(provider_id=PROVIDER, driver_id="oidc-generic", title="Dex")
        ])

    def test_the_user_arrives(self):
        """The point of the whole package."""
        result = import_site(document())

        assert not result.refused
        assert result.users == [USERID]
        assert get_profile(USERID) is not None

    def test_the_userid_travels_verbatim(self):
        """Every local role and ownership in the target site is written
        against it, so an import that minted a new one would produce a site
        full of content owned by nobody -- silently."""
        import_site(document())

        assert get_profile(USERID).userid == USERID

    def test_the_user_is_a_plone_user(self):
        """Not merely an object: the account has to answer the ordinary API,
        or nothing has been restored."""
        import_site(document())

        assert api.user.get(userid=USERID) is not None

    def test_the_identity_resolves(self):
        """Signing in with the provider has to reach the restored account."""
        import_site(document())

        assert self.plugin.store.userid_for(PROVIDER, SUBJECT) == USERID

    def test_the_group_arrives_and_the_user_is_in_it(self):
        """Groups are written first for exactly this reason."""
        import_site(document())

        assert result_groups(self.portal) == ["site-editors"]
        assert get_profile(USERID).group_ids == ("site-editors",)

    def test_a_dry_run_writes_nothing(self):
        """Not "writes and rolls back" -- the write is never attempted."""
        result = import_site(document(), dry_run=True)

        assert result.dry_run
        assert result.users == [USERID]
        assert get_profile(USERID) is None


def result_groups(portal) -> list[str]:
    """Return the group ids the site holds.

    :param portal: The portal.
    :returns: The ids, sorted.
    """
    from pas.plugins.identity.core.catalog import GROUP_PORTAL_TYPE
    from pas.plugins.identity.core.catalog import query_catalog

    brains = query_catalog().unrestrictedSearchResults(portal_type=GROUP_PORTAL_TYPE)
    return sorted(brain.group_id for brain in brains)


class TestWhatItRefuses:
    """Conditions that make the whole run meaningless."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin) -> None:
        self.portal = portal
        self.plugin = plugin
        # The importer refuses a document naming a provider this site does
        # not have; that guard has its own module, and these are about the
        # writing that happens once it is satisfied.
        set_providers([
            ProviderConfig(provider_id=PROVIDER, driver_id="oidc-generic", title="Dex")
        ])

    @pytest.mark.parametrize(
        "broken,expected",
        [
            ({"version": DOCUMENT_VERSION + 1}, "version"),
            ({"version": "one"}, "integer version"),
            ({"users": "not a list"}, "'users' is not a list"),
        ],
        ids=["from-the-future", "no-version", "users-not-a-list"],
    )
    def test_a_malformed_document_is_refused(self, broken, expected):
        """Refused rather than half-applied. Guessing at a document shape
        produces a partial set of accounts, which is the outcome this whole
        package is arranged to avoid."""
        result = import_site(document(**broken))

        assert result.refused
        assert expected in " ".join(result.refusals)

    def test_a_user_with_no_userid_is_refused(self):
        """It cannot be invented, and the reason is in the message."""
        result = import_site(document(users=[{"login": "nobody"}]))

        assert result.refused
        assert "userid" in " ".join(result.refusals)

    def test_an_identity_missing_half_of_itself_is_refused(self):
        """A provider without a subject, or a subject without a provider,
        identifies nobody."""
        broken = document()
        broken["users"][0]["identities"] = [{"provider": PROVIDER}]

        result = import_site(broken)

        assert result.refused
        assert "subject" in " ".join(result.refusals)


class TestWhatItSkips:
    """One bad record must not stop the other nine hundred."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin) -> None:
        self.portal = portal
        self.plugin = plugin
        # The importer refuses a document naming a provider this site does
        # not have; that guard has its own module, and these are about the
        # writing that happens once it is satisfied.
        set_providers([
            ProviderConfig(provider_id=PROVIDER, driver_id="oidc-generic", title="Dex")
        ])

    def test_a_user_with_no_address_is_skipped_not_refused(self):
        """``emails`` is required on a Profile and ``email`` is derived from
        it, so the object cannot be created -- but the rest of the document
        still can. Inventing an address would produce an account whose owner
        cannot be reached and cannot be told why."""
        doc = document()
        doc["users"][0]["emails"] = []

        result = import_site(doc)

        assert not result.refused
        assert result.users == []
        assert "no email address" in " ".join(result.skipped)
        # The group still arrived.
        assert result.groups == ["site-editors"]

    def test_an_identity_owned_by_somebody_else_is_skipped(self):
        """The one case that must never be resolved by guessing: two people
        cannot both be the same identity, and quietly moving it is one of
        them taking the other's account."""
        self.plugin.link("somebody-else", PROVIDER, SUBJECT, {})

        result = import_site(document())

        assert not result.refused
        assert result.users == [USERID]
        assert result.identities == []
        assert "already linked to somebody-else" in " ".join(result.skipped)

    def test_the_identity_is_not_moved(self):
        """The assertion behind the skip above -- the store still says what
        it said."""
        self.plugin.link("somebody-else", PROVIDER, SUBJECT, {})

        import_site(document())

        assert self.plugin.store.userid_for(PROVIDER, SUBJECT) == "somebody-else"

    def test_an_unknown_group_is_not_created(self):
        """A group this document does not carry is one whose members and
        nesting nobody has stated; inventing it produces a grant nobody
        decided on."""
        doc = document()
        doc["users"][0]["group_ids"] = ["site-editors", "invented"]

        import_site(doc)

        assert get_profile(USERID).group_ids == ("site-editors",)
        assert result_groups(self.portal) == ["site-editors"]
