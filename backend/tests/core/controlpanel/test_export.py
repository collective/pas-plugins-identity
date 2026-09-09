"""What a GenericSetup registry export carries for a provider.

A provider is created at runtime, so nothing guarantees a priori that the
registry exporter describes it well enough to be read back. It does, and that
is worth holding still: exporting a provider configured through the control
panel and pasting it into a profile is how a site ships its providers.

The provider's records come in two kinds, and the difference is the whole
subject of this module:

``driver``, ``title``, ``enabled``, ``order``, ``propertymap``
    Every provider has exactly these, whatever its driver, so they are bound
    to :class:`~pas.plugins.identity.core.controlpanel.interfaces.IProviderRecords`
    and the export names the interface and the field. A hand-written profile
    can therefore declare them with one ``<records interface=... />`` node.

``config.<key>``
    Which of these exist, and what type each one is, comes from the driver's
    ``config_schema`` at runtime. No fixed interface can describe a set of
    fields chosen after the interface was written, so each one carries its own
    field type -- and a profile that states them has to carry it too.

Asserting on the text of an export says the document *mentions* a provider. It
does not say the document can be read back, which is the only thing anybody
wants an export for, so the second half of this module imports what the first
half exported and compares the providers that come out.

Only this package's records are re-imported, never the whole document. Feeding
a full registry export back into a site fails on records belonging to other
packages -- ``ConstraintNotSatisfied('/news/aggregator')`` -- which is a fact
about the site, not about this export, and it is also why shipping a provider
means extracting its records by hand.
"""

from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import PROVIDERS_PREFIX
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.controlpanel.export import provider_fragment
from plone import api
from plone.app.registry.exportimport.handler import RegistryImporter
from plone.registry.interfaces import IRegistry
from zope.component import getUtility

import io
import logging
import pytest
import tarfile
import xml.etree.ElementTree as ET


PREFIX = "pas.plugins.identity.providers.github"

#: Dotted name of the schema the fixed provider fields are bound to.
IFACE = "pas.plugins.identity.core.controlpanel.interfaces.IProviderRecords"

#: The fields every provider has, whatever its driver.
FIXED_FIELDS = ("driver", "title", "enabled", "order", "propertymap")

#: An icon for the fixture. Present because it is the field whose
#: serialization is least obvious: it is stored as ``Bytes`` carrying Plone's
#: own ``filenameb64:...;datab64:...`` upload envelope, so an export that
#: mangled it would still look like an export.
#:
#: Not what gets stored. ``ProviderConfig.icon`` sanitizes on assignment and
#: normalizes attribute order on the way through, so this is the document
#: handed over rather than the one kept.
ICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
    '<path d="M1 1h14v14H1z"/></svg>'
)


def configured() -> ProviderConfig:
    """Return the provider both halves of this module work from.

    Every field a provider has is filled in, including the two maps and the
    icon: a round trip that only carries the fields somebody remembered to set
    proves the fields somebody remembered to set.

    :returns: The provider.
    """
    return ProviderConfig(
        provider_id="github",
        driver_id="github",
        title="GitHub",
        icon=ICON,
        background_color="#24292f",
        foreground_color="#ffffff",
        config={"client_id": "abc", "client_secret": "s3cr3t"},
        propertymap={"name": "fullname"},
        groupmap={"admins": "Site Administrators"},
    )


def snapshot(provider: ProviderConfig) -> dict:
    """Return a provider's state as plain values.

    ``ProviderConfig`` has no ``__eq__``, so comparing two of them compares
    identity and passes for the wrong reason. This compares what was stored.

    :param provider: The provider to describe.
    :returns: Its fields.
    """
    return {
        "provider_id": provider.provider_id,
        "driver_id": provider.driver_id,
        "title": provider.title,
        "enabled": provider.enabled,
        "show_in_login": provider.show_in_login,
        "icon": provider.icon,
        "background_color": provider.background_color,
        "foreground_color": provider.foreground_color,
        "config": provider.config,
        "propertymap": provider.propertymap,
        "groupmap": provider.groupmap,
    }


