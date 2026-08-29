"""First login and claims sync.

Two jobs, both driven purely by the event contract: mint a Profile the
first time somebody logs in, and keep the provider-owned fields on it fresh
without ever overwriting something a human typed.

**How "without overwriting" is decided.** Provider-owned claims refresh on
every login while profile-owned fields are never clobbered, which needs a way
to tell the two apart. Rather than a flag per field -- which has
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

**Which fields.** The provider's own property map, the one the control panel
edits and :mod:`pas.plugins.identity.core.propertymap` applies to the Plone
user, so a site states the mapping once and both the user and the Profile
follow it. Claims are addressed by dotted path there, which is how
``address.formatted`` reaches into a provider's own document; a path landing
on an object rather than a scalar is treated as absent rather than written
as a repr.

``login`` is deliberately not in :data:`WRITABLE_FIELDS`, whatever a map says.
It is half of the case-folded index the enumeration plugin queries and it is
what the identity join is displayed against; a provider renaming somebody
should not silently move their account. Neither is ``group_ids``: a provider
that could edit it could grant itself roles.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.catalog import query_catalog
from pas.plugins.identity.core.completeness import reconcile
from pas.plugins.identity.core.container import get_container
from pas.plugins.identity.core.events import ExternalIdentityAuthenticated
from pas.plugins.identity.core.events import IdentityLinked
from pas.plugins.identity.core.events import UserClaimsRefreshed
from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.profile import UserProfile
from pas.plugins.identity.core.propertymap import resolve_claim
from persistent.mapping import PersistentMapping
from plone import api
from plone.base.utils import safe_text
from zope.annotation.interfaces import IAnnotations
from zope.lifecycleevent import modified


#: Annotation key holding what the provider last wrote, per field. Also the
#: record of *whether* it ever wrote: a field absent from here has never been
#: touched by a provider.
PROVIDER_VALUES_KEY = "pas.plugins.identity.provider_values"

#: UserProfile fields a provider may ever write, whatever its property map says.
#: ``userid`` is the join to the identity store and is permanent; ``login`` is
#: half of the case-folded index the enumeration plugin queries; ``group_ids``
#: is group membership, and a provider that could edit it could grant itself
#: roles. A map naming any of them is ignored rather than refused: the map is
#: typed in a control panel and a typo there must not fail a login.
WRITABLE_FIELDS = frozenset({
    "fullname",
    "email",
    "home_page",
    "description",
    "location",
})

#: Applied when a provider has no property map of its own. Enough to make an
#: account identifiable, which is what an unconfigured provider owes the site.
DEFAULT_CLAIM_FIELDS = {
    "fullname": "fullname",
    "email": "email",
}


def claim_fields(provider_id: str) -> dict[str, str]:
    """Return the claim path to Profile field map for one provider.

    The provider's own map, which is what the control panel edits and what
    :mod:`pas.plugins.identity.core.propertymap` applies to a Plone user, so a
    site configures the mapping once and both the user and the Profile follow
    it. A provider that has no map gets :data:`DEFAULT_CLAIM_FIELDS`.

    :param provider_id: Provider the claims came from.
    :returns: Claim path to Profile field, restricted to
        :data:`WRITABLE_FIELDS`.
    """
    from pas.plugins.identity.core.controlpanel import get_provider

    config = get_provider(provider_id)
    if config is None or not config.propertymap:
        return dict(DEFAULT_CLAIM_FIELDS)
    return {
        path: field
        for path, field in config.propertymap.items()
        if field in WRITABLE_FIELDS
    }


def _scalar(value: object) -> str:
    """Render a resolved claim as text, or as nothing.

    A claim path may land on a list or a mapping -- ``address`` is an object
    at every OIDC provider -- and a Profile field is a line of text. Rather
    than write ``{'formatted': ...}`` into somebody's location, anything that
    is not a scalar is treated as an absent claim, which the caller already
    knows not to write.

    :param value: Whatever the claim path resolved to.
    :returns: The value as text, or an empty string.
    """
    if value is None or isinstance(value, (dict, list, tuple, set)):
        return ""
    if isinstance(value, bool):
        return ""
    return str(value)


def _remembered(profile: UserProfile) -> PersistentMapping:
    """Return the mutable record of provider-written values.

    :param profile: The Profile.
    :returns: A persistent mapping of field name to value.
    """
    annotations = IAnnotations(profile)
    if PROVIDER_VALUES_KEY not in annotations:
        annotations[PROVIDER_VALUES_KEY] = PersistentMapping()
    return annotations[PROVIDER_VALUES_KEY]


def _provider_may_write(
    profile: UserProfile, field: str, remembered: PersistentMapping
) -> bool:
    """Decide whether the provider still owns a field.

    :param profile: The Profile.
    :param field: Field name.
    :param remembered: What the provider last wrote, per field.
    :returns: Whether the current value is still the provider's own.
    """
    current = getattr(profile, field, None) or ""
    return current == (remembered.get(field) or "")


#: Key under which the provider's picture URL is remembered.
#:
#: In the same mapping as the text fields, because it is the same rule: the
#: provider may replace only what it put there. What is remembered is the
#: *URL* rather than the bytes -- comparing blobs to decide ownership would
#: read the whole image on every login, and the URL answers the question just
#: as well.
PICTURE_FIELD = "picture"


def remembered_picture_url(profile: UserProfile) -> str:
    """Return the picture URL the provider last wrote, if any.

    :param profile: The Profile.
    :returns: The URL, or the empty string when the picture on this Profile
        is not the provider's -- which includes a Profile whose picture the
        user uploaded, and one that has never had a picture at all.
    """
    return str(_remembered(profile).get(PICTURE_FIELD) or "")


def remember_picture_url(profile: UserProfile, url: str) -> None:
    """Record that the provider supplied this Profile's picture.

    :param profile: The Profile.
    :param url: The ``picture_url`` claim, or the empty string to hand
        ownership back -- which is what a user uploading their own picture
        does, and what stops a provider from replacing it later.
    """
    remembered = _remembered(profile)
    if url:
        remembered[PICTURE_FIELD] = url
    else:
        remembered.pop(PICTURE_FIELD, None)


def sync_claims(
    profile: UserProfile, claims: Claims, provider_id: str = ""
) -> list[str]:
    """Write the provider's claims onto the fields it still owns.

    :param profile: The Profile.
    :param claims: Normalized claims.
    :param provider_id: Provider the claims came from. Empty means "no
        provider in particular", which takes :data:`DEFAULT_CLAIM_FIELDS`.
    :returns: The fields that actually changed.
    """
    remembered = _remembered(profile)
    changed = []
    for claim, field in claim_fields(provider_id).items():
        value = safe_text(_scalar(resolve_claim(claim, claims)))
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
    changes, so the Profile never has to be renamed -- and a rename is
    the one operation that can strand a URL somebody bookmarked.

    :param userid: Canonical Plone userid.
    :returns: The object id.
    """
    return userid


