"""Migrating from ``pas.plugins.authomatic``.

The fixtures install the real plugin and write into its real BTrees rather
than synthesizing the shapes. That is the whole point: a fixture that encoded
our reading of its storage would pass while the migration was wrong about it,
which is exactly the failure the spike was meant to rule out.

Both user-id modes are covered. authomatic's four factories all produce opaque
strings that are already stored against the identity, so a migration
preserving the user id verbatim is correct in every mode -- these prove that
rather than assume it.
"""

from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.migration import authomatic as migration

import pytest


@pytest.fixture
def authomatic_plugin(portal, acl_users):
    """Install the real authomatic plugin.

    :param portal: The Plone site.
    :param acl_users: The site's PAS instance.
    :returns: The installed plugin.
    """
    from plone.app.testing import applyProfile

    applyProfile(portal, "pas.plugins.authomatic:default")
    return acl_users[migration.AUTHOMATIC_PLUGIN_ID]


@pytest.fixture
def legacy(authomatic_plugin):
    """Return a helper writing identities into authomatic's own storage.

    Writes the two BTrees directly, in the shape ``remember_identity`` leaves
    them. Driving a real Authomatic result would need a real provider round
    trip; the storage is what the migration reads, and it is what is pinned.

    :param authomatic_plugin: The authomatic plugin.
    :returns: Callable taking provider, subject and userid.
    """
    from pas.plugins.authomatic.useridentities import UserIdentities
    from pas.plugins.authomatic.useridentities import UserIdentity
    from persistent.mapping import PersistentMapping

    def build(data: dict) -> UserIdentity:
        """Build a ``UserIdentity`` without an Authomatic result.

        Its ``__init__`` wants a live result object, so this bypasses it the
        same way the package's own (unreleased) ``from_dict`` does. Calling
        that helper directly would tie these tests to an API that exists in
        the development branch and not in the 2.0.0 release we depend on.

        :param data: The identity mapping.
        :returns: The identity.
        """
        identity = UserIdentity.__new__(UserIdentity)
        PersistentMapping.__init__(identity)
        identity.update(data)
        return identity

    def add(provider: str, subject: str, userid: str, **user) -> None:
        authomatic_plugin._userid_by_identityinfo[(provider, subject)] = userid
        identities = authomatic_plugin._useridentities_by_userid.get(userid)
        if identities is None:
            identities = UserIdentities(userid)
            authomatic_plugin._useridentities_by_userid[userid] = identities
        identities._identities[provider] = build({
            "provider_name": provider,
            "id": subject,
            **user,
        })

    return add


class TestNothingToDo:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users) -> None:
        self.portal = portal
        self.acl_users = acl_users

    def test_refuses_without_authomatic(self):
        """A site that never had it is not an error, but it is a refusal."""
        report = migration.migrate(dry_run=True)

        assert report.refused
        assert "nothing to migrate" in report.refusals[0]

    def test_empty_authomatic_migrates_nothing(self, authomatic_plugin):
        """Installed but never used."""
        report = migration.migrate(dry_run=True)

        assert not report.refused
        assert report.identities == []


