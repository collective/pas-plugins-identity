"""Copying a provider's avatar into Plone's portrait storage.

``picture_url`` is copied into whichever store holds this user's picture:
the ``image`` field on their Profile, or ``portal_memberdata`` for a userid
that has no Profile -- an account created before this add-on was installed
and not signed in with since.

A picture on the Profile **wins** where the user filled it in: a picture
somebody chose beats one a provider supplied. See
:func:`pas.plugins.identity.core.serializer.portrait_of`, which is where the
precedence lives. What lands in ``portal_memberdata`` is the fallback.

Syncing is **off by default**, which is worth explaining.

**Why off by default.** ``picture_url`` is a claim, and at plenty of providers
a claim is whatever the user typed. Turning it into a server-side fetch makes
the login path a request forger: a user who sets their avatar URL to an
address only the backend can reach -- a metadata endpoint, an internal admin
port -- gets the backend to fetch it, and gets the bytes back by looking at
their own portrait. That is a real exposure, it is not obvious from the
feature's description, and no site should acquire it by upgrading. A site that
wants avatars turns the record on having read this.

**What is enforced when it is on.** HTTPS only, so the fetch cannot be
downgraded or aimed at a plain-HTTP internal service; a short timeout, because
this runs while somebody is waiting to log in; a size cap read from the stream
rather than trusted from a header; and a content type the server actually
claims is an image. None of this makes fetching a user-supplied URL safe --
a hostile URL can still name a public host that resolves internally -- which
is why the flag exists rather than a longer list of guards.

**Where it lands depends on the user.** It goes on their Profile, because
that is where a person's fields live and a picture in the other store would
leave the content object showing an empty one. For a userid with no Profile
it is ``portal_memberdata``. One store per user either way, and the same one
a preferences upload uses -- see
:class:`pas.plugins.identity.core.services.users.ProfileUsersPatch` for
the other writer. A picture the user chose is never overwritten: the Profile
remembers which URL the provider supplied, and a provider may replace only
its own.

**Plain HTTP is a per-provider decision.** A provider can be configured to
allow it, and nothing else can: it is a field on the provider rather than a
second site-wide record, because "this one issuer is a container on my own
machine that has no certificate" is a statement about that issuer and not
about the site. It exists because a demo or development stack over plain HTTP
otherwise cannot exercise this path at all, and a feature nobody can run is a
feature nobody has tested. It is off unless somebody sets it, and the whole of
the paragraph above is why it should stay off anywhere a stranger can pick
the URL.

**Failures never break a login.** Every error here is logged and swallowed. An
avatar that would not load is a missing picture, and refusing the login over
it would be a far worse bug than the missing picture.
"""

from io import BytesIO
from OFS.Image import Image
from pas.plugins.identity import logger
from pas.plugins.identity.core.subscribers import get_profile
from pas.plugins.identity.core.subscribers import remember_picture_url
from pas.plugins.identity.core.subscribers import remembered_picture_url
from plone import api
from plone.namedfile.file import NamedBlobImage
from Products.PlonePAS.utils import scale_image
from urllib.parse import urlparse
from zope.lifecycleevent import modified

import requests


#: Registry record switching the whole feature on. Off by default; see the
#: module docstring for why.
ENABLED_RECORD = "pas.plugins.identity.sync_portraits"

#: Seconds to wait for the image. Short on purpose: a user is watching a login
#: spinner while this runs.
TIMEOUT = 5

#: Largest avatar accepted, in bytes. Counted off the stream rather than taken
#: from ``Content-Length``, which a hostile server is free to lie about.
MAX_BYTES = 2 * 1024 * 1024

#: Chunk size for the capped read.
CHUNK = 64 * 1024

#: Filename given to a picture fetched from a provider.
#:
#: A provider's avatar URL rarely ends in something usable, and the field
#: needs *a* name. What it is called matters only in a download header.
PROVIDER_FILENAME = "portrait"


class PortraitRefused(ValueError):
    """The URL or its answer did not satisfy the guards."""


def picture_url(userid: str) -> str | None:
    """Return the URL of the picture held on a user's Profile.

    :param userid: Canonical Plone userid.
    :returns: An absolute URL, or ``None`` when there is no Profile or it has
        no picture. ``None`` is what makes the member portrait the fallback,
        so it has to mean "nothing here" rather than "no Profile".
    """
    profile = get_profile(userid)
    if profile is None or getattr(profile, "image", None) is None:
        return None
    # `@@images` rather than `@@download` so a caller may ask for a scale.
    return f"{profile.absolute_url()}/@@images/image"


def store_provider_picture(userid: str, data: bytes, url: str) -> bool:
    """Store a provider's avatar on a user's Profile, if it may.

    Refused when the user has a picture the provider did not put there. That
    is the precedence a Profile has always claimed -- a picture somebody
    chose beats one a provider supplied -- and it is enforced the same way
    the text fields are: the Profile remembers what the provider last wrote,
    and the provider may replace only that.

    Refusing is not an error. The caller stores the member portrait instead,
    so a user who chose their own Profile picture still gets their provider's
    avatar kept as the fallback nobody sees.

    :param userid: Canonical Plone userid.
    :param data: The image bytes, already fetched and vetted.
    :param url: The claim they came from.
    :returns: Whether it was stored.
    """
    profile = get_profile(userid)
    if profile is None:
        return False

    current = getattr(profile, "image", None)
    if current is not None and not remembered_picture_url(profile):
        # Theirs. Untouched, and the provider does not acquire it by being
        # the next writer.
        return False

    profile.image = NamedBlobImage(
        data=data,
        contentType=_image_type(data),
        filename=PROVIDER_FILENAME,
    )
    remember_picture_url(profile, url)
    # The Profile is catalogued, and users are read out of that catalog; a
    # write nobody reindexed is a write nobody can see.
    modified(profile)
    return True


