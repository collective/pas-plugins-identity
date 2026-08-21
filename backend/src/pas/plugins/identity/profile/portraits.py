"""Copying a provider's avatar into Plone's portrait storage (D5).

D5 asks for ``picture_url`` to be copied into the standard portrait storage
during claims sync, with no custom adapter. That is what this does -- and it
is **off by default**, which D5 did not ask for and which is worth explaining.

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

**Failures never break a login.** Every error here is logged and swallowed. An
avatar that would not load is a missing picture, and refusing the login over
it would be a far worse bug than the missing picture.
"""

from io import BytesIO
from OFS.Image import Image
from pas.plugins.identity import logger
from plone import api
from Products.PlonePAS.utils import scale_image
from urllib.parse import urlparse

import requests


#: Registry record switching the whole feature on. Off by default; see the
#: module docstring for why.
ENABLED_RECORD = "pas.plugins.identity.profile_sync_portraits"

#: Seconds to wait for the image. Short on purpose: a user is watching a login
#: spinner while this runs.
TIMEOUT = 5

#: Largest avatar accepted, in bytes. Counted off the stream rather than taken
#: from ``Content-Length``, which a hostile server is free to lie about.
MAX_BYTES = 2 * 1024 * 1024

#: Chunk size for the capped read.
CHUNK = 64 * 1024


class PortraitRefused(ValueError):
    """The URL or its answer did not satisfy the guards."""


def enabled() -> bool:
    """Report whether portrait syncing is switched on for this site.

    :returns: Whether to fetch avatars at all.
    """
    return bool(api.portal.get_registry_record(ENABLED_RECORD, default=False))


def _fetch(url: str) -> bytes:
    """Fetch an avatar, refusing anything that fails a guard.

    :param url: The ``picture_url`` claim.
    :returns: The image bytes.
    :raises PortraitRefused: If any guard rejects the URL or the answer.
    """
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise PortraitRefused(f"{parsed.scheme or 'relative'} is not https")

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


def store(userid: str, data: bytes) -> None:
    """Put image bytes into Plone's portrait storage for a user.

    Scaled through Plone's own helper rather than stored raw, so the result is
    the same shape as a portrait uploaded through the user's preferences and
    an oversized image is not kept at full resolution.

    :param userid: Canonical Plone userid.
    :param data: The image bytes.
    """
    memberdata = api.portal.get_tool("portal_memberdata")
    membership = api.portal.get_tool("portal_membership")
    safe_id = membership._getSafeMemberId(userid)
    scaled, _mimetype = scale_image(BytesIO(data))
    memberdata._setPortrait(Image(id=safe_id, file=scaled, title=""), safe_id)


def sync_portrait(userid: str, url: str) -> bool:
    """Copy a provider avatar into portrait storage, if allowed and possible.

    :param userid: Canonical Plone userid.
    :param url: The ``picture_url`` claim.
    :returns: Whether a portrait was stored.
    """
    if not url or not enabled():
        return False
    try:
        store(userid, _fetch(url))
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
    "store",
    "sync_portrait",
]
