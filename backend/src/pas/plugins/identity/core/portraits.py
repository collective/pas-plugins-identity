"""Copying a provider's avatar into Plone's portrait storage.

``picture_url`` is copied into the standard portrait storage on login, with
no custom adapter -- ``portal_memberdata``, the same place a portrait
uploaded through user preferences goes. It stays there rather than moving to
the ``[profile]`` layer's Dexterity type, because a portrait synced from a
provider has to work the same whether or not that optional layer is
installed.

The ``[profile]`` type *does* have a picture field now, and it **wins** where
a user has filled it in: a picture somebody chose beats one a provider
supplied. See :func:`pas.plugins.identity.core.serializer.portrait_of`, which
is where the precedence lives. What is written here is the fallback.

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

**Where it lands depends on the site.** On one running the ``[profile]``
layer the picture goes on the user's Profile, because that is where that site
keeps a person's fields and a picture in the other store would leave the
content object showing an empty one. Everywhere else it is
``portal_memberdata``. One store per user either way, and the same one a
preferences upload uses -- see
:class:`pas.plugins.identity.profile.services.users.ProfileUsersPatch` for
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
from pas.plugins.identity.core.interfaces import IProfileSupport
from plone import api
from Products.PlonePAS.utils import scale_image
from urllib.parse import urlparse
from zope.component import queryUtility

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


class PortraitRefused(ValueError):
    """The URL or its answer did not satisfy the guards."""


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
    support = queryUtility(IProfileSupport)
    if support is not None and support.picture_url(userid) is not None:
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

    On a site running the ``[profile]`` layer that is the Profile, for the
    same reason a portrait uploaded through preferences goes there: the
    Profile is where that site keeps a person's fields, and a picture in the
    other store would leave the content object showing an empty one. Without
    the layer -- or for a user who has no Profile, or who put a picture on it
    themselves -- it is ``portal_memberdata``, exactly as before.

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
    support = queryUtility(IProfileSupport)
    if support is not None and support.store_provider_picture(userid, data, url):
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
