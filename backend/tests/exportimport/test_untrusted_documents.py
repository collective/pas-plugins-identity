"""Documents nobody vouches for.

A document is a file. It may come from this package's exporter, from an older
version of it, from a migration script somebody wrote, or from an editor. Any
of them can put the wrong type in a field, an id the site cannot hold, or a
role nobody defined. Three things must hold whatever arrives:

* nothing raises -- the answer is a refusal or a skip, with a reason;
* a refused document writes nothing at all;
* a dry run reports what the real run then does, so that reading the report
  first is worth something.

Wrong *types* are a refusal: they are the document's shape, and the operator
fixes the file. An id or a role the *site* cannot take is a skip: the rest of
the document still lands, as the importer does for every other per-record
problem.
"""

from . import PROVIDER
from . import SUBJECT
from . import USERID
from .test_importer import document
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.profiles import get_profile
from pas.plugins.identity.exportimport import import_site
from pas.plugins.identity.exportimport.schema import ExportImportError
from pas.plugins.identity.exportimport.schema import validate
from plone import api

import copy
import pytest
import re


def user(**overrides) -> dict:
    """Return the one user of :func:`document`, with some keys replaced.

    :param overrides: Keys to replace.
    :returns: A user record.
    """
    record = document()["users"][0]
    record.update(overrides)
    return record


def identity(**overrides) -> dict:
    """Return a well-formed identity record, with some keys replaced.

    :param overrides: Keys to replace.
    :returns: An identity record.
    """
    return {"provider": PROVIDER, "subject": SUBJECT, **overrides}


def group(**overrides) -> dict:
    """Return a well-formed group record, with some keys replaced.

    :param overrides: Keys to replace.
    :returns: A group record.
    """
    return {"group_id": "staff", "title": "Staff", **overrides}


#: A document with one wrong type, and the words its refusal must contain.
WRONG_TYPES = {
    "userid-integer": (document(users=[user(userid=5)]), "users[0]['userid']"),
    "userid-list": (document(users=[user(userid=["a"])]), "users[0]['userid']"),
    "login-integer": (document(users=[user(login=5)]), "users[0]['login']"),
    "fullname-list": (document(users=[user(fullname=["a"])]), "'fullname'"),
    "location-object": (document(users=[user(location={"a": 1})]), "'location'"),
    "description-integer": (document(users=[user(description=1)]), "'description'"),
    "emails-string": (
        document(users=[user(emails="erico@plone.org")]),
        "users[0]['emails']",
    ),
    "emails-holding-numbers": (
        document(users=[user(emails=["erico@plone.org", 5])]),
        "users[0]['emails']",
    ),
    "user-group-ids-string": (
        document(users=[user(group_ids="site-editors")]),
        "users[0]['group_ids']",
    ),
    "subject-integer": (
        document(users=[user(identities=[identity(subject=5)])]),
        "not text",
    ),
    "provider-list": (
        document(users=[user(identities=[identity(provider=["a"])])]),
        "not text",
    ),
    "claims-string": (
        document(users=[user(identities=[identity(claims="x")])]),
        "['claims']",
    ),
    "identity-groups-string": (
        document(users=[user(identities=[identity(groups="staff")])]),
        "['groups']",
    ),
    "group-id-integer": (document(groups=[group(group_id=5)]), "groups[0]['group_id']"),
    "group-title-list": (document(groups=[group(title=["a"])]), "'title'"),
    "group-roles-string": (
        document(groups=[group(global_roles="Manager")]),
        "'global_roles'",
    ),
    "group-roles-holding-numbers": (
        document(groups=[group(global_roles=["Editor", 5])]),
        "'global_roles'",
    ),
    "group-group-ids-object": (
        document(groups=[group(group_ids={"a": 1})]),
        "groups[0]['group_ids']",
    ),
    "container-group-integer": (
        document(groups=[group(container_group=5)]),
        "'container_group'",
    ),
}

#: An id the site cannot file a principal under, and why not.
UNUSABLE_IDS = {
    "path": "../escape",
    "slash": "a/b",
    "underscore": "__init__",
    "acquisition": "aq_parent",
    "view": "@@view",
    "traverser": "++resource++x",
    "dot": "..",
    "request": "REQUEST",
    "space-and-markup": "<b>x</b>",
}

