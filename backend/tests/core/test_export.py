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
"""

from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from plone import api

import io
import pytest
import tarfile


PREFIX = "pas.plugins.identity.providers.github"

#: Dotted name of the schema the fixed provider fields are bound to.
IFACE = "pas.plugins.identity.core.controlpanel.interfaces.IProviderRecords"

#: The fields every provider has, whatever its driver.
FIXED_FIELDS = ("driver", "title", "enabled", "order", "propertymap")


@pytest.fixture
def exported(portal) -> str:
    """Return the registry export for a site with one provider.

    :param portal: The Plone site.
    :returns: The exported ``registry.xml``.
    """
    set_providers([
        ProviderConfig(
            provider_id="github",
            driver_id="github",
            title="GitHub",
            config={"client_id": "abc", "client_secret": "s3cr3t"},
            propertymap={"login": "username"},
        )
    ])
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