def _image_type(data: bytes) -> str:
    """Return the image's media type, read from the bytes themselves.

    Not from the response header the fetch saw: :func:`_fetch` already
    refused anything whose header did not claim to be an image, and what is
    stored should be described by what it *is*. An unrecognised image is
    stored as a generic one rather than refused -- it was already vetted, and
    a picture the browser can render is not worth losing to a signature table.

    :param data: The image bytes.
    :returns: A media type.
    """
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"GIF8"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "application/octet-stream"


def has_picture(userid: str) -> bool:
    """Report whether a user has a picture in either store.

    The question the ``[server]`` layer needs before it publishes a
    ``picture`` claim, and it has to be asked of both stores for the same
    reason :func:`pas.plugins.identity.core.serializer.portrait_of` reads
    both: which one holds a given user's picture depends on whether that
    user has a Profile, and the server layer is not allowed to know.

    Asking ``portal_memberdata`` alone is what this replaced. It was correct
    only while every avatar landed there, so it went wrong the moment the
    Profile started winning -- the claim was silently dropped, and a relying
    party cannot tell "this user has no picture" from "the server looked in
    the wrong place".

    :param userid: Canonical Plone userid.
    :returns: Whether a picture exists anywhere for this user.
    """
    if picture_url(userid) is not None:
        return True

    memberdata = api.portal.get_tool("portal_memberdata")
    membership = api.portal.get_tool("portal_membership")
    safe_id = membership._getSafeMemberId(userid)
    return memberdata._getPortrait(safe_id) is not None


def enabled() -> bool:
    """Report whether portrait syncing is switched on for this site.

    :returns: Whether to fetch avatars at all.
    """
    return bool(api.portal.get_registry_record(ENABLED_RECORD, default=False))


def _fetch(url: str, allow_http: bool = False) -> bytes:
    """Fetch an avatar, refusing anything that fails a guard.

    :param url: The ``picture_url`` claim.
    :param allow_http: Whether the provider is configured to allow plain
        HTTP. Never a default: see the module docstring.
    :returns: The image bytes.
    :raises PortraitRefused: If any guard rejects the URL or the answer.
    """
    parsed = urlparse(url)
    allowed = {"https", "http"} if allow_http else {"https"}
    if parsed.scheme not in allowed:
        raise PortraitRefused(
            f"{parsed.scheme or 'relative'} is not {' or '.join(sorted(allowed))}"
        )

    response = requests.get(url, timeout=TIMEOUT, stream=True)
    if response.status_code != 200:
        raise PortraitRefused(f"answered {response.status_code}")

    content_type = response.headers.get("Content-Type", "")
    if not content_type.startswith("image/"):
        raise PortraitRefused(f"answered {content_type or 'no content type'}")

    data = b""
    for chunk in response.iter_content(CHUNK):
        data += chunk
        if len(data) > MAX_BYTES:
            raise PortraitRefused(f"larger than {MAX_BYTES} bytes")
    return data


def store(userid: str, data: bytes, url: str = "") -> None:
    """Put image bytes wherever this user's picture lives.

    Their Profile, for the same reason a portrait uploaded through
    preferences goes there: the Profile is where a person's fields live, and a
    picture in the other store would leave the content object showing an empty
    one. For a user who has no Profile, or who put a picture on it themselves,
    it is ``portal_memberdata`` instead.

    Scaled through Plone's own helper rather than stored raw for the member
    portrait, so the result is the same shape as one uploaded through
    preferences and an oversized image is not kept at full resolution. The
    Profile keeps the bytes: it is a Dexterity image field with scales of its
    own, and pre-scaling would throw away the resolution those want.

    :param userid: Canonical Plone userid.
    :param data: The image bytes.
    :param url: The claim they came from, remembered by the Profile so a
        later sync can tell its own picture from one the user chose.
    """
    if store_provider_picture(userid, data, url):
        return

    memberdata = api.portal.get_tool("portal_memberdata")
    membership = api.portal.get_tool("portal_membership")
    safe_id = membership._getSafeMemberId(userid)
    scaled, _mimetype = scale_image(BytesIO(data))
    memberdata._setPortrait(Image(id=safe_id, file=scaled, title=""), safe_id)


def sync_portrait(userid: str, url: str, allow_http: bool = False) -> bool:
    """Copy a provider avatar into portrait storage, if allowed and possible.

    :param userid: Canonical Plone userid.
    :param url: The ``picture_url`` claim.
    :param allow_http: Whether the provider that sent the URL allows plain
        HTTP. The site-wide switch still has to be on as well.
    :returns: Whether a portrait was stored.
    """
    if not url or not enabled():
        return False
    try:
        store(userid, _fetch(url, allow_http), url)
    except PortraitRefused as refused:
        logger.info("Refused portrait for %s: %s", userid, refused)
        return False
    except Exception:
        # Anything at all: a DNS failure, a truncated stream, an image PIL
        # will not open. A login must not fail over an avatar.
        logger.exception("Could not store portrait for %s", userid)
        return False
    return True


__all__ = [
    "ENABLED_RECORD",
    "PortraitRefused",
    "enabled",
    "has_picture",
    "store",
    "sync_portrait",
]
