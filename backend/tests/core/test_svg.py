"""Unit tests for the provider-icon sanitizer.

No portal: :mod:`pas.plugins.identity.core.svg` is a pure function over a
string, and the whole point of it is that it can be reasoned about without a
site in the loop.
"""

from pas.plugins.identity.core.svg import InvalidSVG
from pas.plugins.identity.core.svg import MAX_LENGTH
from pas.plugins.identity.core.svg import sanitize

import pytest


#: A plausible provider icon.
ICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
    "<title>GitHub</title>"
    '<path d="M8 0a8 8 0 0 0-2.5 15.6" fill="#24292f"/>'
    "</svg>"
)


class TestKeepsWhatAnIconNeeds:
    def test_the_root_survives(self):
        """An ordinary icon comes back as an SVG document."""
        assert sanitize(ICON).startswith("<svg")

    def test_geometry_survives(self):
        """The path is the icon; losing it would leave an empty box."""
        result = sanitize(ICON)

        assert 'd="M8 0a8 8 0 0 0-2.5 15.6"' in result
        assert 'viewBox="0 0 16 16"' in result

    def test_presentation_survives(self):
        """A fill is what makes a monochrome icon the brand's colour."""
        assert 'fill="#24292f"' in sanitize(ICON)

    def test_the_title_survives_with_its_text(self):
        """It is what a screen reader announces."""
        assert "<title>GitHub</title>" in sanitize(ICON)

    def test_the_namespace_is_written_back(self):
        """Without it a browser renders nothing at all."""
        assert 'xmlns="http://www.w3.org/2000/svg"' in sanitize(ICON)

    def test_empty_is_not_an_error(self):
        """Clearing an icon is an ordinary edit."""
        assert sanitize("") == ""
        assert sanitize("   ") == ""


class TestDropsWhatRuns:
    def test_a_script_element_goes_with_its_text(self):
        """Unwrapping it would keep the payload, which is the whole element."""
        source = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<script>fetch("//evil.example")</script>'
            '<path d="M0 0"/>'
            "</svg>"
        )

        result = sanitize(source)

        assert "script" not in result
        assert "evil.example" not in result
        assert 'd="M0 0"' in result

    def test_an_event_handler_is_not_an_allowed_attribute(self):
        """Excluded by the allowlist rather than by matching ``on*``."""
        source = '<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>'

        assert "onload" not in sanitize(source)

    def test_foreign_object_is_arbitrary_html(self):
        """It is the documented way to put a whole HTML document in an SVG."""
        source = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<foreignObject><iframe src="//evil.example"/></foreignObject>'
            "</svg>"
        )

        result = sanitize(source)

        assert "foreignObject" not in result
        assert "iframe" not in result

    def test_a_style_element_goes(self):
        """CSS is a second language, and it can fetch."""
        source = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            "<style>@import url(//evil.example)</style>"
            "</svg>"
        )

        assert "evil.example" not in sanitize(source)

    def test_a_style_attribute_goes(self):
        """Same reason, in the place people forget to look."""
        source = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path d="M0 0" style="background:url(//evil.example)"/>'
            "</svg>"
        )

        assert "evil.example" not in sanitize(source)

    def test_an_external_reference_goes(self):
        """A ``use`` pulls in a document from somewhere else."""
        source = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<use href="https://evil.example/x.svg#i"/>'
            "</svg>"
        )

        result = sanitize(source)

        assert "use" not in result
        assert "evil.example" not in result

    def test_a_url_valued_attribute_goes_even_on_an_allowed_element(self):
        """The element is fine; what it points at is not."""
        source = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path d="M0 0" fill="url(#x)"/>'
            "</svg>"
        )

        result = sanitize(source)

        assert 'd="M0 0"' in result
        assert "url(#x)" not in result

    def test_text_content_on_a_shape_is_dropped(self):
        """A shape's text means nothing in SVG, so keeping it is only a way
        past a filter that looked at tags alone."""
        source = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path d="M0 0">alert(1)</path>'
            "</svg>"
        )

        assert "alert(1)" not in sanitize(source)


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
