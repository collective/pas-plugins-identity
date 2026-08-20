"""Unit tests for the identity store (§4.2, I1/I3)."""

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


@pytest.fixture()
def store() -> IdentityStore:
    """Return an empty identity store."""
    return IdentityStore()


@pytest.fixture()
def linked_store(store: IdentityStore) -> IdentityStore:
    """Return a store with one GitHub identity linked to ``USERID``."""
    store.add(*GITHUB, USERID, CLAIMS)
    return store


class TestStoreContract:
    def test_provides_interface(self, store: IdentityStore):
        """The store implements the declared interface."""
        assert verifyObject(IIdentityStore, store)

    def test_starts_empty(self, store: IdentityStore):
        """A fresh store holds no identities."""
        assert len(store) == 0
        assert store.userids() == ()


class TestAdd:
    def test_add_returns_record(self, store: IdentityStore):
        """Linking returns the stored record."""
        record = store.add(*GITHUB, USERID, CLAIMS)

        assert isinstance(record, IdentityRecord)
        assert record.provider == "github"
        assert record.subject == "1234567"
        assert record.last_login is None

    def test_add_is_resolvable(self, linked_store: IdentityStore):
        """A linked identity resolves to its userid."""
        assert linked_store.userid_for(*GITHUB) == USERID
        assert len(linked_store) == 1

    def test_add_appears_in_reverse_map(self, linked_store: IdentityStore):
        """A linked identity is listed against its userid."""
        records = linked_store.identities_for(USERID)

        assert len(records) == 1
        assert records[0].provider == "github"
        assert linked_store.userids() == (USERID,)

    def test_claims_snapshot_is_copied(self, linked_store: IdentityStore):
        """The stored claims match what was passed in."""
        record = linked_store.get(*GITHUB)

        assert dict(record.claims) == CLAIMS

    def test_second_provider_same_user(self, linked_store: IdentityStore):
        """One userid owns identities from several providers -- the point of
        the package."""
        linked_store.add("google", "sub-abc", USERID, CLAIMS)

        assert linked_store.userid_for("google", "sub-abc") == USERID
        assert len(linked_store.identities_for(USERID)) == 2


class TestCollision:
    """I3/S3 -- an identity is never silently moved between userids."""

    def test_other_userid_collides(self, linked_store: IdentityStore):
        """Linking a taken identity to another userid is a hard error."""
        with pytest.raises(IdentityCollision) as exc:
            linked_store.add(*GITHUB, OTHER_USERID, CLAIMS)

        assert USERID in str(exc.value)

    def test_same_userid_collides(self, linked_store: IdentityStore):
        """Re-adding to the owning userid is a collision too: use touch()."""
        with pytest.raises(IdentityCollision):
            linked_store.add(*GITHUB, USERID, CLAIMS)

    def test_collision_leaves_store_untouched(self, linked_store: IdentityStore):
        """A refused link changes nothing."""
        with pytest.raises(IdentityCollision):
            linked_store.add(*GITHUB, OTHER_USERID, CLAIMS)

        assert linked_store.userid_for(*GITHUB) == USERID
        assert len(linked_store) == 1
        assert linked_store.identities_for(OTHER_USERID) == ()


class TestEmailCaseNormalization:
    """``provider="email"`` subjects are case-insensitive; others are not."""

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

    def test_lookup_is_case_insensitive(self, store: IdentityStore):
        """An address linked in one case resolves in another."""
        store.add(*EMAIL_MIXED_CASE, USERID, CLAIMS)

        assert store.userid_for(*EMAIL_LOWER) == USERID
        assert store.userid_for("email", "ERICO@PLONE.ORG") == USERID

    def test_same_mailbox_cannot_be_linked_twice(self, store: IdentityStore):
        """Case variants are the same identity, so the second link collides."""
        store.add(*EMAIL_LOWER, USERID, CLAIMS)

        with pytest.raises(IdentityCollision):
            store.add(*EMAIL_MIXED_CASE, OTHER_USERID, CLAIMS)

    def test_subject_stored_normalized(self, store: IdentityStore):
        """The record carries the normalized subject, not what was passed."""
        record = store.add(*EMAIL_MIXED_CASE, USERID, CLAIMS)

        assert record.subject == "erico@plone.org"

    def test_github_lookup_is_case_sensitive(self, store: IdentityStore):
        """Non-email subjects are opaque and compared verbatim."""
        store.add("github", "AbC", USERID, CLAIMS)

        assert store.userid_for("github", "abc") is None


