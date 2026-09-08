"""What a claims snapshot refuses to carry.

``claims["raw"]`` is not scratch space. It is stored on the identity record as
a ``PersistentMapping`` and written out verbatim by the exporter, so a value
that gets in during a migration is in the ZODB and in every principal document
produced afterwards. The login path never has to think about this because a
userinfo response carries no credential; the migration paths read a store this
package did not write, and authomatic's is one that does.
"""

from pas.plugins.identity.core.utils.claims import scrub_payload
from pas.plugins.identity.core.utils.claims import SECRET_KEYS

import pytest


class TestWhatIsDropped:
    @pytest.mark.parametrize("key", sorted(SECRET_KEYS))
    def test_every_named_key_is_dropped(self, key: str):
        """The whole list, so adding one to it cannot be a no-op."""
        assert scrub_payload({key: "s3cr3t", "name": "Dana"}) == {"name": "Dana"}

    def test_authomatic_credentials_are_dropped(self):
        """The one this package provably meets: ``User.to_dict()`` puts a
        serialized ``Credentials`` here, holding the account's tokens."""
        payload = {"credentials": "1|2|ya29.a0Af...", "id": "1234567"}

        assert scrub_payload(payload) == {"id": "1234567"}

    def test_the_match_ignores_case(self):
        """A dump is a file somebody wrote, and JSON keys are not normalized
        anywhere on the way here."""
        assert scrub_payload({"Access_Token": "x", "ID": "7"}) == {"ID": "7"}


class TestWhatSurvives:
    def test_an_ordinary_payload_is_untouched(self):
        """The common case, and the one the enrichers depend on."""
        payload = {"login": "ericof", "bio": "Writes Python.", "followers": 42}

        assert scrub_payload(payload) == payload

    def test_a_key_that_merely_contains_a_secret_word_survives(self):
        """Whole keys only. A substring rule would redact a provider's own
        vocabulary on a guess, and this package does not get to do that."""
        payload = {"secret_santa_nickname": "Dana", "token_count": 3}

        assert scrub_payload(payload) == payload

    def test_a_nested_object_is_not_walked(self):
        """Top level only, deliberately: a nested object is the provider's own
        structure and the credential-bearing shapes this package meets are all
        flat. Documented rather than discovered."""
        payload = {"address": {"formatted": "Berlin", "token": "kept"}}

        assert scrub_payload(payload) == payload


class TestWhatIsNotAPayload:
    @pytest.mark.parametrize("value", [None, [], "", "a string", 7, ["token"]])
    def test_anything_that_is_not_an_object_becomes_an_empty_one(self, value):
        """A dump is untrusted input, and a snapshot with no payload is a
        better answer than a traceback halfway through a migration."""
        assert scrub_payload(value) == {}
