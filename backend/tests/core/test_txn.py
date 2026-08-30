"""What a login leaves in the transaction's own record.

The undo log is the one account of a login that survives the request, and
before this it said nothing: ``recordMetaData`` runs before the view, and the
view is where a federated login authenticates, so the transaction that mints an
account committed as a bare path with no user.

These drive the real plugin rather than the helpers, because the fact under
test is *that the login path calls them at all* -- a note module nothing
invokes is the same as no note module.
"""

from pas.plugins.identity.core import txn
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.pas import EXTRACTOR
from pas.plugins.identity.core.pas import PLUGIN_ID as CORE_PLUGIN_ID
from pas.plugins.identity.core.subscribers import get_profile

import pytest
import transaction


PROVIDER = "oidc-generic"
SUBJECT = "CgVlcmljbxIFbG9jYWw"
CLAIMS = {
    "fullname": "Érico Andrei",
    "email": "erico@plone.org",
    "email_verified": True,
    # ``emails`` rather than ``email_verified`` alone: that is what
    # ``verified_by_provider`` reads, and adoption by address is what makes
    # "new identity" without "new user" reachable at all.
    "emails": [{"address": "erico@plone.org", "verified": True}],
    "username": "ericof",
    "raw": {},
}


def description() -> str:
    """Return the current transaction's description.

    :returns: The note text.
    """
    return transaction.get().description or ""


def forget_notes() -> None:
    """Clear the description without aborting.

    ``transaction.abort()`` would clear it and would also roll the login back,
    so a test measuring a *second* login would be measuring a first one.
    """
    transaction.get().description = ""


def identity_lines() -> list[str]:
    """Return only the lines this package added.

    :returns: The notes, with the prefix stripped.
    """
    return [
        line[len(txn.PREFIX) :].strip()
        for line in description().splitlines()
        if line.startswith(txn.PREFIX)
    ]


class TestTheNoteHelpers:
    """The module on its own, where the shapes are easy to state."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_a_note_is_prefixed(self):
        """So an operator can tell our lines from Zope's path."""
        txn.note("something happened")

        assert description() == "identity: something happened"

    def test_notes_append_rather_than_replace(self):
        """``Transaction.note`` appends, which is what lets each fact be its
        own line without any one caller owning the whole description."""
        txn.note("first")
        txn.note("second")

        assert identity_lines() == ["first", "second"]

    def test_a_note_does_not_join_the_transaction(self):
        """The whole design rests on this. A note is an attribute of the
        ``Transaction`` object, not of a resource manager, so annotating a
        request that wrote nothing must leave it writing nothing -- otherwise
        this module would turn every read into a write."""
        transaction.abort()
        connection = self.portal._p_jar

        txn.note("a note, and nothing else")
        txn.attribute_to("somebody")

        assert connection._registered_objects == []

    @pytest.mark.parametrize(
        "already,expected",
        [
            ("", True),
            ("plone None", True),
            ("None", True),
            ("plone someone-else", False),
        ],
        ids=["empty", "anonymous-request", "bare-None", "a-real-user"],
    )
    def test_attribution_defers_to_a_user_already_named(self, already, expected):
        """``recordMetaData`` writes the string ``"None"`` for an anonymous
        request, so an empty field is not the only way to be unattributed --
        and a request that really was made by somebody keeps its own name."""
        transaction.get().user = already

        txn.attribute_to("the-new-user")

        assert ("the-new-user" in transaction.get().user) is expected


class TestWhatALoginRecords:
    """Through the plugin, which is the only thing that proves it is wired."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users) -> None:
        self.portal = portal
        self.plugin = acl_users[CORE_PLUGIN_ID]
        set_providers([
            ProviderConfig(
                provider_id=PROVIDER,
                driver_id="oidc-generic",
                title="Dex",
                # Adoption by address is what tells "new identity" apart from
                # "new user", and it only happens for a provider the site
                # takes the word of.
                config={
                    "auto_link_by_email": True,
                    "trust_email_verification": True,
                },
            )
        ])
        forget_notes()

    def authenticate(self, subject: str = SUBJECT) -> str:
        """Run one login, as PAS does.

        :param subject: Provider-side subject.
        :returns: The userid.
        """
        userid, _ = self.plugin.authenticateCredentials({
            "extractor": EXTRACTOR,
            "provider": PROVIDER,
            "subject": subject,
            "claims": CLAIMS,
        })
        return userid

    def test_a_first_login_records_the_login_and_the_profile(self):
        """Both facts, each on its own line, in the order they happened."""
        userid = self.authenticate()

        assert identity_lines() == [
            f"login {userid} via {PROVIDER} (new user, new identity)",
            f"profile created at {'/'.join(get_profile(userid).getPhysicalPath())}",
        ]

    def test_a_later_login_records_only_the_login(self):
        """Nothing is created, so nothing claims to have been."""
        userid = self.authenticate()
        forget_notes()

        self.authenticate()

        assert identity_lines() == [f"login {userid} via {PROVIDER}"]

    def test_the_provider_is_named(self):
        """The one piece of context that says *how* somebody got in. It is a
        provider id -- site configuration -- rather than anything about them."""
        self.authenticate()

        assert f"via {PROVIDER}" in description()

    def test_the_note_carries_no_personal_data(self):
        """The undo log is not purged short of packing the storage, which
        makes it the worst place to put an address. The userid is opaque and
        the subject belongs to the provider; neither goes in."""
        self.authenticate()

        assert CLAIMS["email"] not in description()
        assert CLAIMS["fullname"] not in description()
        assert CLAIMS["username"] not in description()
        assert SUBJECT not in description()

    def test_the_transaction_is_attributed_to_the_user(self):
        """At traversal time they were anonymous, which is the whole reason
        Zope could not do this."""
        userid = self.authenticate()

        assert transaction.get().user.endswith(userid)

    def test_an_identity_adopted_by_email_is_not_reported_as_a_new_user(self):
        """A second provider for somebody already here links an identity
        without minting an account, and the note has to tell them apart."""
        first = self.authenticate()
        forget_notes()

        second = self.plugin.authenticateCredentials({
            "extractor": EXTRACTOR,
            "provider": PROVIDER,
            "subject": "a-different-subject",
            "claims": CLAIMS,
        })[0]

        assert second == first
        assert identity_lines()[0] == f"login {first} via {PROVIDER} (new identity)"
