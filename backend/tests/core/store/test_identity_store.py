"""Unit tests for the identity store."""

from . import CLAIMS
from . import EMAIL_LOWER
from . import EMAIL_MIXED_CASE
from . import GITHUB
from . import OTHER_USERID
from . import USERID
from pas.plugins.identity.core.interfaces import IdentityCollision
from pas.plugins.identity.core.interfaces import IIdentityStore
from pas.plugins.identity.core.store import IdentityRecord
from pas.plugins.identity.core.store import IdentityStore
from pas.plugins.identity.core.store import normalize_subject
from zope.interface.verify import verifyObject

import pytest


@pytest.fixture
def store() -> IdentityStore:
    """Return an empty identity store."""
    return IdentityStore()


@pytest.fixture
def linked_store(store: IdentityStore) -> IdentityStore:
    """Return a store with one GitHub identity linked to ``USERID``."""
    store.add(*GITHUB, USERID, CLAIMS)
    return store


class TestStoreContract:
    @pytest.fixture(autouse=True)
    def _setup(self, store: IdentityStore) -> None:
        self.store = store

    def test_provides_interface(self):
        """The store implements the declared interface."""
        assert verifyObject(IIdentityStore, self.store)

    def test_starts_empty(self):
        """A fresh store holds no identities."""
        assert len(self.store) == 0
        assert self.store.userids() == ()


class TestAdd:
    @pytest.fixture(autouse=True)
    def _setup(self, store: IdentityStore) -> None:
        self.store = store
        self.record = store.add(*GITHUB, USERID, CLAIMS)

    def test_add_returns_record(self):
        """Linking returns the stored record."""
        record = self.record

        assert isinstance(record, IdentityRecord)
        assert record.provider == "github"
        assert record.subject == "1234567"
        assert record.last_login is None

    def test_add_is_resolvable(self):
        """A linked identity resolves to its userid."""
        assert self.store.userid_for(*GITHUB) == USERID
        assert len(self.store) == 1

    def test_add_appears_in_reverse_map(self):
        """A linked identity is listed against its userid."""
        records = self.store.identities_for(USERID)

        assert len(records) == 1
        assert records[0].provider == "github"
        assert self.store.userids() == (USERID,)

    def test_claims_snapshot_is_copied(self):
        """The stored claims match what was passed in."""
        record = self.store.get(*GITHUB)

        assert dict(record.claims) == CLAIMS

    def test_second_provider_same_user(self):
        """One userid owns identities from several providers -- the point of
        the package."""
        self.store.add("google", "sub-abc", USERID, CLAIMS)

        assert self.store.userid_for("google", "sub-abc") == USERID
        assert len(self.store.identities_for(USERID)) == 2


class TestCollision:
    """An identity is never silently moved between userids."""

    @pytest.fixture(autouse=True)
    def _setup(self, linked_store: IdentityStore) -> None:
        self.store = linked_store

    def test_other_userid_collides(self):
        """Linking a taken identity to another userid is a hard error."""
        with pytest.raises(IdentityCollision) as exc:
            self.store.add(*GITHUB, OTHER_USERID, CLAIMS)

        assert USERID in str(exc.value)

    def test_same_userid_collides(self):
        """Re-adding to the owning userid is a collision too: use touch()."""
        with pytest.raises(IdentityCollision):
            self.store.add(*GITHUB, USERID, CLAIMS)

    def test_collision_leaves_store_untouched(self):
        """A refused link changes nothing."""
        with pytest.raises(IdentityCollision):
            self.store.add(*GITHUB, OTHER_USERID, CLAIMS)

        assert self.store.userid_for(*GITHUB) == USERID
        assert len(self.store) == 1
        assert self.store.identities_for(OTHER_USERID) == ()


class TestEmailCaseNormalization:
    """``provider="email"`` subjects are case-insensitive; others are not."""

    @pytest.fixture(autouse=True)
    def _setup(self, store: IdentityStore) -> None:
        self.store = store

    @pytest.mark.parametrize(
        "provider,subject,expected",
        [
            ("email", "Erico@Plone.ORG", "erico@plone.org"),
            ("email", "erico@plone.org", "erico@plone.org"),
            ("github", "AbC", "AbC"),
            ("oidc-generic", "Sub-123", "Sub-123"),
        ],
    )
    def test_normalize_subject(self, provider: str, subject: str, expected: str):
        """Only email subjects are lowercased."""
        assert normalize_subject(provider, subject) == expected

    def test_lookup_is_case_insensitive(self):
        """An address linked in one case resolves in another."""
        self.store.add(*EMAIL_MIXED_CASE, USERID, CLAIMS)

        assert self.store.userid_for(*EMAIL_LOWER) == USERID
        assert self.store.userid_for("email", "ERICO@PLONE.ORG") == USERID

    def test_same_mailbox_cannot_be_linked_twice(self):
        """Case variants are the same identity, so the second link collides."""
        self.store.add(*EMAIL_LOWER, USERID, CLAIMS)

        with pytest.raises(IdentityCollision):
            self.store.add(*EMAIL_MIXED_CASE, OTHER_USERID, CLAIMS)

    def test_subject_stored_normalized(self):
        """The record carries the normalized subject, not what was passed."""
        record = self.store.add(*EMAIL_MIXED_CASE, USERID, CLAIMS)

        assert record.subject == "erico@plone.org"

    def test_github_lookup_is_case_sensitive(self):
        """Non-email subjects are opaque and compared verbatim."""
        self.store.add("github", "AbC", USERID, CLAIMS)

        assert self.store.userid_for("github", "abc") is None


