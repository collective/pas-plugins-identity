"""Finding a person's Profile.

The lookup half of the façade: given a userid, or given nobody at all, return
the :class:`~pas.plugins.identity.core.contents.profile.UserProfile` object.
Questions answerable *from* a Profile are methods on it rather than functions
here -- :attr:`~pas.plugins.identity.core.contents.profile.UserProfile.email`
and :attr:`~pas.plugins.identity.core.contents.profile.UserProfile.verified_emails`
are the pattern -- and its URL is ``profile.absolute_url()``, which is why this
module offers no ``url`` of its own.
"""

from pas.plugins.identity.core.contents.profile import UserProfile
from pas.plugins.identity.core.profiles import ensure_profile
from pas.plugins.identity.core.profiles import get_profile
from plone import api as plone_api


def get(userid: str) -> UserProfile | None:
    """Return a user's Profile, or ``None``.

    The userid is required, and there is deliberately no default. A default
    falling back to the current user would make ``None`` mean two things at
    once -- "I did not say whose" and "the lookup missed" -- and only the
    caller knows which. Worse, ``get(brain.userid)`` on a brain whose metadata
    was missing would answer with *the caller's own Profile*, and every check
    downstream would pass. In a package whose job is telling people apart,
    that is the worst available direction for a silent fallback. Ask for the
    current user's Profile with :func:`get_current`.

    Wakes the object. Reads that only need one value should go through the
    catalog; see :mod:`pas.plugins.identity.core.pas.profile`.

    :param userid: Canonical Plone userid.
    :returns: The Profile, or ``None`` when this user has none -- an account
        that predates the add-on and has not signed in since, or a site not
        keeping users as content.
    """
    if not userid:
        return None
    return get_profile(userid)


def get_current() -> UserProfile | None:
    """Return the current user's Profile, or ``None``.

    Named after :func:`plone.api.user.get_current`, and split from :func:`get`
    for the same reason ``plone.api`` splits them: an argument that may be
    absent turns one function into two questions with one answer shape.

    :returns: The Profile, or ``None`` -- which covers an anonymous caller as
        well as a signed-in one who has no Profile. Anonymous is not an
        error here: a view asking "does the person reading this have a
        Profile" wants ``None``, not an exception.
    """
    user = plone_api.user.get_current()
    userid = user.getId() if user is not None else None
    if not userid:
        # Anonymous. ``getId()`` is None for the anonymous user, so this is
        # the same branch as "no userid" rather than a separate check.
        return None
    return get_profile(userid)


def get_or_create(userid: str, login: str) -> UserProfile | None:
    """Return a user's Profile, minting one if this is their first sign-in.

    Runs unrestricted: the person is typically mid-login and holds no roles
    yet, and an add permission an ordinary member could satisfy would be a way
    to mint accounts.

    :param userid: Canonical Plone userid.
    :param login: Login name to record on a Profile that has to be created.
        Required because the field is: a Profile that cannot be created is a
        login that fails.
    :returns: The Profile, or ``None`` when this site does not keep users as
        content -- there is no catalog to file one in.
    """
    return ensure_profile(userid, login, {})


__all__ = [
    "get",
    "get_current",
    "get_or_create",
]
