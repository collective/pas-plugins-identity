"""Export a site, import the document, and get the same site back.

The round trip is the only assertion that covers both halves at once, and it
is the one an operator actually depends on: a backup nobody has restored is
not a backup. Each half is also tested on its own next door, because a round
trip that is wrong in *both* directions passes.
"""

from . import ADDRESS
from . import CLAIMS
from . import LOGIN
from . import PROVIDER
from . import SUBJECT
from . import USERID
from pas.plugins.identity.core.container import get_container
from pas.plugins.identity.core.container import GROUP
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.pas.profile import PLUGIN_ID as PROFILE_PLUGIN_ID
from pas.plugins.identity.exportimport import export_site
from pas.plugins.identity.exportimport import import_site
from plone import api

import json
import pytest


class TestARoundTrip:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin, make_user, make_group) -> None:
        self.portal = portal
        self.plugin = plugin
        # The importer refuses a document naming a provider this site does
        # not have, so the round trip has to configure the one it links.
        set_providers([
            ProviderConfig(provider_id=PROVIDER, driver_id="oidc-generic", title="Dex")
        ])
        make_group("site-editors", title="Site Editors")
        make_group("staff", title="Staff", group_ids=("site-editors",))
        self.profile = make_user(location="Berlin", group_ids=("site-editors",))
        record = self.plugin.link(USERID, PROVIDER, SUBJECT, CLAIMS)
        record.groups = ("site-editors",)

    def test_the_document_survives_json(self):
        """It is written to a file, so anything in it has to serialize. A
        ``datetime`` left in by accident would fail here and nowhere else."""
        document = export_site()

        assert json.loads(json.dumps(document)) == document

    def test_a_second_import_changes_nothing(self):
        """Idempotence, which is what makes a document safe to re-run. A
        migration you cannot re-run is one nobody dares run."""
        document = export_site()

        first = import_site(document)
        second = import_site(document)

        assert not first.refused
        assert second.users == first.users
        assert second.groups == first.groups
        # Every identity is already ours the second time, so none is written.
        assert second.identities == []

    def test_importing_into_itself_preserves_the_user(self):
        """The round trip proper, against the site that produced it."""
        assert not import_site(export_site()).refused

        after = export_site()
        user = after["users"][0]

        assert user["userid"] == USERID
        assert user["login"] == LOGIN
        assert user["emails"] == [ADDRESS]
        assert user["location"] == "Berlin"
        assert user["group_ids"] == ["site-editors"]

    def test_the_identity_join_survives(self):
        """The whole reason this package exists rather than
        ``plone.exportimport`` alone."""
        assert not import_site(export_site()).refused

        identities = export_site()["users"][0]["identities"]

        assert len(identities) == 1
        assert identities[0]["provider"] == PROVIDER
        assert identities[0]["subject"] == SUBJECT
        assert identities[0]["groups"] == ["site-editors"]

    def test_the_nesting_survives(self):
        """A group inside a group, which is the case that needs the third
        pass -- the nesting can name a group that comes later in the list."""
        assert not import_site(export_site()).refused

        groups = {group["group_id"]: group for group in export_site()["groups"]}

        assert groups["staff"]["group_ids"] == ["site-editors"]


class TestAHierarchyRoundTrips:
    """The other way of writing the nesting, which is a *place* rather than a
    field and therefore needs a pass of its own on the way back in.

    Without it a document restores every group into the one configured
    container, so a restored site keeps the memberships and loses the shape
    somebody built -- silently, since the access all still resolves.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_group) -> None:
        self.portal = portal
        staff = make_group("staff", title="Staff")
        engineering = make_group("engineering", title="Engineering", container=staff)
        make_group("developers", title="Developers", container=engineering)
        # Resolved after the first group, which is what creates the container.
        self.groups = get_container(kind=GROUP)
        self.plugin = portal.acl_users[PROFILE_PLUGIN_ID]

    def _exported(self) -> dict:
        """Return the exported groups, keyed by group id.

        :returns: Group records.
        """
        return {group["group_id"]: group for group in export_site()["groups"]}

    def test_the_container_is_exported(self):
        """One record per group, each naming the group it sits in."""
        groups = self._exported()

        assert groups["staff"]["container_group"] == ""
        assert groups["engineering"]["container_group"] == "staff"
        assert groups["developers"]["container_group"] == "engineering"

    def test_the_hierarchy_is_rebuilt(self):
        """Into a site whose groups have been flattened, which is what a
        restore amounts to once every group has been created in the one
        container the importer files them in."""
        document = export_site()
        # Flatten it, innermost first so each move is out of a group that is
        # still where it was. This is the state a fresh import produces, and
        # it is one an operator can produce by hand too.
        with api.env.adopt_roles(["Manager"]):
            api.content.move(
                source=self.groups["staff"]["engineering"]["developers"],
                target=self.groups,
            )
            api.content.move(
                source=self.groups["staff"]["engineering"], target=self.groups
            )
        assert self._exported()["developers"]["container_group"] == ""

        assert not import_site(document).refused

        groups = self._exported()

        assert groups["engineering"]["container_group"] == "staff"
        assert groups["developers"]["container_group"] == "engineering"

    def test_a_second_import_leaves_the_shape_alone(self):
        """The re-import case: every group is already where the document
        says, and moving it again would be a write for nothing."""
        assert not import_site(export_site()).refused
        assert not import_site(export_site()).refused

        groups = self._exported()

        assert groups["developers"]["container_group"] == "engineering"

    def test_membership_follows_the_rebuilt_hierarchy(self):
        """The point of restoring the shape rather than only the records."""
        assert not import_site(export_site()).refused

        assert set(self.plugin.getNestedGroupIds("staff")) == {
            "engineering",
            "developers",
        }
