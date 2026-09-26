"""Two answers to ``SearchableText``, chosen by which catalog is asking.

Kept together because neither makes sense alone: which one a catalog gets is
decided by how specifically each is registered, and each one's docstring is
half of that explanation.
"""

from pas.plugins.identity.core.contents.profile import UserProfile
from pas.plugins.identity.core.interfaces import IIdentityProfileCatalog
from pas.plugins.identity.core.interfaces import IUserProfile
from plone.indexer.decorator import indexer


@indexer(IUserProfile, IIdentityProfileCatalog)
def searchable_text_index(obj: UserProfile) -> str:
    """Index full name, login and email as one text blob, for enumeration.

    Deliberately not the biography: a Sharing-tab search for a user should not
    match somebody who happens to mention them in their own bio. The site's
    own search asks a different question and gets a different answer -- see
    :func:`site_searchable_text_index`.

    :param obj: The Profile.
    :returns: Space-joined searchable text.
    """
    return " ".join(value for value in (obj.fullname, obj.login, obj.email) if value)


@indexer(IUserProfile)
def site_searchable_text_index(obj: UserProfile) -> str:
    """Index title, id and biography, for ``portal_catalog``.

    A Profile is a ``Container``, so Plone catalogs it in the site catalog like
    any other content, and it turns up in site search. What it should be
    findable *by* there is not what enumeration searches on:

    * a visitor types a name, so the title;
    * a userid is what a URL and a link carry, so the id;
    * a biography is the one thing on a Profile written to be read, so the
      description.

    Not the login and not the address. A login is half the case-folded index
    the enumeration plugin queries and has no business in site search, and
    publishing addresses to it would make the site's own search box an email
    harvester.

    **Registered for one argument on purpose, and that is the whole mechanism.**
    An indexer declared ``@indexer(IUserProfile)`` is registered against any
    catalog; the one above names :class:`IIdentityProfileCatalog` as well and is
    therefore more specific, so the multi-adapter lookup prefers it there and
    falls back to this one everywhere else. Two answers to ``SearchableText``,
    chosen by which catalog is asking.

    Before this existed, the narrow version above answered *both* catalogs,
    because it too was registered for one argument -- so a Profile's entry in
    site search was full name, login and email, and its biography was not
    searchable at all.

    :param obj: The Profile.
    :returns: Space-joined searchable text.
    """
    return " ".join(
        value for value in (obj.Title(), obj.getId(), obj.Description()) if value
    )
