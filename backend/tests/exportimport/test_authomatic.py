"""Reading a ``pas.plugins.authomatic`` dump.

The conversion is structural and has no site in it, so most of this is plain
data in and plain data out. The last class is the one that matters: the
converted document goes through the ordinary importer, because the whole point
of converting rather than importing directly is that there is one importer to
get right.
"""

from . import ADDRESS
from . import USERID
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.profiles import get_profile
from pas.plugins.identity.exportimport import convert_authomatic
from pas.plugins.identity.exportimport import import_site
from pas.plugins.identity.exportimport.authomatic import site_propertymaps
from pas.plugins.identity.exportimport.authomatic import SOURCE
from pas.plugins.identity.exportimport.authomatic import unmapped_providers
from pas.plugins.identity.exportimport.schema import ExportImportError
from pas.plugins.identity.exportimport.schema import USER_FIELDS

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

    def unmapped(self) -> dict:
        """Convert a dump whose properties all lack a Profile field.

        ``picture``, ``first_name`` and ``last_name`` are in a real Google
        property map and this package has a field for none of them.

        :returns: The converted user record.
        """
        d = dump()
        d["users"][0]["properties"] = {
            "email": ADDRESS,
            "picture": "https://example.org/a.png",
            "first_name": "Erico",
            "last_name": "Andrei",
        }
        return convert_authomatic(d)["users"][0]

    def test_a_key_with_no_profile_field_becomes_no_field(self):
        """An attribute nothing declares is invisible to every form and
        permission in the site, so it does not become one."""
        user = self.unmapped()

        assert "picture" not in user
        assert "first_name" not in user
        assert "https://example.org/a.png" not in str({
            name: user[name] for name in USER_FIELDS
        })

    def test_a_key_with_no_profile_field_survives_in_the_payload(self):
        """The other half, and it is not a leak. The claims snapshot is the
        provider's own document rather than a set of Profile attributes, and a
        key this package has no name for is exactly what a site installs an
        ``IProfileEnricher`` to reach: dropping it here leaves the enricher
        nothing to read. See ``test_enricher_payload``.

        The assertion above used to read ``not in str(user)``, which held only
        while the snapshot was empty and every enricher therefore did
        nothing."""
        raw = self.unmapped()["identities"][0]["claims"]["raw"]

        assert raw["picture"] == "https://example.org/a.png"
        assert raw["first_name"] == "Erico"

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


def github_dump(**properties) -> dict:
    """Return a dump carrying GitHub's own vocabulary.

    What the documented extraction produces: it merges the provider's document
    into the stored identity, so the raw API fields (``bio``, ``blog``,
    ``html_url``) sit beside authomatic's normalized ones (``name``, ``link``).

    :param properties: Property keys to replace.
    :returns: The dump.
    """
    return {
        "source": SOURCE,
        "users": [
            {
                "userid": USERID,
                "identities": [{"provider": "github", "subject": "1234567"}],
                "properties": {
                    "login": "ericof",
                    "name": "Érico Andrei",
                    "bio": "Writes Python for a living.",
                    "blog": "https://erico.example.com",
                    # authomatic's GitHub parser sets ``link`` from
                    # ``html_url``; verified against authomatic 1.3.0.
                    "link": "https://github.com/ericof",
                    "html_url": "https://github.com/ericof",
                    "location": "Berlin",
                    "email": ADDRESS,
                    **properties,
                },
            }
        ],
    }


#: What a site running GitHub actually configures, and what the built-in map
#: cannot know.
GITHUB_MAP = {"bio": "description", "blog": "home_page", "name": "fullname"}


class TestTheSitePropertyMap:
    """A dump carries the provider's vocabulary, and only the target site's
    map says what it means. Left to the built-in map, a GitHub migration put
    everybody's profile URL in ``home_page`` and dropped every biography."""

    def test_the_site_map_supplies_a_field_the_builtin_has_no_name_for(self):
        user = convert_authomatic(github_dump(), {"github": GITHUB_MAP})["users"][0]

        assert user["description"] == "Writes Python for a living."

    def test_the_site_map_beats_the_builtin_for_the_same_field(self):
        """``blog`` is the homepage and ``link`` is the GitHub profile URL.
        The built-in map only knows the second, so without the site's map
        every user's homepage came out as their GitHub page."""
        user = convert_authomatic(github_dump(), {"github": GITHUB_MAP})["users"][0]

        assert user["home_page"] == "https://erico.example.com"

    def test_the_builtin_still_fills_what_the_site_map_leaves(self):
        """The site's map is consulted first, not exclusively -- it names no
        location, and the dump has one."""
        user = convert_authomatic(github_dump(), {"github": GITHUB_MAP})["users"][0]

        assert user["location"] == "Berlin"

    def test_without_the_map_the_builtin_still_answers(self):
        """Omitting the argument converts exactly as before, so a caller that
        has no site is not broken by this."""
        user = convert_authomatic(github_dump())["users"][0]

        assert user["home_page"] == "https://github.com/ericof"
        assert user["description"] == ""

    def test_a_map_for_another_provider_does_not_apply(self):
        """The map is read for the provider the user actually signed in with.
        A site with GitHub and Google has two, and they disagree."""
        user = convert_authomatic(github_dump(), {"google": {"bio": "description"}})[
            "users"
        ][0]

        assert user["description"] == ""

    def test_the_first_identity_answers_for_a_field(self):
        """Two providers, both mapping ``bio``. The dump lists them in an
        order and that order decides, the same way the built-in map's first
        matching key wins."""
        d = github_dump()
        d["users"][0]["identities"].append({"provider": "google", "subject": "9"})
        maps = {
            "github": {"bio": "description"},
            "google": {"login": "description"},
        }

        user = convert_authomatic(d, maps)["users"][0]

        assert user["description"] == "Writes Python for a living."

    def test_a_field_no_document_carries_is_dropped(self):
        """``portrait`` is a real target for a login and not something a
        document carries, so a site mapping it must not put it in one."""
        maps = {"github": {"avatar_url": "portrait", "bio": "description"}}
        d = github_dump(avatar_url="https://example.com/a.png")

        user = convert_authomatic(d, maps)["users"][0]

        assert "portrait" not in user
        assert user["description"] == "Writes Python for a living."

    def test_a_structured_claim_does_not_reach_a_text_field(self):
        """A document field is text. A map naming something that resolves to
        a list means something this format cannot express, so the built-in
        map answers instead of writing ``['a', 'b']`` into a profile."""
        maps = {"github": {"topics": "description"}}
        d = github_dump(topics=["plone", "python"])

        user = convert_authomatic(d, maps)["users"][0]

        assert user["description"] == ""

    def test_an_empty_map_is_not_an_answer(self):
        """A provider configured with no map at all falls through, rather
        than blanking every field it does not name."""
        user = convert_authomatic(github_dump(), {"github": {}})["users"][0]

        assert user["fullname"] == "Érico Andrei"
        assert user["location"] == "Berlin"


