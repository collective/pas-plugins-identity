"""A migrated account reaches the enrichers with the provider's payload.

An import fires ``IdentityLinked``, and its subscriber runs the site's
installed ``IProfileEnricher`` utilities against the claims the import wrote.
That already worked. What did not is what those claims contained: both
authomatic paths built a snapshot with ``"raw": {}``, so every enricher ran
against an empty document, wrote nothing, and reported nothing wrong. The
Profiles came out of the migration missing exactly the fields a site had
installed an enricher to fill -- silently, which is the part that makes it
worth a test rather than a fix.

``raw`` is the whole contract. The property map deliberately refuses a
structured claim (``_scalar`` reads a list as an absent claim, so an OIDC
``address`` object never lands in a location field as a repr), and an enricher
is what a site has instead. Handing it nothing to read leaves it no way to do
its job.

The scrubbing is asserted here too, and belongs with it: a snapshot is stored
on the identity record and written out again by the exporter, so the fix that
carries the payload in is also the one that could carry a token in.
"""

from . import ADDRESS
from . import SUBJECT
from . import USERID
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.interfaces import IProfileEnricher
from pas.plugins.identity.core.subscribers import get_profile
from pas.plugins.identity.exportimport import import_site
from pas.plugins.identity.exportimport.authomatic import convert_authomatic
from pas.plugins.identity.exportimport.authomatic import SOURCE
from zope.component import getGlobalSiteManager
from zope.interface import implementer

import pytest


#: The provider the dump names. A real id rather than the shared constant,
#: because ``_check_providers`` refuses a document naming one the site has not
#: configured, and this module configures it below.
PROVIDER = "github"

#: authomatic's serialized ``Credentials``: the account's access and refresh
#: tokens, which its ``User.to_dict()`` puts on every stored identity.
CREDENTIALS = "1|2|ya29.a0AfH6SMBnotarealtoken"


def dump(**properties) -> dict:
    """Return an authomatic dump in GitHub's own vocabulary.

    What the documented extraction produces: the provider's document merged
    into the stored identity, so the raw API fields sit beside authomatic's
    normalized ones.

    :param properties: Property keys to add or replace.
    :returns: The dump.
    """
    return {
        "source": SOURCE,
        "users": [
            {
                "userid": USERID,
                "identities": [{"provider": PROVIDER, "subject": SUBJECT}],
                "properties": {
                    "login": "ericof",
                    "name": "Érico Andrei",
                    "email": ADDRESS,
                    "bio": "Writes Python for a living.",
                    "blog": "https://erico.example.com",
                    "twitter_username": "ericof",
                    **properties,
                },
            }
        ],
    }


@implementer(IProfileEnricher)
class SocialLinks:
    """The case the extension point exists for: a list field, from keys the
    property map has no name for."""

    def __init__(self):
        self.calls = []

    def enrich(self, profile, claims, provider, memory):
        raw = claims.get("raw") or {}
        self.calls.append(raw)
        links = []
        if handle := raw.get("twitter_username"):
            links.append(f"https://twitter.com/{handle}")
        if blog := raw.get("blog"):
            links.append(blog)
        if not links or memory.get("written") == links:
            return []
        profile.social_links = links
        memory["written"] = list(links)
        return ["social_links"]


@pytest.fixture
def enricher():
    """Register one enricher for a test and take it away after.

    A utility left in the global registry changes every later test in the run,
    and the failure surfaces somewhere else entirely.

    :returns: The enricher, with the payloads it was handed.
    """
    gsm = getGlobalSiteManager()
    utility = SocialLinks()
    gsm.registerUtility(utility, IProfileEnricher, name="test.social")
    yield utility
    gsm.unregisterUtility(utility, IProfileEnricher, name="test.social")


class TestTheConversionCarriesThePayload:
    """Before any site is involved: what the converted document holds."""

    def claims(self, **properties) -> dict:
        """Convert a dump and return its one identity's claims.

        :param properties: Property keys to add or replace.
        :returns: The claims snapshot.
        """
        document = convert_authomatic(dump(**properties))
        return document["users"][0]["identities"][0]["claims"]

    def test_the_payload_is_carried(self):
        """The fix. It was ``{}``, which is why every enricher wrote
        nothing."""
        assert self.claims()["raw"]["twitter_username"] == "ericof"

    def test_a_key_no_field_maps_is_carried_too(self):
        """The point of ``raw``: the map moves the four keys this package has
        a field for, and an enricher is for everything else."""
        assert self.claims()["raw"]["bio"] == "Writes Python for a living."

    def test_the_normalized_claims_are_unchanged(self):
        """The fix adds a key; it does not restate the address facts."""
        claims = self.claims()

        assert claims["email"] == ADDRESS
        assert claims["email_verified"] is False

    def test_a_credential_in_the_dump_does_not_survive(self):
        """A document is a file that gets copied around, and an extraction
        script that copied a whole token response into ``properties`` is a
        likelier mistake than a malicious one."""
        document = convert_authomatic(dump(credentials=CREDENTIALS))

        assert CREDENTIALS not in str(document)

    def test_claims_the_dump_states_itself_are_scrubbed_too(self):
        """A dump may carry its own snapshot per identity, and that branch is
        preferred over the one built from ``properties``. It gets the same
        treatment: the extraction script is not ours either way."""
        raw = dump()
        raw["users"][0]["identities"][0]["claims"] = {
            "email": ADDRESS,
            "raw": {"bio": "Kept.", "access_token": CREDENTIALS},
        }

        document = convert_authomatic(raw)
        claims = document["users"][0]["identities"][0]["claims"]

        assert claims["raw"] == {"bio": "Kept."}
        assert CREDENTIALS not in str(document)


class TestTheImportReachesTheEnricher:
    """The end of the flow, through the real importer and the real subscriber."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin) -> None:
        self.portal = portal
        self.plugin = plugin
        set_providers([
            ProviderConfig(
                provider_id=PROVIDER,
                driver_id="github",
                title="GitHub",
                enabled=True,
            )
        ])

    def run_import(self, **properties):
        """Convert a dump and import it.

        :param properties: Property keys to add or replace.
        :returns: The importer's result.
        """
        return import_site(convert_authomatic(dump(**properties)))

    def test_the_user_arrives(self):
        """The control. Everything below is worthless if the import failed."""
        result = self.run_import()

        assert result.users == [USERID]
        assert result.refusals == []

    def test_the_enricher_receives_the_payload(self, enricher):
        """The fix, at the far end of the flow it has to survive."""
        self.run_import()

        assert enricher.calls, "the enricher was never called at all"
        assert enricher.calls[0]["twitter_username"] == "ericof"

    def test_the_list_field_is_written(self, enricher):
        """What the site installed the enricher to do, and what a migration
        was quietly not doing."""
        self.run_import()

        profile = get_profile(USERID)

        assert profile.social_links == [
            "https://twitter.com/ericof",
            "https://erico.example.com",
        ]

    def test_no_credential_reaches_the_stored_identity(self, enricher):
        """``raw`` is persisted on the identity record and re-exported, so
        this is the assertion that keeps the fix from becoming a leak."""
        self.run_import(credentials=CREDENTIALS)

        record = self.plugin.store.get(PROVIDER, SUBJECT)

        assert CREDENTIALS not in str(dict(record.claims))
