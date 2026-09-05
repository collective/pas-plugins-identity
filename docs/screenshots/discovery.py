"""Discover which screenshots the documentation references.

The list of screenshots is not maintained here. It is deduced from the Markdown
itself, by the same function that generates the placeholders — keeping a second
list would mean keeping it up to date, and it would not stay so.

Two rules follow from that, and the code enforces both:

-   **Only a screenshot the Markdown references is ever captured.** A misspelled
    name fails immediately, with a list of near misses, so no orphan image
    reaches the repository.
-   **Every referenced screenshot needs a script.** That is what
    :mod:`test_coverage` checks.
"""

from functools import cache
from pathlib import Path
from types import ModuleType

import importlib.util


#: Root of the docs project.
ROOT = Path(__file__).resolve().parent.parent

#: The script that already knows how to scan the Markdown.
GENERATOR = ROOT / "scripts" / "generate_placeholders.py"

#: Where captures are written. The same path the Markdown references.
SCREENS = ROOT / "docs" / "_static" / "screens"


@cache
def _generator() -> ModuleType:
    """Load ``scripts/generate_placeholders.py`` as a module.

    The script is not part of an installable package, so it is loaded by path
    rather than by altering :data:`sys.path`.

    :returns: The loaded module.
    :raises FileNotFoundError: If the script is missing.
    """
    if not GENERATOR.exists():
        raise FileNotFoundError(f"Generator script not found at {GENERATOR}")
    spec = importlib.util.spec_from_file_location("generate_placeholders", GENERATOR)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@cache
def referenced() -> dict[str, str]:
    """List the screenshots the documentation references.

    :returns: A mapping of ``{filename: description}``, sorted by name. The
        description is the text of the ``:alt:`` option on the ``image``
        directive.
    """
    return _generator().discover()


def is_placeholder(name: str) -> bool:
    """Report whether a screenshot is still a placeholder.

    :param name: Filename, without extension or directory.
    :returns: ``True`` when the file is missing or is a generated placeholder.
    """
    return _generator().is_placeholder(SCREENS / f"{name}.png")


def pending() -> dict[str, str]:
    """List the screenshots that have not been captured for real yet.

    :returns: A mapping of ``{filename: description}`` for every screenshot
        whose file is still a placeholder, or does not exist.
    """
    return {
        name: description
        for name, description in referenced().items()
        if is_placeholder(name)
    }
