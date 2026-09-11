"""A provider icon written by an import is held to the control panel's rule.

``IProviderRecords.icon`` declares its SVG check as a field constraint, and
``plone.registry`` stores fields without their constraints, so a profile
import accepted any bytes at all. A document that was not an SVG surfaced at
the next read of the providers, as an exception out of ``@login-providers``
for every provider on the site. An SVG carrying a script was stored as it
came, so the registry and every later export held the unsafe version.

Both forms a profile can use are covered, because they reach the registry
through different events: ``<records interface=...>`` registers the fields and
then assigns each value, which is a modification, while ``<record>`` creates
the record and its value in one step, which is an addition.
"""

from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import PROVIDERS_PREFIX
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.controlpanel.export import provider_fragment
from pas.plugins.identity.core.subscribers.providers import icon_provider
from pas.plugins.identity.core.utils.svg import decode_upload
from pas.plugins.identity.core.utils.svg import InvalidSVG
from pas.plugins.identity.core.utils.svg import sanitize
from plone.app.registry.exportimport.handler import RegistryImporter
from plone.registry.interfaces import IRegistry
from xml.sax.saxutils import escape
from zope.component import getUtility

import logging
import pytest


#: The value from the report: the ``repr`` of empty bytes, written as text.
REPORTED = "b''"

#: A document the sanitizer keeps.
ICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
    '<path d="M1 1h14v14H1z"/></svg>'
)

#: A valid SVG carrying a script, which the sanitizer drops with its contents.
SCRIPTED = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
    "<script>alert(document.cookie)</script>"
    '<path d="M1 1h14v14H1z"/></svg>'
)

#: A provider in the form a hand-written profile uses.
GROUPED = """<registry>
  <records
      interface="pas.plugins.identity.core.controlpanel.interfaces.IProviderRecords"
      prefix="pas.plugins.identity.providers.broken">
    <value key="driver">github</value>
    <value key="title">Broken</value>
    {icon}
  </records>
</registry>
"""

#: One icon record, in the form the registry exporter writes.
SINGLE = """<registry>
  <record name="pas.plugins.identity.providers.broken.icon">
    <field type="plone.registry.field.Bytes">
      <title>Icon</title>
      <required>False</required>
    </field>
    <value>{value}</value>
  </record>
</registry>
"""


class Environ:
    """The two methods ``RegistryImporter`` asks its environment for."""

    def getLogger(self, name: str) -> logging.Logger:
        """Return a logger.

        :param name: Logger name.
        :returns: The logger.
        """
        return logging.getLogger(name)

    def shouldPurge(self) -> bool:
        """Never purge: emptying the registry is not what is being tested.

        :returns: ``False``.
        """
        return False


def import_document(document: str) -> None:
    """Import a registry document into the site.

    :param document: The XML.
    """
    RegistryImporter(getUtility(IRegistry), Environ()).importDocument(document.encode())


def grouped(icon: str | None) -> str:
    """Return the grouped provider document with the given icon.

    :param icon: The icon value as a profile would write it, or ``None`` for
        an empty ``<value>`` element.
    :returns: The XML.
    """
    if icon is None:
        node = '<value key="icon" />'
    else:
        node = f'<value key="icon">{escape(icon)}</value>'
    return GROUPED.format(icon=node)


def stored_icon(provider_id: str = "broken") -> bytes:
    """Return the raw value of a provider's icon record.

    The record itself rather than ``get_provider``: reading a provider
    sanitizes its icon on the way out, which is exactly the step that hid an
    unsafe stored value.

    :param provider_id: The provider.
    :returns: The stored bytes.
    """
    return getUtility(IRegistry).records[f"{PROVIDERS_PREFIX}{provider_id}.icon"].value