class TestReportingWhatHasNoMap:
    """Falling back to the built-in map is the case that loses data, so it is
    reported rather than done quietly."""

    def test_a_provider_with_no_record_is_counted(self):
        assert unmapped_providers(github_dump(), {}) == {"github": 1}

    def test_a_configured_provider_is_not_counted(self):
        assert unmapped_providers(github_dump(), {"github": GITHUB_MAP}) == {}

    def test_users_are_counted_per_provider(self):
        d = dump()
        d["users"][0]["identities"] = [
            {"provider": "github", "subject": "1"},
            {"provider": "twitter", "subject": "2"},
        ]

        assert unmapped_providers(d, {"github": GITHUB_MAP}) == {"twitter": 1}

    def test_one_user_counts_once_per_provider(self):
        """A user with two identities from the same provider is one user with
        an unmapped provider, not two."""
        d = github_dump()
        d["users"][0]["identities"].append({"provider": "github", "subject": "7654321"})

        assert unmapped_providers(d, {}) == {"github": 1}

    def test_a_malformed_row_is_not_a_refusal(self):
        """This runs before any row has been validated -- it is what decides
        whether to warn, and a warning must not be the thing that raises. The
        importer refuses a bad row later, one at a time."""
        d = dump(
            users=[
                "not a user",
                {"userid": "u1", "identities": ["not an identity"]},
                {
                    "userid": "u2",
                    "identities": [{"provider": "github", "subject": "1"}],
                },
            ]
        )

        assert unmapped_providers(d, {}) == {"github": 1}

    def test_the_worst_offender_comes_first(self):
        """An operator reading the warning acts on the biggest number."""
        d = dump(
            users=[
                {
                    "userid": "u1",
                    "identities": [{"provider": "twitter", "subject": "1"}],
                },
                {
                    "userid": "u2",
                    "identities": [{"provider": "twitter", "subject": "2"}],
                },
                {
                    "userid": "u3",
                    "identities": [{"provider": "github", "subject": "3"}],
                },
            ]
        )

        assert list(unmapped_providers(d, {})) == ["twitter", "github"]


class TestReadingTheMapsFromTheSite:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_a_configured_map_is_read(self):
        set_providers([
            ProviderConfig(
                provider_id="github",
                driver_id="github",
                title="GitHub",
                propertymap=GITHUB_MAP,
            )
        ])

        assert site_propertymaps()["github"] == GITHUB_MAP

    def test_a_provider_with_no_map_is_left_out(self):
        """So that :func:`unmapped_providers` reports it -- an empty map and
        no map mean the same thing here."""
        set_providers([
            ProviderConfig(provider_id="github", driver_id="github", title="GitHub")
        ])

        assert "github" not in site_propertymaps()

    def test_the_site_map_reaches_the_conversion(self):
        """The whole path, from the registry to the converted document."""
        set_providers([
            ProviderConfig(
                provider_id="github",
                driver_id="github",
                title="GitHub",
                propertymap=GITHUB_MAP,
            )
        ])

        user = convert_authomatic(github_dump(), site_propertymaps())["users"][0]

        assert user["home_page"] == "https://erico.example.com"
        assert user["description"] == "Writes Python for a living."


class TestConvertedThenImported:
    """The reason the conversion produces a document rather than writing to
    the site itself: migrating is the ordinary import."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin) -> None:
        self.portal = portal
        self.plugin = plugin
        # Both providers the dump names, because the importer refuses a
        # document naming one this site does not have.
        set_providers([
            ProviderConfig(provider_id=pid, driver_id="oidc-generic", title=pid)
            for pid in ("github", "google")
        ])

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
