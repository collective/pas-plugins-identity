"""Migrating from ``pas.plugins.oidc``.

Most of these are about what the migration *refuses* to do, which is the
honest shape for this one. Reading its source established that it stores no
identity mapping at all: it derives a user id from a configurable claim,
creates a ``source_users`` account with that id, and keeps nothing else.

So the migration can only reconstruct the join on the default ``sub``
strategy, and it cannot tell which accounts came from OIDC at all. Both
limits are enforced here rather than documented and hoped for.
"""

from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.migration import oidc as migration

import pytest


@pytest.fixture
def oidc_plugin(portal, acl_users):
    """Install a real OIDC plugin, configured against an issuer.

    :param portal: The Plone site.
    :param acl_users: The site's PAS instance.
    :returns: The installed plugin.
    """
    from pas.plugins.oidc.plugins import OIDCPlugin

    acl_users._setObject("oidc", OIDCPlugin("oidc", title="Corporate SSO"))
    plugin = acl_users["oidc"]
    plugin.issuer = "https://sso.example.com/"
    plugin.client_id = "plone"
    plugin.client_secret = "shhh"
    plugin.scope = ("openid", "profile", "email")
    return plugin


@pytest.fixture
def legacy_user(acl_users):
    """Return a factory for a ``source_users`` account, as OIDC leaves one.

    :param acl_users: The site's PAS instance.
    :returns: Callable taking a userid.
    """

    def add(userid: str) -> None:
        acl_users.source_users.addUser(userid, userid, "placeholder")

    return add


class TestNothingToDo:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_refuses_without_oidc(self):
        """A site that never had it."""
        report = migration.migrate(dry_run=True)

        assert report.refused
        assert "nothing to migrate" in report.refusals[0]


class TestRefusesANonDefaultStrategy:
    """The finding that shaped this migration.

    ``pas.plugins.oidc`` never stored the subject. On the default ``sub``
    strategy the user id *is* the subject, so the join reconstructs. On any
    other, the subject is simply gone, and a migration that carried on would
    produce a join that looks right and is not -- which surfaces months later
    as somebody logging into somebody else's account.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, oidc_plugin, legacy_user, store) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.oidc_plugin = oidc_plugin
        self.legacy_user = legacy_user
        self.store = store

    def test_email_strategy_is_refused(self):
        """The most likely non-default setting."""
        self.oidc_plugin.user_property_as_userid = "email"
        self.legacy_user("alice@example.com")

        report = migration.migrate(dry_run=True)

        assert report.refused

    def test_the_refusal_explains_why(self):
        """An operator has to be able to act on it."""
        self.oidc_plugin.user_property_as_userid = "email"

        report = migration.migrate(dry_run=True)

        assert "was never stored" in report.refusals[0]
        assert "email" in report.refusals[0]

    def test_nothing_is_migrated_when_refused(self):
        """A refusal is not a partial migration."""
        self.oidc_plugin.user_property_as_userid = "email"
        self.legacy_user("alice@example.com")

        migration.migrate(dry_run=False)

        assert self.store.userid_for("oidc", "alice@example.com") is None

    def test_no_provider_is_created_when_refused(self):
        """Not even the half that would have been safe."""
        self.oidc_plugin.user_property_as_userid = "email"

        migration.migrate(dry_run=False)

        assert get_providers() == []

    def test_the_default_is_accepted(self):
        """The other half of the rule."""
        self.legacy_user("sub-alice")

        assert not migration.migrate(dry_run=True).refused


class TestDegradedSites:
    """States a half-removed installation can leave behind."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, oidc_plugin) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.oidc_plugin = oidc_plugin

    def test_missing_identity_plugin_is_refused(self):
        """Migrating onto a package that is not installed is not a migration."""
        self.acl_users._delObject(PLUGIN_ID)

        report = migration.migrate(dry_run=True)

        assert report.refused
        assert "is not installed" in report.refusals[0]

    def test_uninstalled_oidc_package_is_a_refusal(self, monkeypatch, portal):
        """No way to recognise its plugins, so nothing can be claimed.

        Unlike the authomatic case, where the identities live in the plugin's
        own BTrees and survive the package, everything here is derived from
        the plugin *class* -- so without the class there is nothing to read.
        """
        import sys

        monkeypatch.setitem(sys.modules, "pas.plugins.oidc.plugins", None)

        assert migration.migrate(dry_run=True).refused

    def test_a_site_without_source_users_claims_nothing(self):
        """Nothing to enumerate, and no reason to fail over it."""
        self.acl_users._delObject("source_users")

        report = migration.migrate(dry_run=True)

        assert report.identities == []


class TestDryRun:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, oidc_plugin, legacy_user, store) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.oidc_plugin = oidc_plugin
        self.legacy_user = legacy_user
        self.store = store

    def test_reports_what_it_would_do(self):
        """Which accounts it would claim, so a mixed site can see it."""
        self.legacy_user("sub-alice")

        report = migration.migrate(dry_run=True)

        assert ("oidc", "sub-alice", "sub-alice") in report.identities

    def test_writes_nothing(self):
        """Dry run means dry."""
        self.legacy_user("sub-alice")

        migration.migrate(dry_run=True)

        assert self.store.userid_for("oidc", "sub-alice") is None

    def test_is_the_default(self):
        """Same reasoning as the authomatic migration."""
        self.legacy_user("sub-alice")

        migration.migrate()

        assert self.store.userid_for("oidc", "sub-alice") is None