class TestGet:
    @pytest.fixture(autouse=True)
    def _setup(self, linked_store: IdentityStore) -> None:
        self.store = linked_store

    def test_get_returns_record(self):
        """A known identity yields its record."""
        record = self.store.get(*GITHUB)

        assert record.subject == "1234567"

    def test_get_unknown_returns_none(self):
        """An unknown identity yields ``None`` rather than raising."""
        assert self.store.get("google", "nobody") is None

    def test_get_finds_right_record_among_many(self):
        """The reverse map scan picks the matching provider/subject pair."""
        self.store.add("google", "sub-abc", USERID, CLAIMS)

        assert self.store.get("google", "sub-abc").provider == "google"
        assert self.store.get(*GITHUB).provider == "github"


class TestRemove:
    @pytest.fixture(autouse=True)
    def _setup(self, linked_store: IdentityStore) -> None:
        self.store = linked_store

    def test_remove_clears_forward_map(self):
        """The identity no longer resolves."""
        self.store.remove(*GITHUB)

        assert self.store.userid_for(*GITHUB) is None
        assert len(self.store) == 0

    def test_remove_clears_reverse_map(self):
        """The userid drops out once it owns nothing."""
        self.store.remove(*GITHUB)

        assert self.store.identities_for(USERID) == ()
        assert self.store.userids() == ()

    def test_remove_keeps_sibling_identities(self):
        """Unlinking one identity leaves the others in place."""
        self.store.add("google", "sub-abc", USERID, CLAIMS)

        self.store.remove(*GITHUB)

        remaining = self.store.identities_for(USERID)
        assert [r.provider for r in remaining] == ["google"]
        assert self.store.userid_for("google", "sub-abc") == USERID

    def test_remove_unknown_raises(self):
        """Unlinking something that was never linked is an error."""
        with pytest.raises(KeyError):
            self.store.remove("google", "nobody")

    def test_remove_is_case_insensitive_for_email(self):
        """An address can be unlinked in any case."""
        self.store.add(*EMAIL_LOWER, USERID, CLAIMS)

        self.store.remove(*EMAIL_MIXED_CASE)

        assert self.store.userid_for(*EMAIL_LOWER) is None


class TestTouch:
    @pytest.fixture(autouse=True)
    def _setup(self, linked_store: IdentityStore) -> None:
        self.store = linked_store

    def test_touch_sets_last_login(self):
        """A login stamps the record."""
        record = self.store.touch(*GITHUB, CLAIMS)

        assert record.last_login is not None

    def test_touch_refreshes_claims(self):
        """Provider-owned claims are refreshed on every login."""
        fresh = {**CLAIMS, "fullname": "Érico Andrei (renamed)"}

        record = self.store.touch(*GITHUB, fresh)

        assert record.claims["fullname"] == "Érico Andrei (renamed)"

    def test_touch_does_not_relink(self):
        """Touching never changes ownership or count."""
        self.store.touch(*GITHUB, CLAIMS)

        assert self.store.userid_for(*GITHUB) == USERID
        assert len(self.store) == 1

    def test_touch_unknown_raises(self):
        """Touching an unknown identity is an error."""
        with pytest.raises(KeyError):
            self.store.touch("google", "nobody", CLAIMS)


class TestSerialize:
    @pytest.fixture(autouse=True)
    def _setup(self, linked_store: IdentityStore) -> None:
        self.store = linked_store

    def test_serialize_shape(self):
        """The API representation carries exactly the documented keys."""
        payload = self.store.get(*GITHUB).serialize()

        assert set(payload) == {
            "provider",
            "subject",
            "created",
            "last_login",
            "claims",
            "groups",
        }
        assert payload["provider"] == "github"
        assert payload["last_login"] is None

    def test_a_record_grants_no_groups_until_a_login_says_so(self):
        """``groups`` is what this provider granted, not what the user is in.

        A class attribute, so a record written before the field existed reads
        as an empty grant rather than needing an upgrade step.
        """
        record = self.store.get(*GITHUB)

        assert record.groups == ()
        assert record.serialize()["groups"] == []

    def test_serialize_after_login(self):
        """``last_login`` becomes an ISO timestamp once the identity is used."""
        self.store.touch(*GITHUB, CLAIMS)

        payload = self.store.get(*GITHUB).serialize()

        assert payload["last_login"].startswith(str(payload["created"][:4]))

    def test_repr(self):
        """The record has a readable repr for debugging."""
        assert repr(self.store.get(*GITHUB)) == "<IdentityRecord github:1234567>"
