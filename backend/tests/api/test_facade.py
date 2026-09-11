"""What the façade puts on the table.

A re-export is easy to get wrong in a way nothing notices: a name in
``__all__`` that no import provides, or an import that quietly resolves to a
different object from the one the layer defines. Both would be found by
whoever tried to use it, which is the wrong person to find it.
"""

from pas.plugins.identity import api

import pytest


class TestEveryNameResolves:
    def test_all_is_complete(self):
        """Nothing in ``__all__`` is missing from the module.

        ``from pas.plugins.identity.api import *`` would raise on a name that
        is listed and not imported, and nothing in the suite does that -- so
        without this test the typo ships.
        """
        missing = [name for name in api.__all__ if not hasattr(api, name)]

        assert missing == []

    def test_all_has_no_duplicates(self):
        """A name listed twice is a merge artefact, and harmless enough to
        survive review."""
        assert len(api.__all__) == len(set(api.__all__))

    def test_the_namespaces_are_modules(self):
        """``api.profile`` is reachable after importing ``api`` alone.

        A submodule is not an attribute of its package until something
        imports it, so this is a real property of ``__init__`` rather than a
        tautology.
        """
        for name in ("profile", "portrait", "provider", "claims", "clients"):
            assert hasattr(api, name), name


class TestTheVocabularyIsTheRealThing:
    """A re-export must *be* the layer's object, not a lookalike.

    ``@adapter(api.IUserProfile)`` and ``@adapter(core...IUserProfile)`` have
    to register against one interface, or a downstream adapter is registered
    for something nothing provides -- and the failure is silence, not an
    error.
    """

    def test_interfaces_are_identical(self):
        """Identity, not equality: interfaces compare by identity."""
        from pas.plugins.identity.core import interfaces

        assert api.IProfileEnricher is interfaces.IProfileEnricher
        assert api.IUserProfile is interfaces.IUserProfile
        assert api.IUserGroup is interfaces.IUserGroup
        assert api.IUserContent is interfaces.IUserContent
        assert api.IIdentityProfileCatalog is interfaces.IIdentityProfileCatalog

    def test_events_are_identical(self):
        """A subscriber registered through the façade must see the event the
        package actually fires."""
        from pas.plugins.identity.core import events

        assert api.IdentityLinked is events.IdentityLinked
        assert api.IdentityUnlinked is events.IdentityUnlinked
        assert api.ExternalIdentityAuthenticated is events.ExternalIdentityAuthenticated
        assert api.UserClaimsRefreshed is events.UserClaimsRefreshed

    def test_content_classes_are_identical(self):
        """``isinstance(obj, api.UserProfile)`` must answer for the object the
        factory actually creates."""
        from pas.plugins.identity.core.contents.group import UserGroup
        from pas.plugins.identity.core.contents.profile import UserProfile

        assert api.UserProfile is UserProfile
        assert api.UserGroup is UserGroup


class TestTheFacadeIsALeaf:
    """The property the import-linter contract enforces, asserted here too.

    The contract is the gate; this is the explanation. A test that fails names
    the rule, where a broken contract names only an import chain.
    """

    def test_no_layer_imports_the_facade(self):
        """Nothing under the package may import ``api``.

        ``api`` re-exports the optional ``[server]`` layer, so a core module
        importing it would drag that layer into a no-extras install -- which
        is the configuration two other contracts exist to protect.
        """
        import ast
        import pas.plugins.identity
        import pathlib

        root = pathlib.Path(pas.plugins.identity.__file__).parent
        offenders = []
        for path in sorted(root.rglob("*.py")):
            if path.is_relative_to(root / "api"):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                # Parsed rather than grepped: docstrings cross-reference
                # ``pas.plugins.identity.api`` on purpose, and a text scan
                # would read a citation as a dependency.
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    base = node.module or ""
                    names = [base] + [f"{base}.{a.name}" for a in node.names]
                else:
                    continue
                if any(
                    name == "pas.plugins.identity.api"
                    or name.startswith("pas.plugins.identity.api.")
                    for name in names
                ):
                    offenders.append(f"{path.relative_to(root)}:{node.lineno}")

        assert offenders == []


class TestImportingItNeedsNothing:
    def test_it_imports_outside_a_zope_application(self):
        """The façade imports with no site, no request and no test layer.

        This is not automatic. ``pas.plugins.identity.core`` runs two things
        at import -- it patches PlonePAS's group tool and closes the
        vocabularies to anonymous callers -- because it is the module the
        layer's ZCML loads. Anything the façade did at import time would run
        in every consumer that so much as imported it, including a console
        script and a migration.

        ``make check-clean-install`` asserts the same property against a
        bare install; this asserts it every time the suite runs, where a
        regression is attributable to the commit that caused it.
        """
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-c", "import pas.plugins.identity.api"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stderr[-2000:]

    def test_the_server_namespace_imports_without_the_layer_installed(self):
        """``api.claims`` is importable on a site that never switched the
        authorization server on.

        The ``[server]`` profile is not applied in this module, so the layer
        is present as code and absent as configuration -- which is the state
        of every site that installed the add-on and nothing else. Importing
        the namespace must still work; only calling into it needs the layer.
        """
        assert api.claims.get_scopes is not None
        assert api.clients.get_all is not None


@pytest.mark.parametrize(
    "namespace,names",
    [
        ("profile", ("get", "get_current", "get_or_create")),
        ("portrait", ("has_picture", "get_url", "store", "sync_portrait")),
        ("provider", ("get", "get_all", "plugin")),
        ("claims", ("get", "get_scopes", "get_released")),
        ("clients", ("get", "get_all", "add", "remove")),
    ],
)
def test_each_namespace_offers_what_it_documents(namespace, names):
    """The shape the docs promise, asserted per namespace.

    Renaming one of these is a breaking change for a downstream package, so it
    should take a deliberate edit here rather than passing unnoticed.
    """
    module = getattr(api, namespace)

    assert [name for name in names if not hasattr(module, name)] == []
