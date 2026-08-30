"""Making an operator-supplied SVG safe to render inline.

A provider icon is an SVG document typed or uploaded in the control panel and
then rendered *inside* the login page, which is the one thing that separates
it from an ordinary image: an ``<img src>`` runs nothing, an inlined
``<svg>`` runs whatever it carries. SVG is XML with a scripting model -- it
has ``<script>``, it has ``onload``, it has ``<foreignObject>`` for arbitrary
HTML, and it can pull in remote documents through ``<use href>`` and
``xlink:href``.

The permission needed to configure a provider is ``Manage portal``, so this
is not a privilege boundary that has to hold against an attacker who already
owns the site. It is the boundary that stops a *copied-and-pasted* icon from
carrying something its new owner never read. Icons come from a brand page,
and a brand page's SVG routinely carries a comment, a title, a stray
``<style>`` and occasionally a tracking script.

So the policy is an allowlist and nothing else survives it:

* the root element must be ``svg``;
* only the elements in :data:`ALLOWED_ELEMENTS` are kept, and an element that
  is not on it is dropped **with its whole subtree** -- not unwrapped, since
  unwrapping a ``<script>`` would keep its text;
* only the attributes in :data:`ALLOWED_ATTRIBUTES` are kept, which excludes
  every ``on*`` handler by construction rather than by pattern;
* no attribute value may reference a URL, so no external fetch and no
  ``javascript:``.

What comes back is serialized from the parsed tree rather than sliced out of
the input, so nothing survives that this module did not deliberately write.

Parsing is ``defusedxml``: an SVG is XML, and the entity-expansion attacks
against an XML parser are older than the scripting ones.
"""

from binascii import Error as BinasciiError
from defusedxml import ElementTree as DefusedET
from xml.etree import ElementTree as ET

import re


#: XML namespace every SVG element lives in.
SVG_NS = "http://www.w3.org/2000/svg"

#: Elements kept. Shapes, grouping, paths and the two metadata elements a
#: screen reader reads. Deliberately no ``script``, no ``style``, no
#: ``foreignObject``, no ``image``, no ``a``, and no ``use`` -- the last three
#: exist to reference something else, which is the thing this must not do.
ALLOWED_ELEMENTS = frozenset({
    "svg",
    "g",
    "defs",
    "title",
    "desc",
    "path",
    "rect",
    "circle",
    "ellipse",
    "line",
    "polyline",
    "polygon",
    "text",
    "tspan",
    "linearGradient",
    "radialGradient",
    "stop",
    "clipPath",
    "mask",
    "symbol",
})

#: Attributes kept. Geometry, presentation and the accessibility pair.
#:
#: ``style`` is absent on purpose: it is a second language inside the
#: attribute, and it carries ``url(...)`` -- so allowing it would reopen the
#: external-reference hole this closes everywhere else.
ALLOWED_ATTRIBUTES = frozenset({
    "id",
    "class",
    "viewBox",
    "width",
    "height",
    "x",
    "y",
    "x1",
    "y1",
    "x2",
    "y2",
    "cx",
    "cy",
    "r",
    "rx",
    "ry",
    "d",
    "points",
    "transform",
    "fill",
    "fill-rule",
    "fill-opacity",
    "stroke",
    "stroke-width",
    "stroke-linecap",
    "stroke-linejoin",
    "stroke-dasharray",
    "stroke-opacity",
    "opacity",
    "offset",
    "stop-color",
    "stop-opacity",
    "gradientUnits",
    "gradientTransform",
    "clip-path",
    "clip-rule",
    "mask",
    "text-anchor",
    "font-family",
    "font-size",
    "font-weight",
    "role",
    "aria-label",
    "aria-hidden",
    "preserveAspectRatio",
    "xmlns",
})

#: Attribute values that reference something outside the document. Matched
#: rather than parsed: an attribute has no business carrying a URL at all
#: here, so the test is "does this look like one" rather than "where does
#: this one point".
URL_REFERENCE = re.compile(r"(?i)(url\s*\(|javascript:|data:|https?:|//)")

#: Ceiling on the stored source, in characters. An icon is a few kilobytes;
#: anything much past that is a logo somebody exported at full detail, and
#: every login page would carry it.
MAX_LENGTH = 64 * 1024


class InvalidSVG(ValueError):
    """Raised when an icon cannot be stored as an SVG document."""


#: How a file widget marks an upload rather than pasted source.
#:
#: The envelope Plone's own ``site_logo`` is stored in, produced by
#: ``plone.formwidget.namedfile``. No SVG document can begin with it, so the
#: prefix is an exact test rather than a guess.
UPLOAD_PREFIX = "filenameb64:"


