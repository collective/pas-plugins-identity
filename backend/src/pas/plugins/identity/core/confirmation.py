"""Asking a person with several verified addresses which one stands for them.

A provider can report more than one address -- a GitHub account often holds
several -- and every one of them lands on the Profile
(:func:`~pas.plugins.identity.core.profiles.sync_addresses`). The first
verified one is the address that stands for the person here. That order is
the provider's, ranked by the provider's ``address_preference``, and by
default nobody is held on a page to arrange it (Érico, 2026-08-29).

A site can ask anyway. With ``confirm_email_at_first_login`` on, a first
sign-in that leaves a Profile with more than one verified address marks it,
and the Profile stays ``incomplete`` until its owner answers through
``POST @confirm-email``.

**An explicit answer, and nothing else.** A login's own address sync writes
the same list the answer reorders, and so does a save made to fill in some
other field. Taking either as the answer would confirm an address nobody was
asked about, so only :func:`confirm` clears the marker.

**After authentication, so no say in linking.** By the time a Profile exists
to mark, ``auto_link_by_email`` has already matched the provider's addresses
in the site's order. ``address_preference`` is what decides that.

**The switch governs the marker.** A marker set while the switch was on counts
only while it still is. Turning the switch off releases a held Profile when it
is next reconciled -- at its owner's next sign-in, or the next write to it --
exactly as a change to ``required_profile_fields`` does.

**Only while there is a choice.** A marked Profile whose owner has since
removed all but one of their verified addresses is not waiting on anything:
holding it would send them to a question with nothing to answer it with. The
marker stays, so a person who verifies a second address again, never having
answered, is asked again.

The marker is an attribute on the Profile and a column in the identity
catalog, so the gate and ``@my-profile`` read it off a brain like everything
else they read.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.container import PREFIX
from pas.plugins.identity.core.utils.emails import normalize
from plone import api
from plone.api.exc import InvalidParameterError
from zope.lifecycleevent import modified


#: Registry record switching the question on. Off by default: the ordered
#: address list is the answer this package gives, and holding somebody on a
#: page to repeat it is a site's choice to make.
CONFIRM_RECORD = f"{PREFIX}.confirm_email_at_first_login"

#: Attribute and catalog column carrying the marker.
PENDING_ATTRIBUTE = "email_confirmation_pending"


class NothingToConfirm(ValueError):
    """The Profile is not waiting on a confirmation."""


class NotAVerifiedAddress(ValueError):
    """The address is not one of the Profile's verified addresses."""


def asking() -> bool:
    """Return whether this site asks at all.

    :returns: The record's value, and ``False`` when the layer's settings are
        not registered here.
    """
    try:
        return bool(api.portal.get_registry_record(CONFIRM_RECORD, default=False))
    except InvalidParameterError:
        return False


def confirmation_pending(profile) -> bool:
    """Return whether a Profile's owner is being asked to confirm an address.

    :param profile: The Profile.
    :returns: Whether the site asks, the Profile is marked, and it still holds
        more than one verified address to choose between.
    """
    return (
        asking()
        and bool(getattr(profile, PENDING_ATTRIBUTE, False))
        and len(profile.verified_emails) > 1
    )


def confirmation_pending_on_brain(brain) -> bool:
    """Return the same answer as :func:`confirmation_pending`, off a brain.

    :param brain: A Profile brain from the identity catalog.
    :returns: Whether the site asks, the Profile is marked, and its
        ``verified_emails`` column holds more than one address.
    """
    return (
        asking()
        and bool(getattr(brain, PENDING_ATTRIBUTE, False))
        and len(tuple(getattr(brain, "verified_emails", None) or ())) > 1
    )


def ask_if_needed(profile) -> bool:
    """Mark a Profile a first sign-in has just minted, when there is a question.

    There is one when the site asks and the Profile carries more than one
    address this site holds verified. Verified *here*: an address a provider
    reports but this site does not trust is not something to choose between.

    The caller runs this elevated. The write ends in a modification event,
    which autoversioning answers with a save the person signing in may not be
    allowed to make.

    :param profile: The Profile.
    :returns: Whether the Profile was marked.
    """
    if not asking():
        return False
    verified = profile.verified_emails
    if len(verified) < 2:
        return False
    setattr(profile, PENDING_ATTRIBUTE, True)
    modified(profile)
    logger.info(
        "Profile %s: asking which of %d verified addresses stands for them",
        profile.getId(),
        len(verified),
    )
    return True


def confirm(profile, address: str) -> str:
    """Record the owner's answer: this address stands for them.

    Moves the address to the front of ``emails``, which is what makes it the
    Profile's ``email``, and clears the marker.

    :param profile: The Profile.
    :param address: The address the owner chose.
    :returns: The address, normalized.
    :raises NothingToConfirm: When the Profile is not waiting on an answer.
    :raises NotAVerifiedAddress: When the address is not one of its verified
        addresses. An unverified one would not become ``email`` even at the
        front of the list, so accepting it would record an answer that
        changes nothing.
    """
    if not confirmation_pending(profile):
        raise NothingToConfirm(profile.getId())
    chosen = normalize(address)
    if not chosen or chosen not in profile.verified_emails:
        raise NotAVerifiedAddress(address)
    profile.emails = (chosen, *(a for a in profile.emails if a != chosen))
    setattr(profile, PENDING_ATTRIBUTE, False)
    modified(profile)
    logger.info("Profile %s: confirmed %s", profile.getId(), chosen)
    return chosen


__all__ = [
    "CONFIRM_RECORD",
    "PENDING_ATTRIBUTE",
    "NotAVerifiedAddress",
    "NothingToConfirm",
    "ask_if_needed",
    "asking",
    "confirm",
    "confirmation_pending",
    "confirmation_pending_on_brain",
]
