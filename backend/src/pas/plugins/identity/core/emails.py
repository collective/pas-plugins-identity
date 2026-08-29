"""A person's addresses, and which of them this site has proved.

A Profile used to carry one address. That is not what a person has: they have
several, they sign in with more than one of them, and which one is *theirs
here* is a question with an answer that changes. So the Profile carries an
ordered ``emails`` tuple, and ``email`` -- the single address every property
sheet, every claim and every enumeration still reads -- is derived from it.

**Verification is not a field.** An address counts as verified when this site
holds an ``email`` identity for it owned by that userid, which is exactly what
a magic link creates and exactly what ``auto_link_by_email`` already consults.
Storing a second ``verified`` flag beside it would be a copy of that fact,
and the two would drift the first time an identity was unlinked.

**Which address ``email`` resolves to.** The first verified address in
``emails``, and failing that the first address at all. The order is the
person's, so this is "your preferred address, unless you have proved a better
one" -- and a Profile with nothing proved still has a usable address rather
than none, which is what keeps a first login working before any link has been
clicked.

**Where the staleness is.** ``email`` is served from catalog *metadata* on
every path that matters, and confirming a magic link does not touch the
Profile -- it writes to the identity store. So linking or unlinking an email
identity reindexes that user's Profile; see
:func:`~pas.plugins.identity.core.subscribers.on_identity_linked`. Without
that the derived address would be correct on the object and wrong everywhere
it is actually read.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.pas import PLUGIN_ID as CORE_PLUGIN_ID
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from plone import api


def normalize(address: object) -> str:
    """Return an address in the form this package stores and compares.

    :param address: Whatever was supplied.
    :returns: The address stripped and lowercased, or the empty string.
    """
    return str(address or "").strip().lower()


def clean(addresses: object) -> tuple[str, ...]:
    """Return a stored address list with the shape everything else assumes.

    Normalized, de-duplicated, order preserved, empties dropped. Applied on
    the way in rather than on the way out, so that what the catalog indexes
    and what a comparison sees are the same strings.

    :param addresses: The value as supplied.
    :returns: The addresses to store.
    """
    seen: list[str] = []
    for candidate in addresses or ():
        address = normalize(candidate)
        if address and address not in seen:
            seen.append(address)
    return tuple(seen)


def _store():
    """Return the identity store, or ``None``.

    :returns: The store held by the core PAS plugin, or ``None`` when this
        package's plugin is not installed in the current site -- which is an
        ordinary answer, not a failure: a Profile can be read on a site whose
        plugins have been removed.
    """
    try:
        acl = api.portal.get_tool("acl_users")
    except api.exc.CannotGetPortalError:
        # No site: an object being constructed outside a request, or a test
        # touching the class directly. Nothing is verified in that world.
        return None
    plugin = getattr(acl, CORE_PLUGIN_ID, None)
    if plugin is None:
        logger.debug("No %s plugin in this site", CORE_PLUGIN_ID)
        return None
    return plugin.store


def is_verified(userid: str, address: str) -> bool:
    """Report whether this site has proved an address belongs to a userid.

    :param userid: Canonical Plone userid.
    :param address: The address to check.
    :returns: Whether an ``email`` identity for it is held for that userid.
        A magic link is the only thing that creates one; a provider asserting
        ``email_verified`` never does.
    """
    store = _store()
    if store is None or not userid or not address:
        return False
    return store.userid_for(EMAIL_PROVIDER, normalize(address)) == userid


def verified_addresses(userid: str, addresses: tuple[str, ...]) -> tuple[str, ...]:
    """Return the subset of a user's addresses this site has proved.

    One store read per address, which is a BTree lookup each. Written as a
    filter rather than by listing the user's email identities because the
    answer has to keep the *profile's* order: it is what
    :func:`preferred_address` picks from.

    :param userid: Canonical Plone userid.
    :param addresses: The addresses on the profile, in the person's order.
    :returns: Those of them that are verified, in the same order.
    """
    store = _store()
    if store is None or not userid:
        return ()
    return tuple(
        address
        for address in addresses
        if store.userid_for(EMAIL_PROVIDER, address) == userid
    )


def preferred_address(userid: str, addresses: tuple[str, ...]) -> str:
    """Return the one address that stands for this person.

    :param userid: Canonical Plone userid.
    :param addresses: The addresses on the profile, in the person's order.
    :returns: The first verified address, the first address at all when none
        is verified, and the empty string when there are none.
    """
    if not addresses:
        return ""
    verified = verified_addresses(userid, addresses)
    return verified[0] if verified else addresses[0]


__all__ = [
    "clean",
    "is_verified",
    "normalize",
    "preferred_address",
    "verified_addresses",
]
