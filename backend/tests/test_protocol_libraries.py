"""Which modules may speak the protocol, and with what.

Two rules, and neither is about style.

**Nothing imports ``authlib.jose``.** It is deprecated in favour of
``joserfc`` and Authlib promises to keep it only until 2.0.0, so an import
that creeps back in is a module that stops working at a release nobody in
this repository controls. The deprecation warning it emits is the only other
signal, and a warning in a suite with hundreds of them is not a signal.

**Only the modules that own a protocol boundary import a protocol library.**
``docs/docs/reference/security-guarantees.md`` states this as a guarantee --
"protocol messages are never constructed by hand" -- and it named a
grep-level CI rule that did not exist. This is that rule.

The allowlist is small on purpose. A JWT parsed somewhere else is a JWT
somebody parsed by hand, and an authorization URL built somewhere else is a
URL that skipped PKCE.
"""

from pathlib import Path

import pytest


#: The package's source tree.
SOURCE = Path(__file__).resolve().parent.parent / "src" / "pas" / "plugins" / "identity"

#: Modules allowed to import a JOSE or OAuth library, and what each owns.
ALLOWED = {
    "core/flows/__init__.py": "the authorization-code flow, and the id_token it returns",
    "core/flows/magiclink.py": "the magic link's own signature",
    "core/logout.py": "a back-channel logout token from a provider",
    "server/grants/tokens.py": "the tokens this site mints as an issuer",
    "server/utils/keys.py": "the signing key ring behind them",
}

#: What counts as a protocol library.
LIBRARIES = ("authlib", "joserfc")


def modules() -> list[Path]:
    """Return every Python module in the package.

    :returns: Paths, sorted, so a failure names the same file every run.
    """
    return sorted(SOURCE.rglob("*.py"))


def imports(path: Path) -> list[str]:
    """Return the lines of a module that import something.

    Text rather than the AST: an import inside a function is still an import,
    and this package puts several of them there deliberately.

    :param path: The module.
    :returns: The stripped import lines.
    """
    return [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip().startswith(("import ", "from "))
    ]


class TestNothingImportsTheDeprecatedJoseModule:
    """``authlib.jose`` goes away at Authlib 2.0.0."""

    def test_no_module_imports_it(self):
        offenders = [
            str(path.relative_to(SOURCE))
            for path in modules()
            if any("authlib.jose" in line for line in imports(path))
        ]

        assert offenders == [], f"authlib.jose is imported by: {offenders}"

    def test_the_replacement_is_a_declared_dependency(self):
        """It arrives through Authlib today, which is exactly why it is
        declared: what this package imports directly must not depend on
        another package's dependency graph."""
        pyproject = (SOURCE.parents[3] / "pyproject.toml").read_text()

        assert '"joserfc' in pyproject


class TestOnlyTheProtocolModulesSpeakTheProtocol:
    """The rule the security guarantees name."""

    @pytest.mark.parametrize("library", LIBRARIES)
    def test_no_other_module_imports_a_protocol_library(self, library: str):
        offenders = sorted(
            str(path.relative_to(SOURCE))
            for path in modules()
            if str(path.relative_to(SOURCE)) not in ALLOWED
            and any(library in line for line in imports(path))
        )

        assert offenders == [], (
            f"{library} is imported outside the protocol modules: {offenders}. "
            "A JWT parsed elsewhere is a JWT parsed by hand."
        )

    def test_every_allowed_module_exists(self):
        """An allowlist naming a file that has moved allows nothing, and
        would let the rule above pass while the module it was written for
        speaks the protocol somewhere else."""
        missing = [name for name in ALLOWED if not (SOURCE / name).is_file()]

        assert missing == [], f"The allowlist names modules that are gone: {missing}"

    def test_every_allowed_module_actually_uses_one(self):
        """The other direction: an entry nobody needs any more is an
        exemption that outlives its reason."""
        unused = sorted(
            name
            for name in ALLOWED
            if not any(
                library in line
                for line in imports(SOURCE / name)
                for library in LIBRARIES
            )
        )

        assert unused == [], f"The allowlist exempts modules that need it: {unused}"
