"""Reading a ``pas.plugins.authomatic`` dump.

The conversion is structural and has no site in it, so most of this is plain
data in and plain data out. The last class is the one that matters: the
converted document goes through the ordinary importer, because the whole point
of converting rather than importing directly is that there is one importer to
get right.
"""

from . import ADDRESS
from . import USERID
from pas.plugins.identity.core.subscribers import get_profile
from pas.plugins.identity.exportimport import convert_authomatic
from pas.plugins.identity.exportimport import import_site
from pas.plugins.identity.exportimport.authomatic import SOURCE
from pas.plugins.identity.exportimport.schema import ExportImportError

import pytest


def dump(**overrides) -> dict:
    """Return a minimal authomatic dump.

    Shaped after authomatic's own storage: ``_userid_by_identityinfo`` maps
    ``(provider_name, provider_user_id)`` to a userid, and the property sheet
    is derived from each provider's ``propertymap``.

    :param overrides: Keys to replace at the top level.
    :returns: The dump.
    """
    return {
        "source": SOURCE,
        "users": [
            {
                "userid": USERID,
                "identities": [
                    {"provider": "github", "subject": "1234567"},
                    {"provider": "google", "subject": "109876543210"},
                ],
                "properties": {
                    "fullname": "Érico Andrei",
                    "email": ADDRESS,
                    "location": "Berlin",
                },
            }
        ],
        "groups": [
            {
                "group_id": "site-editors",
                "title": "Site Editors",
                "members": [USERID],
            }
        ],
        **overrides,
    }


class TestTheConversion:
    def test_the_userid_travels_verbatim(self):
        """All four of authomatic's user-id factories produce an opaque
        string already stored against the identity, so preserving it is
        correct without branching on which mode the old site used."""
        converted = convert_authomatic(dump())

        assert converted["users"][0]["userid"] == USERID

    def test_every_identity_comes_across(self):
        """One human, two providers -- which is the case this package exists
        for and the one authomatic already stored correctly."""
        identities = convert_authomatic(dump())["users"][0]["identities"]

        assert [(i["provider"], i["subject"]) for i in identities] == [
            ("github", "1234567"),
            ("google", "109876543210"),
        ]

    def test_the_property_sheet_becomes_profile_fields(self):
        """Its sheet keys are whatever the old site's property maps produced;
        these are the names a stock configuration yields."""
        user = convert_authomatic(dump())["users"][0]

        assert user["fullname"] == "Érico Andrei"
        assert user["location"] == "Berlin"
        assert user["emails"] == [ADDRESS]

    def test_membership_is_inverted_onto_the_principal(self):
        """A dump carries members on the group; a document carries groups on
        the principal. Inverted here so the importer only sees one shape."""
        user = convert_authomatic(dump())["users"][0]

        assert user["group_ids"] == ["site-editors"]

    def test_a_missing_timestamp_is_absent_rather_than_invented(self):
        """authomatic keeps none on an identity. A record imported this way
        reads as never having been used here, which is true."""
        identity = convert_authomatic(dump())["users"][0]["identities"][0]

        assert identity["created"] is None
        assert identity["last_login"] is None

    def test_a_name_key_answers_for_fullname(self):
        """Providers disagree, and ``name`` is what several of them send."""
        d = dump()
        d["users"][0]["properties"] = {"name": "Someone", "email": ADDRESS}

        assert convert_authomatic(d)["users"][0]["fullname"] == "Someone"

    def test_the_provider_vocabulary_is_understood(self):
        """A dump read from the *stored identity* rather than from the derived
        property sheet carries the provider's own key names, because that is
        what the provider sent. ``link`` is what an OAuth2 provider calls a
        homepage, and authomatic's own shipped property maps translate it.

        Found by running the documented extraction against a real authomatic
        2.0.0 store: the field was silently dropped.
        """
        d = dump()
        d["users"][0]["properties"] = {
            "name": "Erico Andrei",
            "email": ADDRESS,
            "link": "https://kitconcept.com",
        }

        user = convert_authomatic(d)["users"][0]

        assert user["fullname"] == "Erico Andrei"
        assert user["home_page"] == "https://kitconcept.com"

    def test_a_plone_key_still_wins_over_the_provider_one(self):
        """Both vocabularies are understood, so a dump carrying both must not
        depend on dict ordering to pick."""
        d = dump()
        d["users"][0]["properties"] = {
            "link": "https://provider.example",
            "home_page": "https://plone.example",
            "name": "From the provider",
            "fullname": "From the sheet",
            "email": ADDRESS,
        }

        user = convert_authomatic(d)["users"][0]

        assert user["home_page"] == "https://plone.example"
        assert user["fullname"] == "From the sheet"

    def test_a_key_with_no_profile_field_is_dropped(self):
        """``picture``, ``first_name`` and ``last_name`` are in a real Google
        property map and have no Profile field. An attribute nothing declares
        is invisible to every form and permission in the site."""
        d = dump()
        d["users"][0]["properties"] = {
            "email": ADDRESS,
            "picture": "https://example.org/a.png",
            "first_name": "Erico",
            "last_name": "Andrei",
        }

        user = convert_authomatic(d)["users"][0]

        assert "picture" not in user
        assert "first_name" not in user
        assert "https://example.org/a.png" not in str(user)

    def test_the_generator_says_where_it_came_from(self):
        """A document found on disk in two years should say what made it."""
        assert SOURCE in convert_authomatic(dump())["generator"]

    @pytest.mark.parametrize(
        "broken,expected",
        [
            ({"source": "something-else"}, "not"),
            ({"users": "not a list"}, "no 'users' list"),
        ],
        ids=["wrong-source", "users-not-a-list"],
    )
    def test_a_dump_that_is_not_one_is_refused(self, broken, expected):
        """The two formats are close enough that reading one as the other
        half-works, which is worse than failing."""
        with pytest.raises(ExportImportError) as error:
            convert_authomatic(dump(**broken))

        assert expected in str(error.value)

    def test_a_user_without_a_userid_is_refused(self):
        """Not skipped: a dump missing userids is a broken extraction, and
        every user in it is equally unusable."""
        with pytest.raises(ExportImportError) as error:
            convert_authomatic(dump(users=[{"identities": []}]))

        assert "userid" in str(error.value)

    def test_no_secret_survives_the_conversion(self):
        """authomatic gives each user a random ``_secret`` and treats it as a
        password. Nobody can type it, and a document is a file that gets
        copied around."""
        d = dump()
        d["users"][0]["secret"] = "a-random-uuid"
        d["users"][0]["password"] = "hunter2"

        converted = convert_authomatic(d)

        assert "a-random-uuid" not in str(converted)
        assert "hunter2" not in str(converted)


class TestConvertedThenImported:
    """The reason the conversion produces a document rather than writing to
    the site itself: migrating is the ordinary import."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin) -> None:
        self.portal = portal
        self.plugin = plugin

    def test_the_account_arrives(self):
        result = import_site(convert_authomatic(dump()))

        assert not result.refused
        assert get_profile(USERID) is not None

    def test_both_identities_reach_the_same_account(self):
        """One human who signed in with two providers stays one human."""
        import_site(convert_authomatic(dump()))
        store = self.plugin.store

        assert store.userid_for("github", "1234567") == USERID
        assert store.userid_for("google", "109876543210") == USERID

    def test_the_group_membership_arrives(self):
        import_site(convert_authomatic(dump()))

        assert get_profile(USERID).group_ids == ("site-editors",)