class TestMigration:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, oidc_plugin, legacy_user, store) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.oidc_plugin = oidc_plugin
        self.legacy_user = legacy_user
        self.store = store

    def test_provider_configuration_is_translated(self):
        """The half that is unambiguous: it is all on the plugin."""
        self.legacy_user("sub-alice")

        migration.migrate(dry_run=False)

        record = get_providers()[0]
        assert record.provider_id == "oidc"
        assert record.driver_id == "oidc-generic"
        assert record.config["issuer"] == "https://sso.example.com/"
        assert record.config["client_id"] == "plone"

    def test_the_title_comes_across(self):
        """So the login button still says what it said."""
        self.legacy_user("sub-alice")

        migration.migrate(dry_run=False)

        assert get_providers()[0].title == "Corporate SSO"

    def test_the_userid_is_the_subject(self):
        """The finding this migration rests on, asserted.

        With the ``sub`` strategy these are the same string, which is the only
        reason the join can be reconstructed at all.
        """
        self.legacy_user("sub-alice")

        migration.migrate(dry_run=False)

        assert self.store.userid_for("oidc", "sub-alice") == "sub-alice"

    def test_explicit_userids_are_honoured(self):
        """A mixed site names its OIDC accounts rather than claiming all."""
        self.legacy_user("sub-alice")
        self.legacy_user("locally-created")

        migration.migrate(dry_run=False, userids=["sub-alice"])

        assert self.store.userid_for("oidc", "sub-alice") == "sub-alice"
        assert self.store.userid_for("oidc", "locally-created") is None

    def test_all_source_users_are_claimed_by_default(self):
        """Right for a site that used OIDC exclusively, wrong for a mixed one.

        Pinned because it is a sharp edge: the dry-run report is what an
        operator is supposed to read before accepting it.
        """
        self.legacy_user("sub-alice")
        self.legacy_user("locally-created")

        migration.migrate(dry_run=False)

        assert self.store.userid_for("oidc", "locally-created") == "locally-created"

    def test_several_plugins_become_several_providers(self):
        """A site may have one plugin per issuer."""
        from pas.plugins.oidc.plugins import OIDCPlugin

        self.acl_users._setObject("oidc2", OIDCPlugin("oidc2", title="Partner SSO"))
        self.acl_users["oidc2"].issuer = "https://partner.example.com/"
        self.legacy_user("sub-alice")

        migration.migrate(dry_run=False)

        assert sorted(record.provider_id for record in get_providers()) == [
            "oidc",
            "oidc2",
        ]


class TestIdempotence:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, oidc_plugin, legacy_user, store) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.oidc_plugin = oidc_plugin
        self.legacy_user = legacy_user
        self.store = store

    def test_second_run_migrates_nothing(self):
        """A migration you cannot re-run is a migration nobody dares run."""
        self.legacy_user("sub-alice")
        migration.migrate(dry_run=False)

        report = migration.migrate(dry_run=False)

        assert report.identities == []

    def test_second_run_reports_it_as_skipped(self):
        """Silence would read as "there was nothing there"."""
        self.legacy_user("sub-alice")
        migration.migrate(dry_run=False)

        report = migration.migrate(dry_run=False)

        assert any("already migrated" in note for note in report.skipped)

    def test_second_run_does_not_duplicate_the_provider(self):
        """Provider records are keyed by id."""
        self.legacy_user("sub-alice")
        migration.migrate(dry_run=False)

        migration.migrate(dry_run=False)

        assert [record.provider_id for record in get_providers()] == ["oidc"]

    def test_the_identity_still_resolves(self):
        """The property that actually matters after a second run."""
        self.legacy_user("sub-alice")
        migration.migrate(dry_run=False)
        migration.migrate(dry_run=False)

        assert self.store.userid_for("oidc", "sub-alice") == "sub-alice"


class TestTheMigratedPersonIsAUser:
    """The same gap the authomatic migration had, in the same shape.

    ``store.add`` writes the identity join; ``plugin.link`` writes it and
    fires ``IdentityLinked``, which mints the Profile that is the user. Fixed
    in both at once, because one occurrence is a bug and two are a habit.

    ``pas.plugins.oidc`` keeps no user data this package can read, so there is
    nothing to seed a Profile from beyond the userid itself. The person
    arrives incomplete rather than absent, which is the difference that
    matters: a site administrator can find them, grant them a role and put
    them in a group before they have ever signed in.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, oidc_plugin, legacy_user, store) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.legacy_user = legacy_user
        self.store = store
        self.legacy_user("sub-alice")

    def test_the_profile_exists_after_migrating(self):
        from pas.plugins.identity.core.subscribers import get_profile

        migration.migrate(dry_run=False)

        assert get_profile("sub-alice") is not None

    def test_the_report_names_them(self):
        """Membership rather than equality: this migration also sweeps up
        every other ``source_users`` account, the layer's own test user
        included, which is behaviour of its own and tested above."""
        report = migration.migrate(dry_run=False)

        assert "sub-alice" in report.users

    def test_a_dry_run_creates_nobody(self):
        from pas.plugins.identity.core.subscribers import get_profile

        migration.migrate(dry_run=True)

        assert get_profile("sub-alice") is None

    def test_a_dry_run_says_who_would_arrive(self):
        report = migration.migrate(dry_run=True)

        assert "sub-alice" in report.users