class TestGet:
    def test_get_returns_record(self, linked_store: IdentityStore):
        """A known identity yields its record."""
        record = linked_store.get(*GITHUB)

        assert record.subject == "1234567"

    def test_get_unknown_returns_none(self, store: IdentityStore):
        """An unknown identity yields ``None`` rather than raising."""
        assert store.get(*GITHUB) is None

    def test_get_finds_right_record_among_many(self, linked_store: IdentityStore):
        """The reverse map scan picks the matching provider/subject pair."""
        linked_store.add("google", "sub-abc", USERID, CLAIMS)

        assert linked_store.get("google", "sub-abc").provider == "google"
        assert linked_store.get(*GITHUB).provider == "github"


class TestRemove:
    def test_remove_clears_forward_map(self, linked_store: IdentityStore):
        """The identity no longer resolves."""
        linked_store.remove(*GITHUB)

        assert linked_store.userid_for(*GITHUB) is None
        assert len(linked_store) == 0

    def test_remove_clears_reverse_map(self, linked_store: IdentityStore):
        """The userid drops out once it owns nothing."""
        linked_store.remove(*GITHUB)

        assert linked_store.identities_for(USERID) == ()
        assert linked_store.userids() == ()

    def test_remove_keeps_sibling_identities(self, linked_store: IdentityStore):
        """Unlinking one identity leaves the others in place."""
        linked_store.add("google", "sub-abc", USERID, CLAIMS)

        linked_store.remove(*GITHUB)

        remaining = linked_store.identities_for(USERID)
        assert [r.provider for r in remaining] == ["google"]
        assert linked_store.userid_for("google", "sub-abc") == USERID

    def test_remove_unknown_raises(self, store: IdentityStore):
        """Unlinking something that was never linked is an error."""
        with pytest.raises(KeyError):
            store.remove(*GITHUB)

    def test_remove_is_case_insensitive_for_email(self, store: IdentityStore):
        """An address can be unlinked in any case."""
        store.add(*EMAIL_LOWER, USERID, CLAIMS)

        store.remove(*EMAIL_MIXED_CASE)

        assert len(store) == 0


class TestTouch:
    def test_touch_sets_last_login(self, linked_store: IdentityStore):
        """A login stamps the record."""
        record = linked_store.touch(*GITHUB, CLAIMS)

        assert record.last_login is not None

    def test_touch_refreshes_claims(self, linked_store: IdentityStore):
        """Provider-owned claims are refreshed on every login (D2)."""
        fresh = {**CLAIMS, "fullname": "Érico Andrei (renamed)"}

        record = linked_store.touch(*GITHUB, fresh)

        assert record.claims["fullname"] == "Érico Andrei (renamed)"

    def test_touch_does_not_relink(self, linked_store: IdentityStore):
        """Touching never changes ownership or count."""
        linked_store.touch(*GITHUB, CLAIMS)

        assert linked_store.userid_for(*GITHUB) == USERID
        assert len(linked_store) == 1

    def test_touch_unknown_raises(self, store: IdentityStore):
        """Touching an unknown identity is an error."""
        with pytest.raises(KeyError):
            store.touch(*GITHUB, CLAIMS)


class TestSerialize:
    def test_serialize_shape(self, linked_store: IdentityStore):
        """The API representation carries exactly the documented keys."""
        payload = linked_store.get(*GITHUB).serialize()

        assert set(payload) == {
            "provider",
            "subject",
            "created",
            "last_login",
            "claims",
        }
        assert payload["provider"] == "github"
        assert payload["last_login"] is None

    def test_serialize_after_login(self, linked_store: IdentityStore):
        """``last_login`` becomes an ISO timestamp once the identity is used."""
        linked_store.touch(*GITHUB, CLAIMS)

        payload = linked_store.get(*GITHUB).serialize()

        assert payload["last_login"].startswith(str(payload["created"][:4]))

    def test_repr(self, linked_store: IdentityStore):
        """The record has a readable repr for debugging."""
        assert repr(linked_store.get(*GITHUB)) == "<IdentityRecord github:1234567>"