class Environ:
    """The two methods ``RegistryImporter`` asks its environment for.

    ``shouldPurge`` answers ``False`` deliberately: a purge empties the whole
    registry, and an import that has to empty the site first is not the
    operation being tested.
    """

    def getLogger(self, name: str):
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


def import_document(document: bytes) -> None:
    """Import a registry document into the site.

    :param document: The XML, as bytes. ``lxml`` refuses a ``str`` carrying an
        encoding declaration, and the exporter emits one.
    """
    RegistryImporter(getUtility(IRegistry), Environ()).importDocument(document)


def parsed(document: str) -> ET.Element:
    """Parse a document this module produced.

    :param document: The XML.
    :returns: Its root element.
    """
    # S314 warns about parsing untrusted input. Every document parsed in this
    # module was generated a line or two earlier by the registry exporter.
    return ET.fromstring(document.encode())  # noqa: S314


def provider_records(exported: str) -> bytes:
    """Return only this package's provider records, as a document.

    What an operator does by hand when shipping a provider, and the only part
    of a registry export that can be fed back in.

    :param exported: The full ``registry.xml``.
    :returns: A ``<registry>`` document carrying the provider's records.
    """
    fragment = ET.Element("registry")
    for record in parsed(exported).findall("record"):
        if record.get("name", "").startswith(PROVIDERS_PREFIX):
            fragment.append(record)
    return ET.tostring(fragment)


@pytest.fixture
def exported(portal) -> str:
    """Return the registry export for a site with one provider.

    :param portal: The Plone site.
    :returns: The exported ``registry.xml``.
    """
    set_providers([configured()])
    result = api.portal.get_tool("portal_setup").runExportStep("plone.app.registry")
    with tarfile.open(fileobj=io.BytesIO(result["tarball"])) as tar:
        name = next(n for n in tar.getnames() if n.endswith("registry.xml"))
        return tar.extractfile(name).read().decode()


class TestRegistryExport:
    def test_every_provider_record_is_exported(self, exported: str):
        for field in FIXED_FIELDS:
            assert f'<record name="{PREFIX}.{field}"' in exported

    def test_the_fixed_fields_name_their_interface(self, exported: str):
        """Which is what lets a profile declare them without restating a
        field type per record."""
        for field in FIXED_FIELDS:
            assert (
                f'<record name="{PREFIX}.{field}" interface="{IFACE}" field="{field}">'
            ) in exported

    def test_driver_settings_are_exported(self, exported: str):
        assert f'<record name="{PREFIX}.config.client_id">' in exported

    def test_a_driver_setting_belongs_to_no_interface(self, exported: str):
        """The claim the ``<field>`` element in a profile rests on: with no
        interface to inherit from, a record that does not carry its own type
        cannot be imported into a site that does not already have it."""
        assert f'<record name="{PREFIX}.config.client_id" interface=' not in exported

    def test_a_record_carries_its_own_field_type(self, exported: str):
        """An export states the type either way -- it is a backup, and a
        backup that leans on an interface still being importable is not
        one."""
        assert "plone.registry.field.Password" in exported
        assert "plone.registry.field.Dict" in exported

    def test_typed_values_survive(self, exported: str):
        assert "<value>github</value>" in exported

    def test_a_secret_is_exported_in_the_clear(self, exported: str):
        """Not a leak to fix here -- a registry export is a backup of the
        registry -- but the reason an export is not something to paste into
        a public repository without reading it first."""
        assert "<value>s3cr3t</value>" in exported


class TestTheIconSurvivesTheExport:
    """The field whose serialization is least obvious.

    An icon is stored as ``Bytes`` carrying Plone's own upload envelope, so
    it is the one field where "the export mentions it" and "the export can be
    read back" are visibly different claims.
    """

    def test_the_icon_is_exported(self, exported: str):
        assert f'<record name="{PREFIX}.icon"' in exported

    def test_it_is_exported_as_bytes(self, exported: str):
        """Not text. The record holds the upload envelope, not the SVG."""
        assert "plone.registry.field.Bytes" in exported

    def test_the_envelope_survives_whole(self, exported: str):
        """Both halves. ``datab64`` alone would be an icon nothing can name,
        and Plone's file widgets produce the pair."""
        assert "filenameb64:" in exported
        assert "datab64:" in exported


