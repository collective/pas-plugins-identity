"""A person's picture, wherever this site keeps it.

Keyed by userid rather than by Profile, and that is not an oversight. A user
with no Profile can still have a member portrait, so
``profile.has_picture()`` could not express an answer of ``True`` -- there
would be no object to ask. Which store holds a given user's picture depends on
whether they have a Profile, and a caller should not have to know.
"""

from pas.plugins.identity.core.portraits import has_picture as _has_picture
from pas.plugins.identity.core.portraits import picture_url


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


__all__ = [
    "get_url",
    "has_picture",
]