#: Every shape above, plus the ones that are fine, for the dry-run promise.
ANY_DOCUMENT = {
    **{name: doc for name, (doc, _) in WRONG_TYPES.items()},
    **{
        f"userid-{name}": document(users=[user(userid=value)])
        for name, value in UNUSABLE_IDS.items()
    },
    **{
        f"group-id-{name}": document(groups=[group(group_id=value)])
        for name, value in UNUSABLE_IDS.items()
    },
    "fine": document(),
    "nulls-for-text": document(
        users=[user(fullname=None, location=None, login=None)],
        groups=[group(title=None, description=None, global_roles=None)],
    ),
    "undefined-role": document(groups=[group(global_roles=["NotARole", "Editor"])]),
    "computed-role": document(groups=[group(global_roles=["Authenticated"])]),
    "missing-parent": document(groups=[group(container_group="nobody")]),
    "parent-later-in-the-list": document(
        groups=[group(container_group="outer"), group(group_id="outer")]
    ),
    "one-identity-two-people": document(
        users=[user(), user(userid="somebody-else", emails=["other@example.org"])]
    ),
    "unknown-keys": document(
        users=[user(password="x", roles=["Manager"])], groups=[group(owner="x")]
    ),
}


@pytest.fixture(autouse=True)
def provider(portal) -> None:
    """Configure the provider the documents name.

    :param portal: The Plone site.
    """
    set_providers([
        ProviderConfig(provider_id=PROVIDER, driver_id="oidc-generic", title="Dex")
    ])


def written(portal) -> tuple[set[str], set[str]]:
    """Return the principals the site holds as content.

    :param portal: The Plone site.
    :returns: Userids and group ids.
    """
    from pas.plugins.identity.core.catalog import GROUP_PORTAL_TYPE
    from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
    from pas.plugins.identity.core.catalog import query_catalog

    search = query_catalog().unrestrictedSearchResults
    users = {b.userid for b in search(portal_type=PROFILE_PORTAL_TYPE)}
    groups = {b.group_id for b in search(portal_type=GROUP_PORTAL_TYPE)}
    return users, groups


class TestWrongTypesAreRefused:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    @pytest.mark.parametrize(
        "doc,expected", WRONG_TYPES.values(), ids=WRONG_TYPES.keys()
    )
    def test_validate_names_the_field(self, doc, expected):
        """The message says where, so the file can be fixed."""
        with pytest.raises(ExportImportError, match=re.escape(expected)):
            validate(doc)

    @pytest.mark.parametrize(
        "doc,expected", WRONG_TYPES.values(), ids=WRONG_TYPES.keys()
    )
    @pytest.mark.parametrize("dry_run", [True, False], ids=["dry", "wet"])
    def test_nothing_is_written(self, doc, expected, dry_run):
        """Including the groups that came before the bad user: a refusal is
        decided before the first write."""
        before = written(self.portal)

        result = import_site(doc, dry_run=dry_run)

        assert result.refused
        assert expected in result.refusals[0]
        assert written(self.portal) == before

    def test_the_check_sees_a_write(self):
        """The control for the test above: an import that does write shows
        up in what it compares."""
        before = written(self.portal)

        import_site(document())

        assert written(self.portal) != before

    def test_an_export_still_validates(self, make_user, make_group, plugin):
        """The other direction: what this package writes, it reads. The
        exporter hands tuples over in the same process, which JSON never has."""
        from pas.plugins.identity.exportimport import export_site

        make_group("site-editors", title="Site Editors")
        make_user(group_ids=("site-editors",))
        plugin.link(USERID, PROVIDER, SUBJECT, {"email": "erico@plone.org"})

        assert validate(export_site())


