"""Which of a person's addresses a site wants first.

A provider may report several addresses for one account, and the order they
arrive in decides what this site does with them: the head of the list is the
``email`` claim, the list is the order a new Profile's addresses start in, and
it is the order linking by email tries them in.
The driver's order is the provider's opinion -- for GitHub, the primary address
first, then the verified ones. A site may hold a better one: an organisation
wants its own domain to stand for its people, and nobody wants a ``noreply``
address to.

So an operator names a preference, an ordered list of entries:

* ``@domain`` matches an address on exactly that domain -- not a subdomain,
  and not a domain that merely ends the same way.
* ``*`` places every address no other entry matches. It is a catch-all rather
  than a first-match wildcard, so the entries after it are still reachable.

An address matching nothing, in a list without ``*``, goes last. The list
orders addresses and never removes one: the provider reported it, and it is
still the person's. Addresses in the same place keep the order the driver gave
them, because the sort is stable.
"""

from collections.abc import Iterable
from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.interfaces import ProviderEmail

import re


#: The entry that places every address no other entry matches.
WILDCARD = "*"

#: ``@`` followed by a domain of at least two labels, lowercased.
_DOMAIN_ENTRY = re.compile(
    r"^@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$"
)


def _entries(preference: Iterable[str] | str | None) -> tuple[str, ...]:
    """Return a preference as the lowercased entries it is compared by.

    :param preference: The preference as stored. A single string is one
        entry, not a sequence of characters.
    :returns: The entries, stripped, lowercased, blanks dropped.
    """
    if isinstance(preference, str):
        preference = (preference,)
    return tuple(
        entry
        for entry in (str(value).strip().lower() for value in preference or ())
        if entry
    )


def is_address_pattern(value: object) -> bool:
    """Report whether a value is one entry of an address preference.

    The field's constraint, and the check a provider save goes through: a
    registry record does not keep a field's constraint, so the form is not the
    only place this has to hold.

    :param value: A candidate entry.
    :returns: Whether it is ``*``, or ``@`` followed by a domain. Case does
        not matter, because entries are compared lowercased.
    """
    if not isinstance(value, str):
        return False
    entry = value.strip().lower()
    return entry == WILDCARD or bool(_DOMAIN_ENTRY.match(entry))


def _place(address: str, entries: tuple[str, ...]) -> int:
    """Return where one address belongs in a preference.

    :param address: The address, lowercased.
    :param entries: The preference's entries, lowercased.
    :returns: The index of the ``@domain`` entry naming its domain; failing
        that the index of the first ``*``; failing that, after every entry.
    """
    domain = address.rpartition("@")[2]
    fallback = len(entries)
    for index, entry in enumerate(entries):
        if entry == WILDCARD:
            fallback = min(fallback, index)
        elif entry[1:] == domain:
            return index
    return fallback


def rank_addresses(
    addresses: Iterable[ProviderEmail], preference: Iterable[str] | str | None
) -> tuple[ProviderEmail, ...]:
    """Order a provider's addresses by a site's preference.

    :param addresses: The addresses, in the order the driver gave them.
    :param preference: The site's entries. Empty keeps the driver's order.
    :returns: Every address, reordered. None is added and none is dropped.
    """
    reported = tuple(addresses)
    entries = _entries(preference)
    if not entries:
        return reported
    return tuple(
        sorted(
            reported,
            key=lambda reported_address: _place(
                str(reported_address.get("address", "")).strip().lower(), entries
            ),
        )
    )


def prefer_addresses(claims: Claims, preference: Iterable[str] | str | None) -> Claims:
    """Apply a site's address preference to a login's claims.

    ``email`` is the head of ``emails``, so reordering the list moves the
    headline address -- and ``email_verified`` with it, because the flag has to
    describe the address beside it.

    :param claims: Normalized claims.
    :param preference: The provider's ``address_preference``.
    :returns: The claims, reordered; the same object when nothing moves.
    """
    reported = tuple(claims.get("emails") or ())
    ranked = rank_addresses(reported, preference)
    if not ranked or ranked == reported:
        return claims
    head = ranked[0]
    preferred = claims.copy()
    preferred["emails"] = ranked
    preferred["email"] = head["address"]
    preferred["email_verified"] = head["verified"]
    return preferred


__all__ = [
    "WILDCARD",
    "is_address_pattern",
    "prefer_addresses",
    "rank_addresses",
]
