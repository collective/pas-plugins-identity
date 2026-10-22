"""The fields a property map may write beyond the shipped text fields (#143).

A login can fill a behavior's field, so a document carries it: under
``fields``, serialized and read back by ``plone.restapi``'s field adapters.
"""

from . import ADDRESS
from . import USERID
from pas.plugins.identity.core.profiles import get_profile
from pas.plugins.identity.exportimport import export_site
from pas.plugins.identity.exportimport import import_site
from pas.plugins.identity.exportimport.schema import DOCUMENT_VERSION
from pas.plugins.identity.exportimport.schema import ExportImportError
from pas.plugins.identity.exportimport.schema import USER_EXTRA_FIELDS
from pas.plugins.identity.exportimport.schema import validate
from tests.extra_profile_fields import IAnnotatedProfileFields

import json
import pytest


SOCIAL_LINKS = [
    {
        "@id": "github",
        "id": "github",
        "title": "GitHub",
        "href": [{"@id": "https://github.com/example", "title": "GitHub"}],
    },
]


def document(**fields) -> dict:
    """Return a document with one user carrying these extra fields.

    :param fields: Field name to value, under ``fields``.
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
                USER_EXTRA_FIELDS: fields,
                "identities": [],
            }
        ],
    }


def exported_user() -> dict:
    """Export this site and return its one user.

    :returns: The user record.
    """
    return export_site()["users"][0]


class TestTheExport:
    @pytest.fixture(autouse=True)
    def _setup(self, extra_profile_fields, plugin, make_user) -> None:
        self.portal = extra_profile_fields
        self.profile = make_user(
            social_links=SOCIAL_LINKS, tags=("plone", "python"), age=42
        )

    def test_a_list_of_mappings_is_carried(self):
        assert exported_user()[USER_EXTRA_FIELDS]["social_links"] == SOCIAL_LINKS

    def test_a_tuple_is_carried_as_a_list(self):
        """JSON's shape, which is what the REST API serves too."""
        assert exported_user()[USER_EXTRA_FIELDS]["tags"] == ["plone", "python"]

    def test_a_number_is_carried(self):
        assert exported_user()[USER_EXTRA_FIELDS]["age"] == 42

    def test_the_shipped_text_fields_stay_where_they_were(self):
        """A reader from before ``fields`` still finds them at the top."""
        user = exported_user()

        assert user["fullname"] == "Érico Andrei"
        assert "fullname" not in user[USER_EXTRA_FIELDS]

    def test_the_document_survives_json(self):
        document = export_site()

        assert json.loads(json.dumps(document)) == document


class TestAFieldStoredByAFactory:
    @pytest.fixture(autouse=True)
    def _setup(self, extra_profile_fields, plugin) -> None:
        self.portal = extra_profile_fields

    def test_is_exported(self, make_user):
        IAnnotatedProfileFields(make_user()).nickname = "ada"

        assert exported_user()[USER_EXTRA_FIELDS] == {"nickname": "ada"}

    def test_is_imported_through_the_factory(self):
        import_site(document(nickname="ada"))

        assert IAnnotatedProfileFields(get_profile(USERID)).nickname == "ada"


class TestAnUnfilledField:
    def test_is_left_out(self, extra_profile_fields, plugin, make_user):
        make_user(age=42)

        assert exported_user()[USER_EXTRA_FIELDS] == {"age": 42}

    def test_no_key_when_there_is_nothing(self, portal, plugin, make_user):
        """A site with no such behavior exports what it always did."""
        make_user()

        assert USER_EXTRA_FIELDS not in exported_user()


class TestTheImport:
    @pytest.fixture(autouse=True)
    def _setup(self, extra_profile_fields, plugin) -> None:
        self.portal = extra_profile_fields

    def test_a_new_user_gets_the_fields(self):
        import_site(document(social_links=SOCIAL_LINKS, tags=["plone"], age=42))
        profile = get_profile(USERID)

        assert profile.social_links == SOCIAL_LINKS
        assert profile.tags == ("plone",)
        assert profile.age == 42

    def test_an_existing_user_gets_them_too(self, make_user):
        make_user(age=7)

        import_site(document(age=42))

        assert get_profile(USERID).age == 42

    def test_a_value_the_field_refuses_is_reported(self):
        result = import_site(document(age="old", tags=["plone"]))

        assert any("'age'" in reason for reason in result.skipped)
        assert get_profile(USERID).tags == ("plone",)

    def test_the_user_still_arrives(self):
        result = import_site(document(age="old"))

        assert result.users == [USERID]

    def test_a_dry_run_writes_nothing(self, make_user):
        make_user(age=7)

        import_site(document(age=42), dry_run=True)

        assert get_profile(USERID).age == 7


class TestASiteWithoutTheBehavior:
    """The importing site decides what its user type has."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin) -> None:
        self.portal = portal

    def test_the_field_is_reported(self):
        result = import_site(document(social_links=SOCIAL_LINKS))

        assert result.skipped == [
            f"user {USERID}: field 'social_links' is not a field this site's "
            "user type lets a document write"
        ]

    def test_so_is_a_field_no_map_may_write(self):
        """``fields`` is not a back door to the login or membership."""
        result = import_site(document(group_ids=["Administrators"]))

        assert result.skipped
        assert get_profile(USERID).group_ids == ()

    def test_reported_on_a_dry_run_as_well(self):
        result = import_site(document(social_links=SOCIAL_LINKS), dry_run=True)

        assert len(result.skipped) == 1


class TestTheDocumentFormat:
    def test_fields_must_be_an_object(self):
        with pytest.raises(ExportImportError):
            validate(document() | {"users": [{"userid": USERID, "fields": []}]})

    def test_a_document_without_fields_is_valid(self):
        doc = document()
        del doc["users"][0][USER_EXTRA_FIELDS]

        assert validate(doc) is doc
