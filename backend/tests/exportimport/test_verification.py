"""Whether an address arrives proved, and who decides.

Verification is not a flag on a Profile. It is an identity in the store under
the ``email`` provider, keyed by the address -- so ``verified_addresses`` can
answer "has this site proved this mailbox belongs to this person?" with one
BTree lookup, and so a magic link and a trusted provider write the same record.

Two consequences the export and the import both have to respect.

The first is that an exported document already carries verification, as
``email`` identities among the others. Nothing has to be added for a restore to
keep it -- but the provider-name check has to know that ``email`` is not a
provider anybody configures, or it refuses every document from a site that has
ever verified an address.

The second is that a ``pas.plugins.authomatic`` dump carries something weaker:
the provider's ``email_verified`` claim, which is an assertion rather than a
fact this site established. Whether to believe it is the operator's decision,
recorded per provider as ``trust_email_verification``, and it is applied on
import exactly as it would be at a login. A dump cannot grant itself trust.
"""

from . import ADDRESS
from . import CLAIMS
from . import PROVIDER
from . import SUBJECT
from . import USERID
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from pas.plugins.identity.core.subscribers import get_profile
from pas.plugins.identity.exportimport import convert_authomatic
from pas.plugins.identity.exportimport import export_site
from pas.plugins.identity.exportimport import import_site
from pas.plugins.identity.exportimport.authomatic import SOURCE

import pytest


def dump(verified: object = True) -> dict:
    """Return an authomatic dump whose provider asserts an address.

    :param verified: What the provider says about the address.
    :returns: The dump.
    """
    return {
        "source": SOURCE,
        "users": [
            {
                "userid": USERID,
                "identities": [{"provider": PROVIDER, "subject": SUBJECT}],
                "properties": {
                    "name": "Érico Andrei",
                    "email": ADDRESS,
                    "email_verified": verified,
                },
            }
        ],
        "groups": [],
    }


def provider(trusts: bool) -> None:
    """Configure the one provider, with or without verification trust.

    :param trusts: Whether this site takes the provider's word.
    """
    set_providers([
        ProviderConfig(
            provider_id=PROVIDER,
            driver_id="oidc-generic",
            title="Dex",
            config={"trust_email_verification": trusts},
        )
    ])


class TestAnExportedDocumentKeepsVerification:
    """The restore direction, where it is already a fact this site
    established rather than something a provider said."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin, make_user) -> None:
        self.portal = portal
        self.plugin = plugin
        provider(trusts=False)
        self.profile = make_user()
        self.plugin.link(USERID, PROVIDER, SUBJECT, CLAIMS)
        self.plugin.link(USERID, EMAIL_PROVIDER, ADDRESS, {"email": ADDRESS})

    def test_the_export_carries_it(self):
        """As an ``email`` identity, which is what verification *is*."""
        identities = export_site()["users"][0]["identities"]

        assert (EMAIL_PROVIDER, ADDRESS) in [
            (i["provider"], i["subject"]) for i in identities
        ]

    def test_the_document_can_be_read_back(self):
        """``email`` is not a configured provider and never will be, so the
        provider-name check has to exempt it. Without that, every document
        from a site that has verified anything is refused."""
        result = import_site(export_site())

        assert not result.refused

    def test_the_address_is_still_verified_afterwards(self):
        import_site(export_site())

        assert get_profile(USERID).verified_emails == (ADDRESS,)


class TestAnAuthomaticDumpAsksPermission:
    """The migration direction, where it is the provider's assertion."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin) -> None:
        self.portal = portal
        self.plugin = plugin

    def test_a_trusted_provider_arrives_verified(self):
        """The point of the whole thing: 17 people who signed in with Google
        yesterday should not be strangers to their own addresses today."""
        provider(trusts=True)

        import_site(convert_authomatic(dump()))

        assert get_profile(USERID).verified_emails == (ADDRESS,)

    def test_an_untrusted_provider_does_not(self):
        """Same dump, same claim, different site policy. The operator decides,
        exactly as they do for a login."""
        provider(trusts=False)

        import_site(convert_authomatic(dump()))

        assert get_profile(USERID).verified_emails == ()

    def test_the_profile_still_has_the_address(self):
        """Not verified is not the same as not there."""
        provider(trusts=False)

        import_site(convert_authomatic(dump()))

        assert get_profile(USERID).emails == (ADDRESS,)

    @pytest.mark.parametrize(
        "claimed", [False, "true", 1, None], ids=["false", "string", "one", "absent"]
    )
    def test_only_a_literal_true_counts(self, claimed):
        """A string ``"true"`` and a ``1`` are both truthy and neither is a
        provider saying yes. The same rule as everywhere else this package
        reads the flag."""
        provider(trusts=True)

        import_site(convert_authomatic(dump(verified=claimed)))

        assert get_profile(USERID).verified_emails == ()

    def test_it_happens_through_the_event_contract(self):
        """The importer records nothing itself. ``plugin.link`` fires
        ``IdentityLinked``, and the subscriber answers it the way it answers a
        login -- which is why supplying the claims was the whole fix, and why
        a second call in the importer would have been a second path to the
        same write."""
        provider(trusts=True)

        result = import_site(convert_authomatic(dump()))

        assert result.identities == [(PROVIDER, SUBJECT, USERID)]
        assert self.plugin.store.userid_for(EMAIL_PROVIDER, ADDRESS) == USERID

    def test_a_dry_run_records_nothing(self):
        provider(trusts=True)

        import_site(convert_authomatic(dump()), dry_run=True)

        assert get_profile(USERID) is None
        assert self.plugin.store.userid_for(EMAIL_PROVIDER, ADDRESS) is None
