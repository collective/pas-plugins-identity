"""A person's picture, wherever this site keeps it.

Keyed by userid rather than by Profile, and that is not an oversight. A user
with no Profile can still have a member portrait, so
``profile.has_picture()`` could not express an answer of ``True`` -- there
would be no object to ask. Which store holds a given user's picture depends on
whether they have a Profile, and a caller should not have to know.

The same holds for writing one. A package that seeds its users ahead of their
first login stores their pictures through the same rules a login applies,
rather than reimplementing where a picture goes and whose picture may be
replaced.
"""

from pas.plugins.identity.core.portraits import has_picture as _has_picture
from pas.plugins.identity.core.portraits import picture_url
from pas.plugins.identity.core.portraits import store as _store
from pas.plugins.identity.core.portraits import sync_portrait as _sync_portrait


def has_picture(userid: str) -> bool:
    """Report whether a user has a picture in either store.

    Asks the Profile *and* ``portal_memberdata``. Asking either one alone goes
    wrong the moment a site holds both kinds of user, and the failure is
    silent: a relying party cannot tell "this person has no picture" from
    "the server looked in the wrong place".

    :param userid: Canonical Plone userid.
    :returns: Whether a picture exists anywhere for this user.
    """
    return _has_picture(userid)


def get_url(userid: str) -> str | None:
    """Return the URL of a user's picture, when the Profile holds one.

    :param userid: Canonical Plone userid.
    :returns: An absolute URL, or ``None`` when this user's Profile has no
        picture. ``None`` here is not the same question as
        :func:`has_picture`, which also looks in ``portal_memberdata``.
    """
    return picture_url(userid)


def store(userid: str, data: bytes, url: str = "") -> None:
    """Store image bytes as a user's picture.

    For a caller that already holds the bytes -- an import that downloaded
    and cached its pictures beforehand. The picture goes on the Profile, where
    a login would put it, unless the user has none or chose a picture of their
    own there; then it goes to ``portal_memberdata``, scaled the way an upload
    through preferences is.

    :param userid: Canonical Plone userid.
    :param data: The image bytes.
    :param url: Where they came from. The Profile remembers it, so a later
        login can tell this picture from one the user chose and replace it.
    :raises Exception: When the bytes are not an image this site can scale.
        An operation that cannot proceed raises.
    """
    _store(userid, data, url)


def sync_portrait(userid: str, url: str, allow_http: bool = False) -> bool:
    """Fetch a picture from a URL and store it, with a login's checks.

    For a caller that holds only a URL. The fetch is the one a login makes:
    nothing happens unless the site-wide portrait switch is on, the URL must
    be HTTPS unless ``allow_http`` is set, and the site's timeout and size
    limit apply. What it fetches is stored as :func:`store` stores it.

    Answers ``False`` rather than raising, because a login must not fail over
    an avatar -- and that includes a refusal. A batch import therefore learns
    *why* a picture was refused only from the log.

    :param userid: Canonical Plone userid.
    :param url: The image URL.
    :param allow_http: Whether plain HTTP is acceptable for this URL.
    :returns: Whether a picture was stored.
    """
    return _sync_portrait(userid, url, allow_http)


__all__ = [
    "get_url",
    "has_picture",
    "store",
    "sync_portrait",
]