class TestTheExportRoundTrips:
    """Export it, wipe it, import it, and get the same provider back.

    This is what an export is for, and asserting on the text of one never
    says whether it is true.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, exported: str) -> None:
        self.portal = portal
        self.before = snapshot(get_providers()[0])
        self.fragment = provider_records(exported)

    def reimport(self) -> ProviderConfig:
        """Wipe the provider and read it back from the fragment.

        :returns: The provider as it comes back.
        """
        set_providers([])
        assert get_providers() == []

        import_document(self.fragment)
        return get_providers()[0]

    def test_the_provider_comes_back_identical(self):
        """Every field at once, so a round trip cannot be reported as working
        because the two or three fields somebody thought of survived."""
        assert snapshot(self.reimport()) == self.before

    def test_the_icon_comes_back_as_the_document(self):
        """Stated separately because it is the one field that changes shape on
        the way in and out: the sanitized document in memory, the upload
        envelope in the record. What comes back has to be the document.

        Compared against what was stored rather than against ``ICON``: the
        setter sanitizes on assignment and normalizes attribute order while it
        is there, so ``ICON`` is what was handed over and never what was kept.
        """
        icon = self.reimport().icon

        assert icon == self.before["icon"]
        assert icon.startswith("<svg")
        assert "datab64:" not in icon
        assert 'd="M1 1h14v14H1z"' in icon

    def test_a_typed_setting_comes_back_typed(self):
        """Not the string ``'False'``, and not the string
        ``"('read:user', 'user:email')"``. A record that carries its own field
        type is the whole reason this works."""
        config = self.reimport().config

        assert config["create_user"] is True
        assert config["accept_string_booleans"] is False
        assert tuple(config["scope"]) == ("read:user", "user:email")

    def test_the_secret_comes_back(self):
        """It goes in the clear, so it comes back. Worth an assertion because
        a masked export would be a backup that silently restores a provider
        which cannot authenticate."""
        assert self.reimport().config["client_secret"] == "s3cr3t"


class TestTheFormAProfileShips:
    """The grouped ``<records interface= prefix=>`` node.

    Not what the exporter emits -- it writes one ``<record>`` per field, each
    naming the interface -- but it is what a hand-written profile uses, and
    the two have to mean the same thing.

    The reason for the split is the same one the module opens with: the
    grouped node cannot carry a ``config.*`` record at all, because those are
    not fields on ``IProviderRecords``. Each one is restated below with its
    own ``<field type=>``, which is exactly the tedium
    ``@identity-providers/<id>/export`` exists to remove.
    """

    PROFILE = f"""<registry>
  <records interface="{IFACE}" prefix="{PROVIDERS_PREFIX}acme">
    <value key="driver">github</value>
    <value key="title">Acme</value>
    <value key="enabled">True</value>
    <value key="order">0</value>
  </records>
  <record name="{PROVIDERS_PREFIX}acme.config.client_id">
    <field type="plone.registry.field.TextLine">
      <required>False</required>
    </field>
    <value>acme-id</value>
  </record>
  <record name="{PROVIDERS_PREFIX}acme.config.create_user">
    <field type="plone.registry.field.Bool">
      <required>False</required>
    </field>
    <value>False</value>
  </record>
