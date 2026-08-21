"""First login and claims sync (§4.7, D2).

Two jobs, both driven purely by the §4.3 event contract: mint a Profile the
first time somebody logs in, and keep the provider-owned fields on it fresh
without ever overwriting something a human typed.

**How "without overwriting" is decided.** D2 says provider-owned claims
refresh on every login while profile-owned fields are never clobbered, which
needs a way to tell the two apart. Rather than a flag per field -- which has
to be set somewhere, kept in step, and migrated -- the Profile remembers what
the provider last wrote, and the provider may write a field only when the
current value still equals that. One comparison covers every case:

=========================================  =======================  ========
Situation                                  Current vs remembered    Written?
=========================================  =======================  ========
Fresh Profile, nothing written yet         ``""`` == ``""``         yes
Provider changed the claim since login     equal                    yes
User edited the field                      differs                  no
User cleared the field                     ``""`` vs remembered     no
Administrator typed it in by hand          differs                  no
=========================================  =======================  ========

The last two rows are the ones a flag-based design tends to get wrong:
clearing a field is an edit, and a value that reappears at the next login is
indistinguishable from a bug.

Nothing here commits. Login runs inside the request's transaction, and a
Profile minted for a login that then fails should not outlive it.

``login`` is deliberately not synced. It is half of the case-folded index the
enumeration plugin queries and it is what the identity join is displayed
against; a provider renaming somebody should not silently move their account.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.profile.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.profile.catalog import query_catalog
from pas.plugins.identity.profile.container import get_container
from pas.plugins.identity.profile.portraits import sync_portrait
from persistent.mapping import PersistentMapping
from plone import api
from plone.base.utils import safe_text
from typing import Any
from zope.annotation.interfaces import IAnnotations
from zope.lifecycleevent import modified


#: Annotation key holding what the provider last wrote, per field. Also the
#: record of *whether* it ever wrote: a field absent from here has never been
#: touched by a provider.
PROVIDER_VALUES_KEY = "pas.plugins.identity.provider_values"

#: Claim name to Profile field. Only what a provider legitimately owns; see
#: the module docstring for why ``login`` is not here.
CLAIM_FIELDS = {
    "fullname": "fullname",
    "email": "email",
}

#: Key under which the last-synced avatar URL is remembered. Kept alongside
#: the field values so the portrait is fetched when the provider changes it
#: and not on every login -- this is the one part of the sync that makes a
#: network request, and it runs while somebody waits for a page.
PICTURE_KEY = "picture_url"


def _remembered(profile: Any) -> Any:
    """Return the mutable record of provider-written values.

    :param profile: The Profile.
    :returns: A persistent mapping of field name to value.
    """
    annotations = IAnnotations(profile)
    if PROVIDER_VALUES_KEY not in annotations:
        annotations[PROVIDER_VALUES_KEY] = PersistentMapping()
    return annotations[PROVIDER_VALUES_KEY]


def _provider_may_write(profile: Any, field: str, remembered: Any) -> bool:
    """Decide whether the provider still owns a field (D2).

    :param profile: The Profile.
    :param field: Field name.
    :param remembered: What the provider last wrote, per field.
    :returns: Whether the current value is still the provider's own.
    """
    current = getattr(profile, field, None) or ""
    return current == (remembered.get(field) or "")


def sync_claims(profile: Any, claims: Claims) -> list[str]:
    """Write the provider's claims onto the fields it still owns.

    :param profile: The Profile.
    :param claims: Normalized claims.
    :returns: The fields that actually changed.
    """
    remembered = _remembered(profile)
    changed = []
    for claim, field in CLAIM_FIELDS.items():
        value = safe_text(claims.get(claim) or "")
        if not value:
            # An absent claim is not an instruction to clear the field. A
            # provider that stops sending a name has not told us the user no
            # longer has one.
            continue
        if not _provider_may_write(profile, field, remembered):
            continue
        if (getattr(profile, field, None) or "") != value:
            setattr(profile, field, value)
            changed.append(field)
        remembered[field] = value

    if changed:
        modified(profile)
    return changed


def _profile_id(userid: str) -> str:
    """Return the container id to file a userid's Profile under.

    The canonical userid, not a normalized name. It is opaque and it never
    changes (I1), so the Profile never has to be renamed -- and a rename is
    the one operation that can strand a URL somebody bookmarked.

    :param userid: Canonical Plone userid.
    :returns: The object id.
    """
    return userid


def get_profile(userid: str) -> Any | None:
    """Return a user's Profile object, or ``None``.

    Wakes the object, so this is for the paths that are going to write to it.
    Reads that only need a value should go through the catalog; see
    :mod:`pas.plugins.identity.profile.pas`.

    :param userid: Canonical Plone userid.
    :returns: The Profile, or ``None``.
    """
    catalog = query_catalog()
    if catalog is None:
        return None
    brains = catalog.unrestrictedSearchResults(userid=userid)
    if not brains:
        return None
    return brains[0]._unrestrictedGetObject()


def ensure_profile(userid: str, login: str, claims: Claims) -> Any | None:
    """Return the user's Profile, creating it on first login.

    Runs unrestricted: the person this Profile is for is mid-login and holds
    no roles yet, and an add permission that an ordinary member could satisfy
    would be a way to mint accounts.

    :param userid: Canonical Plone userid.
    :param login: Login name to record.
    :param claims: Normalized claims to seed from.
    :returns: The Profile, or ``None`` when the layer is not installed here.
    """
    if query_catalog() is None:
        return None

    profile = get_profile(userid)
    if profile is not None:
        return profile

    with api.env.adopt_roles(["Manager"]):
        container = get_container(create=True)
        profile = api.content.create(
            container=container,
            type=PROFILE_PORTAL_TYPE,
            id=_profile_id(userid),
            userid=userid,
            login=login,
        )
    logger.info("Created profile for %s", userid)
    return profile


def _login_for(userid: str, claims: Claims) -> str:
    """Choose the login name to record on a new Profile.

    The provider's username when it sent one, the email otherwise, and the
    userid as a last resort -- the field is required, and a Profile that
    cannot be created is a login that fails.

    :param userid: Canonical Plone userid.
    :param claims: Normalized claims.
    :returns: A non-empty login name.
    """
    return safe_text(claims.get("username") or claims.get("email") or userid)


def sync_picture(profile: Any, userid: str, claims: Claims) -> bool:
    """Copy the provider's avatar into portrait storage when it changed (D5).

    Off unless the site switched it on; see
    :mod:`pas.plugins.identity.profile.portraits` for why that is the default.

    :param profile: The Profile, which remembers the last URL synced.
    :param userid: Canonical Plone userid.
    :param claims: Normalized claims.
    :returns: Whether a portrait was stored.
    """
    url = safe_text(claims.get("picture_url") or "")
    remembered = _remembered(profile)
    if not url or url == remembered.get(PICTURE_KEY):
        return False
    # Remembered whether or not the fetch succeeds. A URL that failed once
    # will fail again, and retrying it on every login turns one bad avatar
    # into a permanent tax on that user's sign-in.
    remembered[PICTURE_KEY] = url
    return sync_portrait(userid, url)


def _handle(userid: str, claims: Claims) -> None:
    """Ensure the Profile exists and sync the claims onto it.

    :param userid: Canonical Plone userid.
    :param claims: Normalized claims.
    """
    profile = ensure_profile(userid, _login_for(userid, claims), claims)
    if profile is None:
        return
    sync_claims(profile, claims)
    sync_picture(profile, userid, claims)


def on_authenticated(event: Any) -> None:
    """Mint the Profile on first login and refresh claims on every one (D2).

    :param event: An ``ExternalIdentityAuthenticated`` event.
    """
    _handle(event.userid, event.claims)


def on_identity_linked(event: Any) -> None:
    """Fill still-provider-owned fields from a newly linked provider.

    Somebody who linked GitHub after signing up with a provider that sent no
    full name should end up with the name GitHub knows, without that counting
    as overwriting anything.

    :param event: An ``IdentityLinked`` event.
    """
    _handle(event.userid, event.claims)


def on_claims_refreshed(event: Any) -> None:
    """Apply a claims refresh fired outside the login path.

    :param event: A ``UserClaimsRefreshed`` event.
    """
    _handle(event.userid, event.claims)


__all__ = [
    "ensure_profile",
    "get_profile",
    "on_authenticated",
    "on_claims_refreshed",
    "on_identity_linked",
    "sync_claims",
    "sync_picture",
]
