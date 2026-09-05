"""Report which screenshots still have no script, and check the cycle closes.

Two checks, and only one of them runs today.

:func:`test_report` never opens a browser. It prints what is still missing, so
``make screenshots-coverage`` answers "what is left" without starting anything.

:func:`test_every_screenshot_has_a_script` is the one that closes the cycle: a
screenshot referenced in the Markdown with nothing to capture it is a
placeholder that will ship. It is skipped while coverage is being built up, and
the skip comes off once the scripts cover every referenced screen.
"""

from .discovery import pending
from .discovery import referenced

import pytest


def test_report() -> None:
    """Print which screenshots are still placeholders. Never fails."""
    every = referenced()
    missing = pending()
    captured = len(every) - len(missing)

    print(f"\n{captured} of {len(every)} screenshots captured.")
    if missing:
        print("\nStill placeholders:")
        for name, description in missing.items():
            print(f"  {name}.png — {description}")
    else:
        print("Nothing pending.")


@pytest.mark.skip(
    reason="Coverage is still being built up. Remove this skip once the scripts "
    "cover every screenshot the Markdown references."
)
def test_every_screenshot_has_a_script() -> None:
    """Every referenced screenshot must have been captured for real."""
    missing = pending()
    assert not missing, (
        f"{len(missing)} screenshots are referenced in docs/ and still "
        f"placeholders: {', '.join(sorted(missing))}"
    )


def test_no_orphan_images() -> None:
    """Every file in the screens directory is referenced by some page.

    This one runs. An orphan is cheap to create — rename a screenshot in the
    Markdown and the old file stays behind — and it ships in the built site.
    """
    from .discovery import SCREENS

    if not SCREENS.exists():
        pytest.skip("No screenshots have been generated yet.")

    known = set(referenced())
    orphans = sorted(
        path.stem for path in SCREENS.glob("*.png") if path.stem not in known
    )
    assert not orphans, (
        f"{len(orphans)} image(s) in {SCREENS.name}/ are referenced by no page: "
        f"{', '.join(orphans)}. Delete them, or reference them."
    )