def get_profile(userid: str) -> UserProfile | None:
    """Return a user's Profile object, or ``None``.

    Wakes the object, so this is for the paths that are going to write to it.
    Reads that only need a value should go through the catalog; see
    :mod:`pas.plugins.identity.core.pas.profile`.

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


def profile_url(userid: str) -> str | None:
    """Return the URL of a user's Profile.

    :param userid: Canonical Plone userid.
    :returns: The absolute URL, or ``None`` when the user has none -- an
        account created before this add-on was installed and never signed in
        with since, or one filed somewhere this site does not catalog.
    """
    profile = get_profile(userid)
    return profile.absolute_url() if profile is not None else None


def ensure_profile(userid: str, login: str, claims: Claims) -> UserProfile | None:
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


def _handle(userid: str, claims: Claims, provider_id: str) -> None:
    """Ensure the Profile exists and sync the claims onto it.

    :param userid: Canonical Plone userid.
    :param claims: Normalized claims.
    :param provider_id: Provider the claims came from.
    """
    profile = ensure_profile(userid, _login_for(userid, claims), claims)
    if profile is None:
        return
    sync_claims(profile, claims, provider_id)
    # After the claims, not before: a provider that has just supplied the
    # missing email completes the profile in the same login rather than in the
    # next one.
    reconcile(profile)


def on_profile_modified(profile: UserProfile, event) -> None:
    """Re-examine a profile whenever anything writes to it.

    The other half of the login-time reconciliation. Without this a user who
    has just filled the form in stays ``incomplete`` until their next sign-in
    and is sent straight back to the form they have already completed, which
    is the shape of loop the whole flow exists to avoid.

    Covers every writer for the same reason: the edit form, ``@users`` PATCH,
    user preferences, an import, and a site administrator fixing something by
    hand all end in a modification event.

    :param profile: The profile that was written to.
    :param event: The modification event, unused.
    """
    reconcile(profile)


def on_authenticated(event: ExternalIdentityAuthenticated) -> None:
    """Mint the Profile on first login and refresh claims on every one.

    :param event: An ``ExternalIdentityAuthenticated`` event.
    """
    _handle(event.userid, event.claims, event.provider)


#: Profile fields seeded from a member's existing property sheets.
#:
#: Only what a stock Plone site already knows about somebody. The Profile is
#: minted from what the site holds rather than from nothing, so a user who has
#: had a fullname and an address here for years is not asked to type them in
#: again the first time they sign in after the layer is installed.
SEEDED_FROM_MEMBER = ("fullname", "email", "home_page", "description", "location")


def _seed_from_member(profile: UserProfile, member) -> None:
    """Copy what the site already knows onto a newly minted Profile.

    Read through ``getProperty``, which is the ordered sheets and therefore
    every store the site has -- not ``portal_memberdata`` by name, because a
    site may have replaced it.

    :param profile: The Profile just created.
    :param member: The ``MemberData`` wrapper for the same user.
    """
    for field in SEEDED_FROM_MEMBER:
        if getattr(profile, field, None):
            continue
        value = member.getProperty(field, "")
        if value:
            setattr(profile, field, safe_text(value))


def on_logged_in(event) -> None:
    """Bring a user logging in by any means into the required-information flow.

    Until this existed the flow reached exactly one kind of user. Everything
    that mints a Profile or reconciles one hangs off
    ``ExternalIdentityAuthenticated``, which only a federated sign-in fires --
    so somebody authenticated by ``source_users``, or by any other PAS plugin,
    never had a Profile minted and was never reconciled. The gate then found
    nothing to hold them for and let them through, which made
    ``enforce_required_profile_fields`` a rule about where a user came from
    rather than about what the site requires of them (Érico, 2026-08-28).

    Minting here is safe on a site that has not asked for users as content:
    :func:`ensure_profile` answers ``None`` when this layer's catalog is
    absent, and installing the layer is what points core's principal records
    at it.

    The Zope root user is skipped. It is not a member of this site -- it lives
    in the root acl_users and the portal's own PAS cannot resolve it -- and
    minting a Profile would file the emergency account among the site's users.

    :param event: An ``IUserLoggedInEvent``.
    """
    principal = getattr(event, "principal", None)
    userid = getattr(principal, "getId", lambda: None)()
    if not userid:
        return
    if api.portal.get_tool("acl_users").getUserById(userid) is None:
        # The Zope root user, or anyone else this site does not hold.
        return

    member = api.user.get(userid=userid)
    if member is None:  # pragma: no cover - PAS just resolved this userid
        return

    profile = get_profile(userid)
    if profile is None:
        profile = ensure_profile(userid, safe_text(principal.getUserName()), {})
        if profile is None:
            return
        _seed_from_member(profile, member)
    reconcile(profile)


def on_identity_linked(event: IdentityLinked) -> None:
    """Fill still-provider-owned fields from a newly linked provider.

    Somebody who linked GitHub after signing up with a provider that sent no
    full name should end up with the name GitHub knows, without that counting
    as overwriting anything.

    :param event: An ``IdentityLinked`` event.
    """
    _handle(event.userid, event.claims, event.provider)


def on_claims_refreshed(event: UserClaimsRefreshed) -> None:
    """Apply a claims refresh fired outside the login path.

    :param event: A ``UserClaimsRefreshed`` event.
    """
    _handle(event.userid, event.claims, event.provider)


__all__ = [
    "claim_fields",
    "ensure_profile",
    "get_profile",
    "on_authenticated",
    "on_claims_refreshed",
    "on_identity_linked",
    "on_logged_in",
    "profile_url",
    "sync_claims",
]
