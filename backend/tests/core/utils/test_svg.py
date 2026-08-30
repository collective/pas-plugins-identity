"""Unit tests for the provider-icon sanitizer.

No portal: :mod:`pas.plugins.identity.core.utils.svg` is a pure function over a
string, and the whole point of it is that it can be reasoned about without a
site in the loop.
"""

from pas.plugins.identity.core.utils.svg import InvalidSVG
from pas.plugins.identity.core.utils.svg import MAX_LENGTH
from pas.plugins.identity.core.utils.svg import sanitize

import pytest


#: A plausible provider icon.
ICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
    "<title>GitHub</title>"
    '<path d="M8 0a8 8 0 0 0-2.5 15.6" fill="#24292f"/>'
    "</svg>"
)


#: The opening tag every attack below is wrapped in, bar the one that
#: carries its payload on the root element itself.
ROOT = '<svg xmlns="http://www.w3.org/2000/svg">'


class TestKeepsWhatAnIconNeeds:
    def test_the_root_survives(self):
        """An ordinary icon comes back as an SVG document."""
        assert sanitize(ICON).startswith("<svg")

    def test_geometry_survives(self):
        """The path is the icon; losing it would leave an empty box."""
        result = sanitize(ICON)

        assert 'd="M8 0a8 8 0 0 0-2.5 15.6"' in result
        assert 'viewBox="0 0 16 16"' in result

    @pytest.mark.parametrize(
        "fragment",
        [
            # A fill is what makes a monochrome icon the brand's colour.
            'fill="#24292f"',
            # The title is what a screen reader announces.
            "<title>GitHub</title>",
            # Without the namespace a browser renders nothing at all.
            'xmlns="http://www.w3.org/2000/svg"',
        ],
        ids=["presentation", "the-title-with-its-text", "the-namespace"],
    )
    def test_it_survives(self, fragment: str):
        assert fragment in sanitize(ICON)

    def test_empty_is_not_an_error(self):
        """Clearing an icon is an ordinary edit."""
        assert sanitize("") == ""
        assert sanitize("   ") == ""


#: ``(source, what must be gone, what must survive)``. The root element
#: is written out per row rather than wrapped around a fragment, because
#: one of these attacks is *on* the root.
ATTACKS = [
    (
        # Unwrapping it would keep the payload, which is the whole element.
        f'{ROOT}<script>fetch("//evil.example")</script><path d="M0 0"/></svg>',
        ("script", "evil.example"),
        ('d="M0 0"',),
    ),
    (
        # Excluded by the allowlist rather than by matching ``on*``.
        '<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>',
        ("onload",),
        (),
    ),
    (
        # foreignObject is the documented way to put a whole HTML
        # document inside an SVG.
        f'{ROOT}<foreignObject><iframe src="//evil.example"/></foreignObject></svg>',
        ("foreignObject", "iframe"),
        (),
    ),
    (
        # CSS is a second language, and it can fetch.
        f"{ROOT}<style>@import url(//evil.example)</style></svg>",
        ("evil.example",),
        (),
    ),
    (
        # Same reason, in the place people forget to look.
        f'{ROOT}<path d="M0 0" style="background:url(//evil.example)"/></svg>',
        ("evil.example",),
        (),
    ),
    (
        # A ``use`` pulls in a document from somewhere else.
        f'{ROOT}<use href="https://evil.example/x.svg#i"/></svg>',
        ("use", "evil.example"),
        (),
    ),
    (
        # The element is fine; what it points at is not.
        f'{ROOT}<path d="M0 0" fill="url(#x)"/></svg>',
        ("url(#x)",),
        ('d="M0 0"',),
    ),
    (
        # A shape's text means nothing in SVG, so keeping it is only a
        # way past a filter that looked at tags alone.
        f'{ROOT}<path d="M0 0">alert(1)</path></svg>',
        ("alert(1)",),
        (),
    ),
]


class TestDropsWhatRuns:
    """The sanitizer's threat model, as a table.

    Each row is one way to get script, network access or markup past a filter
    that looked at element names alone. They were eight near-identical methods
    before; the shape never varied, only the attack did, so the attack is what
    the table carries.
    """

    @pytest.mark.parametrize(
        "source,must_go,must_stay",
        ATTACKS,
        ids=[
            "a-script-element-goes-with-its-text",
            "an-event-handler-is-not-an-allowed-attribute",
            "foreign-object-is-arbitrary-html",
            "a-style-element-goes",
            "a-style-attribute-goes",
            "an-external-reference-goes",
            "a-url-valued-attribute-goes-even-on-an-allowed-element",
            "text-content-on-a-shape-is-dropped",
        ],
    )
    def test_it_is_removed(
        self, source: str, must_go: tuple[str, ...], must_stay: tuple[str, ...]
    ):
        result = sanitize(source)

        for fragment in must_go:
            assert fragment not in result
        for fragment in must_stay:
            assert fragment in result


class TestRefuses:
    def test_something_that_is_not_xml(self):
        """A truncated paste is the common case."""
        with pytest.raises(InvalidSVG):
            sanitize("<svg><path")

    def test_something_that_is_not_an_svg(self):
        """An HTML document parses as XML often enough to matter."""
        with pytest.raises(InvalidSVG) as exc:
            sanitize("<html><body>hi</body></html>")

        assert "not 'svg'" in str(exc.value)

    def test_something_too_large(self):
        """An icon is a few kilobytes; a full-detail export is not an icon,
        and every login page would carry it."""
        with pytest.raises(InvalidSVG):
            sanitize('<svg xmlns="http://www.w3.org/2000/svg">' + "x" * MAX_LENGTH)