</registry>""".encode()

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        set_providers([])
        import_document(self.PROFILE)
        self.provider = get_provider("acme")

    def test_the_provider_exists(self):
        """A profile can declare a provider that nothing created at runtime."""
        assert self.provider is not None

    def test_the_grouped_node_filled_the_fixed_fields(self):
        """One node, no field type restated, four values."""
        assert self.provider.driver_id == "github"
        assert self.provider.title == "Acme"
        assert self.provider.enabled is True

    def test_a_field_the_node_left_out_takes_the_schema_default(self):
        """Which is why a profile can be short: binding the interface creates
        every record it declares, whether or not a value is given."""
        assert self.provider.show_in_login is True
        assert self.provider.groupmap == {}

    def test_a_config_record_carries_its_own_type(self):
        """The half the grouped node cannot express."""
        assert self.provider.config["client_id"] == "acme-id"
        assert self.provider.config["create_user"] is False

    def test_the_rest_of_the_config_is_the_drivers_default(self):
        """A profile states what it changes; the driver supplies the rest."""
        assert tuple(self.provider.config["scope"]) == ("read:user", "user:email")


class TestTheProviderFragment:
    """What ``@identity-providers/<id>/export`` emits, and that it imports.

    The endpoint exists so that shipping a provider stops being a
    hand-extraction. That is only true if what it emits can be pasted into
    ``profiles/default/registry/`` and read back, so the round trip is
    asserted here rather than the shape being eyeballed.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        set_providers([configured()])
        self.before = snapshot(get_providers()[0])
        self.xml = provider_fragment("github")

    def test_it_is_well_formed(self):
        """Parsed rather than pattern-matched. A fragment that only looks like
        XML is the failure this is here for."""
        assert parsed(self.xml).tag == "registry"

    def test_the_fixed_fields_are_one_grouped_node(self):
        """The form a hand-written profile uses, and not what the registry
        exporter emits: it writes one ``<record>`` per field, each restating
        the interface, the type, the title and the description."""
        root = parsed(self.xml)
        records = root.findall("records")

        assert len(records) == 1
        assert records[0].get("interface") == IFACE
        assert records[0].get("prefix") == f"{PROVIDERS_PREFIX}github"
        keys = {value.get("key") for value in records[0].findall("value")}
        assert set(FIXED_FIELDS) <= keys

    def test_no_config_record_is_in_the_grouped_node(self):
        """It cannot be: a driver setting is not a field on the interface, so
        a value under that node would import against nothing."""
        root = parsed(self.xml)

        keys = {value.get("key") for value in root.find("records").findall("value")}
        assert not any(key.startswith("config.") for key in keys)

    def test_every_config_record_carries_its_own_type(self):
        """The reason they stay separate. With no interface to inherit from, a
        record without a type cannot be imported into a site that has never
        seen this provider."""
        root = parsed(self.xml)
        records = root.findall("record")

        assert records
        for record in records:
            assert record.get("name").startswith(f"{PROVIDERS_PREFIX}github.config.")
            assert record.find("field") is not None
            assert record.find("field").get("type", "").startswith("plone.registry.")

    def test_the_fragment_imports_into_a_site_without_the_provider(self):
        """The claim the endpoint rests on, and the only one worth having."""
        set_providers([])
        assert get_providers() == []

        import_document(self.xml.encode())

        assert snapshot(get_providers()[0]) == self.before

    def test_the_icon_survives_the_fragment(self):
        """It is stored as ``Bytes`` carrying an upload envelope, and it is
        moved between elements on the way into the grouped node, so it is the
        value most likely to be the one that does not come back."""
        set_providers([])
        import_document(self.xml.encode())

        assert get_providers()[0].icon == self.before["icon"]

    def test_the_secret_is_in_the_clear(self):
        """Deliberate, and the reason a fragment is not something to paste
        into a public repository without reading it first. Masking it would
        produce a fragment that imports a provider unable to authenticate."""
        assert "s3cr3t" in self.xml

    def test_it_is_shorter_than_the_exporter_form(self):
        """The point of the grouped node. Not a micro-optimisation: the
        difference is a fragment somebody will read against one they will
        not."""
        result = api.portal.get_tool("portal_setup").runExportStep("plone.app.registry")
        with tarfile.open(fileobj=io.BytesIO(result["tarball"])) as tar:
            name = next(n for n in tar.getnames() if n.endswith("registry.xml"))
            full = tar.extractfile(name).read().decode()

        assert len(self.xml) < len(provider_records(full))