def _localname(tag: str) -> str:
    """Return an element or attribute name without its namespace.

    :param tag: The name as ``ElementTree`` reports it.
    :returns: The local part.
    """
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _clean(element: ET.Element) -> ET.Element | None:
    """Return a copy of one element carrying only what is allowed.

    :param element: The parsed element.
    :returns: The cleaned element, or ``None`` when the element itself is not
        allowed -- in which case its children go with it.
    """
    name = _localname(element.tag)
    if name not in ALLOWED_ELEMENTS:
        return None

    cleaned = ET.Element(name)
    for key, value in element.attrib.items():
        attribute = _localname(key)
        if attribute not in ALLOWED_ATTRIBUTES:
            continue
        if URL_REFERENCE.search(value or ""):
            continue
        cleaned.set(attribute, value)

    # Text is kept only for the two elements that are meant to carry it. A
    # shape's text content is nothing in SVG, and keeping it would be a way
    # to smuggle a payload past an element filter that only looked at tags.
    if name in {"title", "desc", "text", "tspan"} and element.text:
        cleaned.text = element.text

    for child in element:
        kept = _clean(child)
        if kept is not None:
            cleaned.append(kept)
    return cleaned


def sanitize(source: str) -> str:
    """Return an SVG document with everything but the allowlist removed.

    :param source: The document as supplied.
    :returns: The sanitized document, or the empty string when the input was
        empty -- clearing an icon is a normal thing to do and is not an error.
    :raises InvalidSVG: When the input is not parseable XML, is not rooted at
        an ``svg`` element, or is longer than :data:`MAX_LENGTH`.
    """
    source = (source or "").strip()
    if not source:
        return ""
    if len(source) > MAX_LENGTH:
        raise InvalidSVG(
            f"icon is {len(source)} characters, over the {MAX_LENGTH} limit"
        )

    try:
        root = DefusedET.fromstring(source)
    except Exception as exc:
        raise InvalidSVG(f"icon is not parseable XML: {exc}") from exc

    if _localname(root.tag) != "svg":
        raise InvalidSVG(f"icon is rooted at {_localname(root.tag)!r}, not 'svg'")

    cleaned = _clean(root)
    if cleaned is None:  # pragma: no cover - 'svg' is in the allowlist
        raise InvalidSVG("icon has no usable content")
    # Written back explicitly: ElementTree would otherwise emit the default
    # namespace as ``ns0:`` on every element, which no browser renders.
    cleaned.set("xmlns", SVG_NS)
    return ET.tostring(cleaned, encoding="unicode")


def decode_upload(value: object) -> str:
    """Return the SVG source inside an uploaded value.

    Two shapes reach this, and both are ordinary. A form sends what Plone's
    own file widgets send -- ``filenameb64:<name>;datab64:<bytes>``, the
    envelope ``site_logo`` is stored in -- while an import, a test or a
    GenericSetup profile sends the source itself. Telling them apart on the
    prefix is exact: no SVG document begins with ``filenameb64:``.

    :param value: The uploaded value, as text or bytes.
    :returns: The SVG source, unsanitized. The empty string when nothing was
        supplied, because clearing an icon is an ordinary edit.
    :raises InvalidSVG: When the envelope is malformed, or its payload is not
        valid base64.
    """
    from plone.formwidget.namedfile.converter import b64decode_file

    if not value:
        return ""
    text = value.decode("utf-8", "replace") if isinstance(value, bytes) else str(value)
    if not text.startswith(UPLOAD_PREFIX):
        return text
    try:
        _filename, data = b64decode_file(text.encode("utf-8"))
    except (ValueError, TypeError, BinasciiError) as exc:
        raise InvalidSVG(f"the uploaded file could not be decoded: {exc}") from exc
    return data.decode("utf-8", "replace")


def encode_upload(source: str, filename: str = "icon.svg") -> bytes:
    """Wrap SVG source in the envelope a file widget round-trips.

    What is wrapped is whatever the caller hands over, so callers wrap the
    *sanitized* source -- the dangerous version must never reach the registry,
    a GenericSetup export, or a form that hands it back.

    :param source: The SVG source to carry.
    :param filename: Name to record. Only the widget's label uses it.
    :returns: The envelope, or empty bytes for an empty icon.
    """
    from plone.formwidget.namedfile.converter import b64encode_file

    if not source:
        return b""
    return b64encode_file(filename, source.encode("utf-8"))


def is_svg_upload(value: object) -> bool:
    """Refuse an uploaded file that is not an SVG document.

    A field constraint, so the refusal happens where every other schema
    refusal happens rather than somewhere further in. It runs the real parser
    rather than sniffing the extension or the MIME type the browser guessed:
    an icon is inlined into the login page as markup, so "is this SVG" is a
    question about the bytes and nothing else.

    :param value: The uploaded value.
    :returns: True, or the constraint has raised.
    :raises InvalidSVG: When the upload is not an SVG document this package
        will store. The message names what was wrong with it.
    """
    if not value:
        # Clearing the icon. A required field is what says an icon is
        # mandatory, and this one deliberately is not.
        return True
    sanitize(decode_upload(value))
    return True


__all__ = [
    "ALLOWED_ATTRIBUTES",
    "ALLOWED_ELEMENTS",
    "UPLOAD_PREFIX",
    "InvalidSVG",
    "decode_upload",
    "encode_upload",
    "is_svg_upload",
    "sanitize",
]
