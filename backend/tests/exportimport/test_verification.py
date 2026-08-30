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
fact this site established. A dump cannot grant itself trust.

Who decides is deliberately two questions, not one. A site that believes the
provider at a login believes the same claim in a document, through the
ordinary event contract and with nothing asked of the operator. A site that
does *not* may still want the addresses its old site had already collected --
which is a decision about history rather than about every future sign-in, and
is asked for per run as ``trust_verified_emails``. Reusing
``trust_email_verification`` for both would mean switching a login policy on,
importing, and remembering to switch it back, with a window in which real
logins are judged by the temporary setting and nothing reporting it if the
last step is forgotten (Érico, 2026-08-30).
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
from pas.plugins.identity.core.verification import trusts_verification
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

    def test_the_flag_accepts_them(self):
        """The point of the whole thing: 17 people who signed in with Google
        yesterday should not be strangers to their own addresses today."""
        provider(trusts=False)

        import_site(convert_authomatic(dump()), trust_verified_emails=True)

        assert get_profile(USERID).verified_emails == (ADDRESS,)

    def test_without_the_flag_an_untrusted_provider_is_not_believed(self):
        """The default. A dump cannot grant itself trust, and importing one
        is not a reason to start believing a provider."""
        provider(trusts=False)

        import_site(convert_authomatic(dump()))

        assert get_profile(USERID).verified_emails == ()

    def test_a_trusted_provider_needs_no_flag(self):
        """A site that already believes this provider at a login believes the
        same claim in a document, through the ordinary event contract."""
        provider(trusts=True)

        import_site(convert_authomatic(dump()))

        assert get_profile(USERID).verified_emails == (ADDRESS,)

    def test_the_flag_does_not_change_the_login_policy(self):
        """The whole reason it is a flag. Reusing
        ``trust_email_verification`` would mean switching a site's login
        policy on, importing, and remembering to switch it back."""
        provider(trusts=False)

        import_site(convert_authomatic(dump()), trust_verified_emails=True)

        assert trusts_verification(PROVIDER) is False

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
        reads the flag -- and the flag says "believe what the dump claims",
        never "call everything verified"."""
        provider(trusts=False)

        import_site(
            convert_authomatic(dump(verified=claimed)), trust_verified_emails=True
        )

        assert get_profile(USERID).verified_emails == ()

    def test_a_trusted_provider_records_through_the_event_contract(self):
        """Without the flag the importer writes nothing itself: ``link`` fires
        ``IdentityLinked`` and the subscriber answers it the way it answers a
        login, which is why supplying the claims was the whole fix."""
        provider(trusts=True)

        result = import_site(convert_authomatic(dump()))

        assert result.identities == [(PROVIDER, SUBJECT, USERID)]
        assert self.plugin.store.userid_for(EMAIL_PROVIDER, ADDRESS) == USERID

    def test_the_flag_reports_what_it_recorded(self):
        """This path *is* the importer acting, so it says so. Recording an
        address as proved is not a small thing to do silently."""
        provider(trusts=False)

        result = import_site(convert_authomatic(dump()), trust_verified_emails=True)

        assert (EMAIL_PROVIDER, ADDRESS, USERID) in result.identities

    @pytest.mark.parametrize("flag", [True, False], ids=["with-flag", "without"])
    def test_a_dry_run_records_nothing(self, flag):
        provider(trusts=True)

        import_site(
            convert_authomatic(dump()), dry_run=True, trust_verified_emails=flag
        )

        assert get_profile(USERID) is None
        assert self.plugin.store.userid_for(EMAIL_PROVIDER, ADDRESS) is None
