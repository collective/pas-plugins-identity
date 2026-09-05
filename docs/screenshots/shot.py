"""Write screenshots where and how the documentation expects them.

Two concerns live here.

The first is **where the file goes**: ``docs/_static/screens/<name>.png``, under
the same name the Markdown references, so a placeholder is simply overwritten
and no page needs editing.

The second is **stability**. A capture that changes on every run produces a diff
in the repository when nothing has actually changed, and reviewing the pull
request stops meaning anything. So :meth:`Shot.capture` turns off animations,
waits for the network to settle, and accepts a list of elements to mask.
"""

from .discovery import referenced
from .discovery import SCREENS
from collections.abc import Mapping
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator
from playwright.sync_api import Page

# Playwright has its own timeout exception, which does **not** derive from
# Python's built-in TimeoutError. Catching the built-in would catch nothing.
from playwright.sync_api import TimeoutError as Timeout


#: Browser window width, matching the placeholders.
WIDTH = 1440

#: Browser window height.
HEIGHT = 810

#: Applied before every capture. Turns off transitions, animations and the
#: blinking caret — three sources of difference between runs that represent no
#: change at all in the interface.
STABILIZE = """
*, *::before, *::after {
    animation-duration: 0s !important;
    animation-delay: 0s !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0s !important;
    transition-delay: 0s !important;
    caret-color: transparent !important;
    scroll-behavior: auto !important;
}
"""

#: Milliseconds to wait for the network to go quiet.
NETWORK_WAIT = 15_000

#: Colour used to cover masked elements. Playwright's default is a strong
#: magenta meant for debugging; on a documentation page it draws more attention
#: than the subject. This grey disappears into the panels.
MASK_COLOUR = "#eceef0"


class UnknownScreenshot(RuntimeError):
    """A capture was asked for under a name the Markdown does not reference.

    Almost always a typo, on one side or the other. Capturing anyway would leave
    an orphan image in the repository.
    """


@dataclass
class Shot:
    """Writes captures for one run of a script.

    :param page: The Playwright page to photograph.
    :param destination: Directory to write into. Defaults to the documentation's
        screens directory.
    :param written: Names written during this run, in order.
    """

    page: Page
    destination: Path = SCREENS
    written: list[str] = field(default_factory=list)

    def path_for(self, name: str) -> Path:
        """Return the file path for a screenshot.

        :param name: Filename, without extension.
        :returns: The full path of the PNG.
        """
        return self.destination / f"{name}.png"

    def _check(self, name: str) -> None:
        """Refuse a name the Markdown does not reference.

        :param name: Filename, without extension.
        :raises UnknownScreenshot: When no page references that name.
        """
        known = referenced()
        if name not in known:
            near = [c for c in known if c.startswith(name[:20])]
            hint = f" Similar names: {', '.join(sorted(near)[:5])}." if near else ""
            raise UnknownScreenshot(
                f"The screenshot {name!r} is referenced by no page in docs/. "
                f"Capturing it would leave an orphan image in the "
                f"repository.{hint}"
            )

    def prepare(self, *, keep_focus: bool = False) -> None:
        """Put the page into a reproducible state before photographing it.

        Three measures, each against an observed source of variation: the
        :data:`STABILIZE` stylesheet against animations and transitions; blurring
        the active element and moving the pointer away against focus and hover
        highlights; and waiting for the network to settle.

        The network wait is best effort. A page that never goes quiet still
        yields a useful capture; it is simply not waited on for ever.

        :param keep_focus: When ``True``, leave the active element focused. See
            the same parameter on :meth:`capture`.
        """
        self.page.add_style_tag(content=STABILIZE)
        self.page.mouse.move(0, 0)
        if not keep_focus:
            self.page.evaluate("() => document.activeElement?.blur?.()")
        with suppress(Timeout):
            self.page.wait_for_load_state("networkidle", timeout=NETWORK_WAIT)
        with suppress(Timeout, PlaywrightError):
            self.page.evaluate("() => document.fonts.ready")

    def capture(
        self,
        name: str,
        *,
        element: Locator | None = None,
        clip: Mapping[str, float] | None = None,
        full_page: bool = False,
        mask: Sequence[Locator] | None = None,
        keep_focus: bool = False,
    ) -> Path:
        """Photograph the page and write the image where the documentation wants it.

        Three framings are possible, in order of preference:

        ``element``
            Crop to one element. The most expressive when a stable selector
            exists for the region to show.
        ``clip``
            Crop to a region of the window, in pixels. For when no reliable
            selector exists.
        the whole window
            The default.

        :param name: Filename, without extension. Must be a name the Markdown
            references.
        :param element: Element to crop the capture to.
        :param clip: Region of the window to crop to, with keys ``x``, ``y``,
            ``width`` and ``height``. Ignored when ``element`` is given.
        :param full_page: When ``True``, photograph the page scrolled to the end
            rather than only the visible part. Incompatible with either crop.
        :param mask: Elements to cover with a solid rectangle — dates, the name
            of whoever is signed in, anything that changes between runs without
            representing a change in the interface.
        :param keep_focus: When ``True``, do not blur the active element before
            photographing. Needed for any screen showing an open dropdown, which
            closes on losing focus — the capture would otherwise show the control
            closed, with no error, and show something other than what the alt
            text promises.
        :returns: The path written.
        :raises UnknownScreenshot: When the name is not referenced in the docs.
        :raises ValueError: When incompatible framings are asked for.
        """
        if full_page and (element is not None or clip is not None):
            raise ValueError(
                "full_page does not combine with element or clip: one asks for "
                "the whole page, the others ask for a piece of it."
            )

        self._check(name)
        self.prepare(keep_focus=keep_focus)

        target = self.path_for(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        masks = list(mask or [])

        if element is not None:
            element.screenshot(path=target, mask=masks, mask_color=MASK_COLOUR)
        elif clip is not None:
            self.page.screenshot(
                path=target, clip=dict(clip), mask=masks, mask_color=MASK_COLOUR
            )
        else:
            self.page.screenshot(
                path=target,
                full_page=full_page,
                mask=masks,
                mask_color=MASK_COLOUR,
            )

        self.written.append(name)
        return target