class TestIdsTheSiteCannotHold:
    """Skipped with the container's own reason; the rest lands."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    @pytest.mark.parametrize("value", UNUSABLE_IDS.values(), ids=UNUSABLE_IDS.keys())
    @pytest.mark.parametrize("dry_run", [True, False], ids=["dry", "wet"])
    def test_a_user(self, value, dry_run):
        doc = document(users=[user(userid=value), user()])

        result = import_site(doc, dry_run=dry_run)

        assert not result.refused
        assert result.users == [USERID]
        assert [entry.split(":")[0] for entry in result.skipped] == [f"user {value}"]

    @pytest.mark.parametrize("value", UNUSABLE_IDS.values(), ids=UNUSABLE_IDS.keys())
    @pytest.mark.parametrize("dry_run", [True, False], ids=["dry", "wet"])
    def test_a_group(self, value, dry_run):
        doc = document(groups=[group(group_id=value), group()])

        result = import_site(doc, dry_run=dry_run)

        assert not result.refused
        assert result.groups == ["staff"]
        assert [entry.split(":")[0] for entry in result.skipped] == [f"group {value}"]

    def test_nothing_is_filed_under_it(self):
        import_site(document(users=[user(userid="../escape"), user()]))

        users, _ = written(self.portal)
        assert users == {USERID}

    def test_a_skipped_group_is_nobody_s_parent(self):
        """A group filed inside one that was skipped is reported, not lost."""
        doc = document(
            groups=[group(group_id="../bad"), group(container_group="../bad")]
        )

        result = import_site(doc)

        assert "group staff: no group '../bad' to file it inside" in result.skipped

    def test_membership_of_a_skipped_group_is_dropped(self):
        doc = document(
            groups=[group(group_id="../bad")], users=[user(group_ids=["../bad"])]
        )

        import_site(doc)

        assert get_profile(USERID).group_ids == ()


class TestRoles:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_an_undefined_role_is_not_granted(self):
        import_site(document(groups=[group(global_roles=["NotARole", "Editor"])]))

        roles = api.group.get_roles(groupname="staff")
        assert "Editor" in roles
        assert "NotARole" not in roles

    @pytest.mark.parametrize("dry_run", [True, False], ids=["dry", "wet"])
    def test_an_undefined_role_is_reported(self, dry_run):
        doc = document(groups=[group(global_roles=["NotARole", "Editor"])])

        result = import_site(doc, dry_run=dry_run)

        assert result.groups == ["staff"]
        assert result.skipped == [
            "group staff: roles this site does not define, not granted: NotARole"
        ]

    def test_an_existing_group_is_held_to_it_too(self):
        import_site(document(groups=[group()]))

        import_site(document(groups=[group(global_roles=["NotARole"])]))

        assert "NotARole" not in api.group.get_roles(groupname="staff")

    def test_a_skipped_group_reports_only_its_id(self):
        """Its roles were never going to be granted."""
        doc = document(groups=[group(group_id="../bad", global_roles=["NotARole"])])

        result = import_site(doc)

        assert len(result.skipped) == 1
        assert result.skipped[0].startswith("group ../bad: ")
        assert "roles" not in result.skipped[0]


class TestTheDryRunTellsTheTruth:
    """Whatever the document, the dry run reports what the real run does."""

    @pytest.mark.parametrize("doc", ANY_DOCUMENT.values(), ids=ANY_DOCUMENT.keys())
    def test_same_report(self, doc, portal):
        dry = import_site(copy.deepcopy(doc), dry_run=True)
        wet = import_site(copy.deepcopy(doc))

        assert dry.refusals == wet.refusals
        assert (dry.users, dry.groups) == (wet.users, wet.groups)
        # Which records were skipped, not the wording: Zope words the same
        # refusal differently depending on whether the container exists yet.
        assert [s.split(": ")[0] for s in dry.skipped] == [
            s.split(": ")[0] for s in wet.skipped
        ]

    def test_a_missing_parent_is_reported(self, portal):
        """The dry run used to skip the nesting pass entirely."""
        doc = document(groups=[group(container_group="nobody")])

        result = import_site(doc, dry_run=True)

        assert result.skipped == ["group staff: no group 'nobody' to file it inside"]

    def test_a_parent_later_in_the_list_is_not_missing(self, portal):
        doc = document(groups=[group(container_group="outer"), group(group_id="outer")])

        result = import_site(doc, dry_run=True)

        assert result.skipped == []

    def test_one_identity_claimed_twice_is_reported(self, portal):
        """The dry run used to remember nothing between users."""
        doc = document(
            users=[user(), user(userid="somebody-else", emails=["other@example.org"])]
        )

        result = import_site(doc, dry_run=True)

        assert result.skipped == [
            f"identity {PROVIDER}:{SUBJECT}: already linked to {USERID}, "
            "not to somebody-else"
        ]
