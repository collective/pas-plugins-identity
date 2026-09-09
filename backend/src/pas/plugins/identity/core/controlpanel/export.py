"""One provider as a registry fragment a profile can ship.

``runExportStep("plone.app.registry")`` dumps the whole registry, and feeding
that document back into a site fails on records belonging to other packages --
``ConstraintNotSatisfied('/news/aggregator')`` is the one that turns up first.
So shipping a provider has meant extracting its records by hand, and two things
make that harder than it sounds: the grouped ``<records interface= prefix=>``
node cannot carry a ``config.*`` record at all, because those are not fields on
:class:`~pas.plugins.identity.core.controlpanel.interfaces.IProviderRecords`;
and which config records exist differs per driver, so there is no fixed list to
copy.

**Nothing here serializes a value.** Every ``<value>`` in the output was
written by ``plone.app.registry``'s own exporter, one record at a time through
:meth:`RegistryExporter.exportRecord`, and the interface-bound ones are then
moved into the grouped node element and all. A ``Tuple`` of scopes, a ``Dict``
of claim mappings and the ``Bytes`` an icon is stored as are shapes worth
nobody re-deriving; the round-trip test in ``tests/core/controlpanel`` is what
says the result imports.
"""

from lxml import etree
from pas.plugins.identity.core.controlpanel import CONFIG_SEGMENT
from pas.plugins.identity.core.controlpanel import provider_record_names
from pas.plugins.identity.core.controlpanel import PROVIDERS_PREFIX
from plone.app.registry.exportimport.handler import RegistryExporter
from plone.registry.interfaces import IRegistry
from plone.supermodel.utils import prettyXML
from zope.component import getUtility

import logging


#: Dotted name of the schema a provider's fixed fields are bound to. Written
#: out rather than derived from the class, because it is what goes into the
#: document and a rename has to be visible as a change to this string.
RECORDS_INTERFACE = "pas.plugins.identity.core.controlpanel.interfaces.IProviderRecords"


class _Environ:
    """The one method ``RegistryExporter`` asks its environment for."""

    def getLogger(self, name: str) -> logging.Logger:
        """Return a logger.

        :param name: Logger name.
        :returns: The logger.
        """
        return logging.getLogger(name)


def fragment_filename(provider_id: str) -> str:
    """Return the filename this fragment belongs under in a profile.

    :param provider_id: The provider.
    :returns: A filename for ``profiles/default/registry/``.
    """
    return f"{PROVIDERS_PREFIX}{provider_id}.xml"


def provider_fragment(provider_id: str) -> str:
    """Return one provider's records as an importable registry document.

    The fixed fields go into a single ``<records interface= prefix=>`` node,
    which is the form a hand-written profile uses and is *not* what the
    registry exporter emits -- it writes one ``<record>`` per field, each
    restating the interface, the field type, the title and the description.
    The config records stay as their own ``<record>`` elements, because they
    have to: with no interface to inherit a type from, a record that does not
    carry its own cannot be imported into a site that has never seen it.

    :param provider_id: The provider to describe.
    :returns: The XML document.
    """
    registry = getUtility(IRegistry)
    exporter = RegistryExporter(registry, _Environ())
    prefix = f"{PROVIDERS_PREFIX}{provider_id}."

    root = etree.Element("registry")
    grouped = etree.SubElement(root, "records")
    grouped.attrib["interface"] = RECORDS_INTERFACE
    grouped.attrib["prefix"] = prefix.rstrip(".")

    for name in provider_record_names(provider_id):
        node = exporter.exportRecord(registry.records[name])
        leaf = name[len(prefix) :]
        if leaf.startswith(CONFIG_SEGMENT) or node.get("interface") is None:
            # Its own type or nothing: a driver setting belongs to no
            # interface, and neither does a record left behind by a driver
            # that has since been removed.
            root.append(node)
            continue
        value = node.find("value")
        if value is None:
            # A record with no value element is one plone.app.registry
            # declined to export -- a field type with no export handler. Left
            # out rather than emitted empty, since an empty value imports as
            # None and that is worse than a missing record.
            continue
        moved = etree.SubElement(grouped, "value")
        moved.attrib["key"] = leaf
        moved.text = value.text
        for child in value:
            moved.append(child)

    return prettyXML(root)
