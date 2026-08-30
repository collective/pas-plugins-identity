"""Refusing an import whose provider names no login will ever match.

The identity key is ``(provider, subject)``. The subject survives a migration
untouched, because it belongs to the provider. The name does not: it is
``pas.plugins.authomatic``'s ``json_config`` key on one side and a string an
operator typed into a control panel on the other, in a different site, after
the import.

Getting it wrong raises nothing. The import reports success, and then every
migrated person signs in, matches no identity, and is handed a second account
beside the one waiting for them -- which keeps their name and their groups and
belongs to nobody who can sign in. ``test_migrated_login.py`` holds that
outcome in place; this module is the guard that stops it happening.
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

import pytest


def document(provider: str = PROVIDER) -> dict:
    """Return a document naming one provider.

    :param provider: The provider id its identity carries.
    :returns: The document.
    """
    return {
        "version": DOCUMENT_VERSION,
        "groups": [],
        "users": [
            {
                "userid": USERID,
                "login": "ericof",
                "emails": [ADDRESS],
                "fullname": "Érico Andrei",
                "identities": [
                    {"provider": provider, "subject": SUBJECT, "claims": {}}
                ],
            }
        ],
    }


class TestTheProviderNamesAreChecked:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users) -> None:
        self.portal = portal

    def configure(self, *provider_ids: str) -> None:
        """Configure the site with these providers and no others.

        :param provider_ids: The ids to configure.
        """
        set_providers([
            ProviderConfig(provider_id=pid, driver_id="oidc-generic", title=pid)
            for pid in provider_ids
        ])

    def test_a_matching_name_imports(self):
        """The premise: the check must not stand in the way of the ordinary
        case."""
        self.configure(PROVIDER)

        result = import_site(document())

        assert not result.refused
        assert result.users == [USERID]

    def test_an_unknown_name_is_refused(self):
        self.configure("some-other-provider")

        result = import_site(document())

        assert result.refused
        assert PROVIDER in " ".join(result.refusals)

    def test_a_site_with_no_providers_at_all_is_refused(self):
        """The commonest way to hit this: import into a site nobody has
        configured yet."""
        self.configure()

        result = import_site(document())

        assert result.refused

    def test_nothing_is_written_when_it_refuses(self):
        """A refusal that had already created half the accounts would be
        worse than no check, because the second run would find them there."""
        self.configure("some-other-provider")

        import_site(document())

        assert get_profile(USERID) is None

    def test_a_dry_run_refuses_too(self):
        """It is the run an operator does *first*, so it is the one that has
        to say so."""
        self.configure("some-other-provider")

        result = import_site(document(), dry_run=True)

        assert result.refused

    def test_the_refusal_names_the_configured_providers(self):
        """An operator reading it should not have to go and look."""
        self.configure("github", "some-other-provider")

        message = " ".join(import_site(document()).refusals)

        assert "'github'" in message
        assert "'some-other-provider'" in message

    def test_a_difference_of_case_is_called_out(self):
        """The likely mistake, and the one hardest to see: the two strings
        look identical in a control panel listing."""
        self.configure("Oidc-Generic")

        message = " ".join(import_site(document("oidc-generic")).refusals)

        assert "spelled differently" in message
        assert "'Oidc-Generic'" in message

    def test_only_the_missing_names_are_reported(self):
        """A document using two providers, one of which is configured."""
        self.configure(PROVIDER)
        doc = document()
        doc["users"][0]["identities"].append({
            "provider": "github",
            "subject": "1234",
            "claims": {},
        })

        message = " ".join(import_site(doc).refusals)

        assert "'github'" in message
        assert f"no provider named '{PROVIDER}'" not in message

    def test_a_document_with_no_identities_is_not_refused(self):
        """Groups, or profiles nobody signs in to. There is no join to get
        wrong, so there is nothing to check."""
        self.configure()
        doc = document()
        doc["users"][0]["identities"] = []

        result = import_site(doc)

        assert not result.refused
        assert result.users == [USERID]

    def test_a_disabled_provider_still_counts(self):
        """Being switched off does not break the join, and an operator may
        reasonably import before switching it on."""
        set_providers([
            ProviderConfig(
                provider_id=PROVIDER,
                driver_id="oidc-generic",
                title="Dex",
                enabled=False,
            )
        ])

        result = import_site(document())

        assert not result.refused


class TestTheEscapeHatch:
    """For the deliberate order: import first, configure afterwards."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users) -> None:
        self.portal = portal
        set_providers([])

    def test_it_imports_when_asked_to(self):
        result = import_site(document(), allow_unknown_providers=True)

        assert not result.refused
        assert result.identities == [(PROVIDER, SUBJECT, USERID)]

    def test_the_identity_is_still_written(self):
        """The point of the flag: the join is stored now and becomes usable
        the moment the provider is configured under the right name."""
        import_site(document(), allow_unknown_providers=True)
        plugin = self.portal.acl_users["identity"]

        assert plugin.store.userid_for(PROVIDER, SUBJECT) == USERID
