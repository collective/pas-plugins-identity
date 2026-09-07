"""Shared values for the install/uninstall tests."""

#: Profiles the ``default`` profile is expected to pull in.
DEPENDENCY_PROFILES = ("plone.restapi:default",)


def declared_catalog() -> tuple[dict[str, str], set[str]]:
    """Read ``identity-catalog.xml`` and return what it declares.

    The profile is the source of truth for the Profile catalog's shape, so a
    test asserting the live catalog has to read the same file GenericSetup
    reads. Asserting against a Python copy of the list would only prove the
    two copies agree, which is the thing that stops being true.

    :returns: Index name to meta_type, and the set of column names.
    """
    from pathlib import Path
    from xml.etree import ElementTree

    import pas.plugins.identity

    path = (
        Path(pas.plugins.identity.__file__).parent
        / "profiles"
        / "default"
        / "identity-catalog.xml"
    )
    # S314: the input is a file shipped inside the package under test,
    # read from its own installed location. defusedxml would do, but it is
    # a transitive Plone dependency this package does not declare, and a
    # test must not be the thing that starts relying on one.
    root = ElementTree.fromstring(path.read_text())  # noqa: S314
    indexes = {
        node.attrib["name"]: node.attrib["meta_type"] for node in root.findall("index")
    }
    columns = {node.attrib["value"] for node in root.findall("column")}
    return indexes, columns