class TestTheGroupedForm:
    """``<records interface=...>``, which arrives as a modification."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_the_reported_value_is_refused(self):
        """The document from the report, which used to import cleanly."""
        with pytest.raises(InvalidSVG):
            import_document(grouped(REPORTED))

    def test_the_refusal_names_the_provider(self):
        """An import carries many records; the error says which one."""
        with pytest.raises(InvalidSVG, match="'broken'"):
            import_document(grouped(REPORTED))

    def test_markup_that_is_not_svg_is_refused(self):
        """Parseable is not enough: the login page inlines an ``svg``."""
        with pytest.raises(InvalidSVG):
            import_document(grouped("<html><body/></html>"))

    def test_an_existing_provider_is_refused_too(self):
        """An import over a provider the control panel created."""
        set_providers([
            ProviderConfig(
                provider_id="broken", driver_id="github", title="Broken", icon=ICON
            )
        ])

        with pytest.raises(InvalidSVG):
            import_document(grouped(REPORTED))

    def test_an_empty_icon_is_accepted(self):
        """No icon is an ordinary provider."""
        import_document(grouped(None))

        assert get_provider("broken").icon == ""

    def test_an_svg_icon_is_accepted(self):
        """And the provider reads back with it."""
        import_document(grouped(ICON))

        assert "<svg" in get_provider("broken").icon


class TestTheSingleRecordForm:
    """``<record>``, which arrives as an addition."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_the_reported_value_is_refused(self):
        """The same value through the other event."""
        with pytest.raises(InvalidSVG, match="'broken'"):
            import_document(SINGLE.format(value=REPORTED))

    def test_an_svg_icon_is_accepted(self):
        """The check refuses bad icons, not new records."""
        import_document(SINGLE.format(value=escape(ICON)))


class TestWhatAnImportStores:
    """The stored value, read straight off the record.

    Checked decoded: the control panel stores the icon inside a base64
    envelope, so the raw bytes would not show a script whether or not one had
    survived.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_a_script_is_not_stored(self):
        """The registry, and every export taken from it, holds the safe
        version, which is what sanitizing on save exists to guarantee."""
        import_document(grouped(SCRIPTED))

        source = decode_upload(stored_icon())

        assert "script" not in source
        assert "<path" in source

    def test_a_script_is_not_stored_through_a_single_record(self):
        """The addition event is held to the same rule."""
        import_document(SINGLE.format(value=escape(SCRIPTED)))

        assert "script" not in decode_upload(stored_icon())

    def test_an_import_stores_what_the_control_panel_stores(self):
        """The same bytes either way, so a provider created in the control
        panel and one shipped in a profile are the same records."""
        set_providers([
            ProviderConfig(
                provider_id="broken",
                driver_id="github",
                title="Broken",
                icon=SCRIPTED,
            )
        ])
        through_the_control_panel = stored_icon()
        set_providers([])

        import_document(grouped(SCRIPTED))

        assert stored_icon() == through_the_control_panel

    def test_sanitizing_twice_changes_nothing(self):
        """What stops the rewrite. Storing the sanitized value fires the
        modified event again, and that pass must find nothing left to change
        or the subscriber would never stop writing."""
        once = sanitize(SCRIPTED)

        assert sanitize(once) == once


class TestWhatThisPackageWrites:
    """The check lets through everything the package itself stores."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_the_control_panel_still_stores_an_icon(self):
        """Stored as the envelope around an already sanitized document."""
        set_providers([
            ProviderConfig(
                provider_id="broken", driver_id="github", title="Broken", icon=ICON
            )
        ])

        assert "<svg" in get_provider("broken").icon

    def test_a_provider_without_an_icon_round_trips(self):
        """The reported value is not something this package's own export
        writes: an empty icon is stored as empty bytes, which export as an
        empty value."""
        set_providers([
            ProviderConfig(provider_id="broken", driver_id="github", title="Broken")
        ])
        document = provider_fragment("broken")
        set_providers([])

        import_document(document)

        assert REPORTED not in document
        assert get_provider("broken").icon == ""


class TestWhichRecordsAreIcons:
    """The record name is the whole of how an icon is recognised."""

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("pas.plugins.identity.providers.github.icon", "github"),
            ("pas.plugins.identity.providers.github.title", None),
            ("pas.plugins.identity.providers.github.config.icon", None),
            ("plone.app.theming.icon", None),
        ],
    )
    def test_it_recognises(self, name: str, expected: str | None):
        """A driver setting named ``icon`` sits under ``config.`` and is not
        the provider's icon."""
        assert icon_provider(name) == expected
