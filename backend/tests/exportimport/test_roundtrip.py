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
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.exportimport import export_site
from pas.plugins.identity.exportimport import import_site

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
