"""What a group map's local side is, and where an unknown group is caught (#144).

The local side was free text, so a typo -- or a group's title where its id
belongs -- saved without complaint and granted nothing at every login. It is
a pick from the site's groups on the form now, and the API refuses the same
rows. The registry's own field stays text, because a profile may ship a map
before the step that creates its group; such a record is logged as it is
written instead of refused.
"""

from pas.plugins.identity.core.controlpanel import check_groupmap
from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.controlpanel import InvalidGroupMap
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.controlpanel import unknown_groups
from pas.plugins.identity.core.controlpanel.interfaces import IProviderForm
from pas.plugins.identity.core.controlpanel.interfaces import IProviderRecords
from pas.plugins.identity.core.services.schema import jsonschema_for
from pas.plugins.identity.core.vocabularies.groups import GROUPS_VOCABULARY
from plone.app.registry.exportimport.handler import RegistryImporter
from plone.registry.interfaces import IRegistry
from zope.component import getUtility
from zope.schema.interfaces import IChoice
from zope.schema.interfaces import ITextLine

import logging
import pytest


#: A provider declared by a profile, mapping one group.
PROFILE_PROVIDER = """<registry>
  <records
      interface="pas.plugins.identity.core.controlpanel.interfaces.IProviderRecords"
      prefix="pas.plugins.identity.providers.plone-org">
    <value key="driver">plone-identity</value>
    <value key="title">Plone</value>
    <value key="groupmap">
      <element key="acl-plone-org-br-editors">{local}</element>
    </value>
  </records>
</registry>
"""


class _Environ:
    """The two methods ``RegistryImporter`` asks its environment for."""

    def getLogger(self, name: str) -> logging.Logger:
        """Return a logger.

        :param name: Logger name.
        :returns: The logger.
        """
        return logging.getLogger(name)

    def shouldPurge(self) -> bool:
        """Never purge.

        :returns: ``False``.
        """
        return False


def import_provider(local: str) -> None:
    """Import :data:`PROFILE_PROVIDER` mapping to one local group.

    :param local: The local group id the profile names.
    """
    document = PROFILE_PROVIDER.format(local=local)
    RegistryImporter(getUtility(IRegistry), _Environ()).importDocument(
        document.encode()
    )


class TestTheFields:
    """Read off the interfaces, so a change on either side is a red test."""

    def test_the_record_stays_text(self):
        """A ``Choice`` here would refuse a profile that ships its map before
        its groups."""
        assert ITextLine.providedBy(IProviderRecords["groupmap"].value_type)

    def test_the_form_picks_from_the_site_s_groups(self):
        value_type = IProviderForm["groupmap"].value_type

        assert IChoice.providedBy(value_type)
        assert value_type.vocabularyName == GROUPS_VOCABULARY

    def test_the_provider_side_stays_text_on_the_form(self):
        """The far end's own group names, which nothing here enumerates."""
        assert not IChoice.providedBy(IProviderForm["groupmap"].key_type)

    def test_every_other_field_is_the_records_own(self):
        assert set(IProviderForm.names(all=True)) == set(
            IProviderRecords.names(all=True)
        )
        assert IProviderForm["propertymap"] is IProviderRecords["propertymap"]


class TestTheCheck:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_a_group_the_site_has_passes(self):
        check_groupmap({"acl-plone-org-br-editors": "Site Administrators"})

    def test_a_group_it_does_not_have_is_refused(self):
        """The report: an id typed by hand, wrong, and nothing said so."""
        with pytest.raises(InvalidGroupMap) as caught:
            check_groupmap({"acl-plone-org-br-editors": "Site Admins"})

        assert "'Site Admins'" in str(caught.value)

    def test_a_virtual_group_is_refused(self):
        """Nobody can be added to ``AuthenticatedUsers``, so the picker does
        not offer it and the check agrees."""
        with pytest.raises(InvalidGroupMap) as caught:
            check_groupmap({"staff": "AuthenticatedUsers"})

        assert "'AuthenticatedUsers'" in str(caught.value)

    def test_a_cleared_row_passes(self):
        """How the form represents a row an operator emptied."""
        check_groupmap({"staff": "", "team": "  "})

    def test_every_missing_group_is_named(self):
        assert unknown_groups({"a": "Nope", "b": "Reviewers", "c": "Also nope"}) == [
            "Also nope",
            "Nope",
        ]

    def test_a_group_that_is_content_passes(self, make_group):
        make_group("site-editors")

        check_groupmap({"editors": "site-editors"})


class TestStoringIsNotRefused:
    """``set_providers`` is what every write goes through, not only an edit."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_a_stale_group_does_not_block_the_other_providers(self):
        """Deleting one provider rewrites the rest; a group removed since one
        of them was saved must not make that impossible."""
        set_providers([
            ProviderConfig(
                provider_id="plone-org",
                driver_id="plone-identity",
                title="Plone",
                groupmap={"editors": "gone"},
            )
        ])

        assert get_provider("plone-org").groupmap == {"editors": "gone"}


class TestAProfileImport:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_a_missing_group_is_stored(self):
        """Refusing would make a profile that creates its groups later
        uninstallable."""
        import_provider("Site Admins")

        assert get_provider("plone-org").groupmap == {
            "acl-plone-org-br-editors": "Site Admins"
        }

    def test_and_logged(self, caplog):
        with caplog.at_level(logging.WARNING):
            import_provider("Site Admins")

        assert "'plone-org' maps a group to 'Site Admins'" in caplog.text

    def test_a_group_the_site_has_is_not_logged(self, caplog):
        with caplog.at_level(logging.WARNING):
            import_provider("Site Administrators")

        assert "maps a group" not in caplog.text


class TestWhatTheEndpointServes:
    """The frontend builds the picker from this and nothing else."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_) -> None:
        self.portal = portal
        schema = jsonschema_for(IProviderForm, portal, request_)
        self.groupmap = schema["properties"]["groupmap"]

    def test_the_local_side_carries_the_groups_vocabulary(self):
        vocabulary = self.groupmap["value_type"]["additional"]["vocabulary"]

        assert vocabulary["@id"].endswith(f"/@vocabularies/{GROUPS_VOCABULARY}")

    def test_the_provider_side_carries_none(self):
        assert "vocabulary" not in self.groupmap["key_type"]["additional"]