class TestDegradedSites:
    """States a half-removed installation can leave behind."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, authomatic_plugin, legacy, store) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.authomatic_plugin = authomatic_plugin
        self.legacy = legacy
        self.store = store

    def test_missing_identity_plugin_is_refused(self):
        """Migrating onto a package that is not installed is not a migration."""
        self.acl_users._delObject(PLUGIN_ID)

        report = migration.migrate(dry_run=True)

        assert report.refused
        assert "is not installed" in report.refusals[0]

    def test_uninstalled_authomatic_package_yields_no_config(
        self, monkeypatch, legacy, store
    ):
        """The plugin object outlives the package it came from.

        Setting the module to ``None`` in ``sys.modules`` is what makes the
        import fail, which is the state a site is in after the distribution is
        removed but the ZODB still holds the plugin.
        """
        import sys

        self.legacy("github", "12345", "some-userid")
        monkeypatch.setitem(sys.modules, "pas.plugins.authomatic.utils", None)

        report = migration.migrate(dry_run=False)

        # The identities still migrate: they live in the plugin's own BTrees,
        # not in the package. Only the provider configuration is lost.
        assert self.store.userid_for("github", "12345") == "some-userid"
        assert report.providers == []

    def test_an_identity_without_stored_userdata_migrates_blank(self):
        """The join is what matters; the claims snapshot is a convenience."""
        self.authomatic_plugin._userid_by_identityinfo[("github", "999")] = "orphan"

        migration.migrate(dry_run=False)

        assert self.store.userid_for("github", "999") == "orphan"
        assert self.store.get("github", "999").claims == {}

    def test_an_identity_for_an_unknown_provider_migrates_blank(self):
        """User data exists, but not for that provider."""
        self.legacy("github", "12345", "some-userid")
        self.authomatic_plugin._userid_by_identityinfo[("google", "777")] = (
            "some-userid"
        )

        migration.migrate(dry_run=False)

        assert self.store.get("google", "777").claims == {}


class TestDryRun:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, legacy, store) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.legacy = legacy
        self.store = store

    def test_reports_what_it_would_do(self):
        """The report is the thing an operator reads before committing."""
        self.legacy("github", "12345", "some-userid")

        report = migration.migrate(dry_run=True)

        assert report.identities == [("github", "12345", "some-userid")]

    def test_writes_nothing(self):
        """Dry run means dry."""
        self.legacy("github", "12345", "some-userid")

        migration.migrate(dry_run=True)

        assert self.store.userid_for("github", "12345") is None

    def test_creates_no_providers(self):
        """Including the configuration half."""
        self.legacy("github", "12345", "some-userid")

        migration.migrate(dry_run=True)

        assert get_providers() == []

    def test_is_the_default(self):
        """A function that rewrites authentication when somebody calls it to
        see what it does is a bad function."""
        self.legacy("github", "12345", "some-userid")

        migration.migrate()

        assert self.store.userid_for("github", "12345") is None


class TestMigration:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, legacy, store) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.legacy = legacy
        self.store = store

    def test_identity_is_migrated(self):
        """The mapping authomatic already had, now in this package's self.store."""
        self.legacy("github", "12345", "some-userid")

        migration.migrate(dry_run=False)

        assert self.store.userid_for("github", "12345") == "some-userid"

    def test_several_providers_for_one_user(self):
        """Linking is the point of this package; the migration must keep it."""
        self.legacy("github", "12345", "shared-userid")
        self.legacy("google", "sub-999", "shared-userid")

        migration.migrate(dry_run=False)

        assert self.store.userid_for("github", "12345") == "shared-userid"
        assert self.store.userid_for("google", "sub-999") == "shared-userid"
        assert len(self.store.identities_for("shared-userid")) == 2

    def test_claims_are_carried_over(self):
        """Best effort, so the account is not blank until the next login."""
        self.legacy(
            "github",
            "12345",
            "some-userid",
            name="Alice Liddell",
            email="alice@example.com",
        )

        migration.migrate(dry_run=False)

        record = self.store.get("github", "12345")
        assert record.claims["fullname"] == "Alice Liddell"
        assert record.claims["email"] == "alice@example.com"

    def test_email_is_never_inherited_as_verified(self):
        """Auto-linking will not act on a claim we cannot trace to our own
        check.

        authomatic did not record whether the provider asserted verification,
        so inheriting it as true would be inventing evidence.
        """
        self.legacy("github", "12345", "some-userid", email="alice@example.com")

        migration.migrate(dry_run=False)

        assert self.store.get("github", "12345").claims["email_verified"] is False

    def test_provider_configuration_is_created(self):
        """Without credentials nothing can log in afterwards."""
        from pas.plugins.authomatic.utils import authomatic_settings

        authomatic_settings().json_config = (
            '{"github": {"consumer_key": "key", "consumer_secret": "secret"}}'
        )
        self.legacy("github", "12345", "some-userid")

        migration.migrate(dry_run=False)

        providers = {record.provider_id: record for record in get_providers()}
        assert providers["github"].driver_id == "github"
        assert providers["github"].config["client_id"] == "key"

    def test_an_unknown_provider_lands_on_the_generic_driver(self):
        """And says so, rather than looking configured."""
        from pas.plugins.authomatic.utils import authomatic_settings

        authomatic_settings().json_config = (
            '{"keycloak": {"consumer_key": "key", "consumer_secret": "secret"}}'
        )
        self.legacy("keycloak", "sub-1", "some-userid")

        report = migration.migrate(dry_run=False)

        providers = {record.provider_id: record for record in get_providers()}
        assert providers["keycloak"].driver_id == "oidc-generic"
        assert any("keycloak" in note for note in report.skipped)


class TestUserIdModes:
    """authomatic's four factories, and why the migration ignores which ran.

    Every factory writes an opaque string into the same BTree, so preserving
    the user id verbatim is correct in all of them. These pin that: whatever
    shape the id has, it survives unchanged, which is what keeps local roles,
    sharing settings and content ownership pointing at the right person.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, legacy, store) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.legacy = legacy
        self.store = store

    @pytest.mark.parametrize(
        "userid",
        [
            "12345",  # ProviderIDUserIDFactory
            "alice",  # ProviderIDUserNameFactory
            "alice_2",  # normalize() after a collision
            "0f8fad5bd9cb469fa16570867728950e",  # uuid factory
        ],
    )
    def test_the_userid_survives_verbatim(self, userid):
        """Whatever mode produced it."""
        self.legacy("github", "12345", userid)

        migration.migrate(dry_run=False)

        assert self.store.userid_for("github", "12345") == userid


class TestIdempotence:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, legacy, store) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.legacy = legacy
        self.store = store

    def test_second_run_migrates_nothing(self):
        """A migration you cannot re-run is a migration nobody dares run."""
        self.legacy("github", "12345", "some-userid")
        migration.migrate(dry_run=False)

        report = migration.migrate(dry_run=False)

        assert report.identities == []

    def test_second_run_reports_it_as_skipped(self):
        """Silence would read as "there was nothing there"."""
        self.legacy("github", "12345", "some-userid")
        migration.migrate(dry_run=False)

        report = migration.migrate(dry_run=False)

        assert any("already migrated" in note for note in report.skipped)

    def test_second_run_does_not_duplicate_the_provider(self):
        """Provider records are keyed by id; two would be one too many."""
        from pas.plugins.authomatic.utils import authomatic_settings

        authomatic_settings().json_config = (
            '{"github": {"consumer_key": "key", "consumer_secret": "secret"}}'
        )
        self.legacy("github", "12345", "some-userid")
        migration.migrate(dry_run=False)

        migration.migrate(dry_run=False)

        assert [record.provider_id for record in get_providers()] == ["github"]

    def test_the_identity_still_resolves(self):
        """The property that actually matters after a second run."""
        self.legacy("github", "12345", "some-userid")
        migration.migrate(dry_run=False)
        migration.migrate(dry_run=False)

        assert self.store.userid_for("github", "12345") == "some-userid"
