"""Event handlers for first login, claims sync and group ids.

Handlers only. What they do to a Profile -- finding it, minting it, writing
the provider's claims onto the fields it still owns -- lives in
:mod:`pas.plugins.identity.core.profiles`, which is also where the rule for
"refresh without overwriting" is written down.

Two jobs, both driven purely by the event contract: mint a Profile the first
time somebody logs in, and keep the provider-owned fields on it fresh without
ever overwriting something a human typed.

Nothing here commits. Login runs inside the request's transaction, and a
Profile minted for a login that then fails should not outlive it.
"""

from pas.plugins.identity.core.catalog import GROUP_PORTAL_TYPE
from pas.plugins.identity.core.catalog import query_catalog
from pas.plugins.identity.core.completeness import reconcile
from pas.plugins.identity.core.confirmation import ask_if_needed
from pas.plugins.identity.core.contents.profile import UserProfile
from pas.plugins.identity.core.enrichment import enrich_profile
from pas.plugins.identity.core.events import ExternalIdentityAuthenticated
from pas.plugins.identity.core.events import IdentityLinked
from pas.plugins.identity.core.events import UserClaimsRefreshed
from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.profiles import ensure_profile
from pas.plugins.identity.core.profiles import get_profile
from pas.plugins.identity.core.profiles import sync_addresses
from pas.plugins.identity.core.profiles import sync_claims
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from pas.plugins.identity.core.verification import record_verified_addresses
from plone import api
from plone.base.utils import safe_text


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


def _handle(
    userid: str, claims: Claims, provider_id: str, sign_in: bool = False
) -> None:
    """Ensure the Profile exists and sync the claims onto it.

    :param userid: Canonical Plone userid.
    :param claims: Normalized claims.
    :param provider_id: Provider the claims came from.
    :param sign_in: Whether this is a sign-in, rather than a link or a refresh.
        Only a Profile minted by a sign-in is asked to confirm an address:
        linking another provider, or a refresh fired outside the login path,
        is nobody's first sign-in.
    """
    minted = sign_in and get_profile(userid) is None
    profile = ensure_profile(userid, _login_for(userid, claims), claims)
    if profile is not None:
        # Unrestricted for the same reason the creation above is: the person
        # is mid-login and holds no roles yet, and these writes are the
        # package acting rather than the user editing.
        #
        # It became load-bearing when the Profile became versionable. Both
        # helpers end in a modification event when they change something,
        # ``at_edit_autoversion`` answers it by calling
        # ``portal_repository.save``, and that is a permission the user being
        # logged in does not have -- so a first federated login failed with
        # "You are not allowed to access 'save' in this context", reported to
        # the caller as a 401 from the callback.
        with api.env.adopt_roles(["Manager"]):
            sync_claims(profile, claims, provider_id)
            sync_addresses(profile, claims)
    # After the addresses rather than before, so that an address this login
    # has just proved is already on the Profile whose derived `email` it
    # changes. Outside the `is not None` because verification is a fact about
    # the identity store: a site not keeping users as content has no Profile
    # and still has addresses to prove.
    record_verified_addresses(userid, provider_id, claims)
    if profile is None:
        return
    # After the package's own writes and after verification, so that what an
    # enricher sees is the Profile this login is leaving behind rather than a
    # half-written one: claims synced, addresses appended, and the derived
    # `email` settled by whatever has just been proved. Elevated for the same
    # reason as the block above, and one reason more -- an enricher writes a
    # field belonging to somebody else's behavior, which the person signing in
    # may well not hold the permission for.
    #
    # Before `reconcile`, so a required field an enricher has just filled
    # counts in this login rather than in the next one.
    with api.env.adopt_roles(["Manager"]):
        # The provider, not just its id: an enricher needs `driver_id` to know
        # what shape the payload is in, and `provider_id` to tell two
        # deployments of the same kind apart. `None` where there is no
        # provider, which is every path that fires with an empty `raw`.
        from pas.plugins.identity.core.controlpanel import get_provider

        enrich_profile(profile, claims, get_provider(provider_id))
        # After verification, whose result it counts, and before `reconcile`,
        # which is what holds the Profile for the answer.
        if minted:
            ask_if_needed(profile)
    # Last: a provider that has just supplied the missing address completes
    # the profile in the same login rather than in the next one.
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
    _handle(event.userid, event.claims, event.provider, sign_in=True)


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
    :func:`~pas.plugins.identity.core.profiles.ensure_profile` answers ``None``
    when this layer's catalog is absent, and installing the layer is what
    points core's principal records at it.

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


def on_email_identity_changed(event) -> None:
    """Reindex a Profile whose set of verified addresses just changed.

    ``email`` and ``verified_emails`` are derived from the identity store, and
    every path that matters reads them from catalog *metadata* -- the property
    sheet, enumeration, the OIDC claims. Confirming or removing a magic-link
    identity writes to the store and never touches the Profile, so without
    this the derived values stay correct on the object and wrong everywhere
    they are actually read.

    Only the email provider matters here: no other provider's identity can
    change which of a person's addresses this site has proved.

    :param event: An ``IdentityLinked`` or ``IdentityUnlinked`` event.
    """
    if event.provider != EMAIL_PROVIDER:
        return
    profile = get_profile(event.userid)
    if profile is None:
        return
    catalog = query_catalog()
    if catalog is not None:
        catalog.reindexObject(profile)
    # The state as well as the metadata. Removing an address can leave a
    # Profile held for an address confirmation with nothing left to choose
    # between (see ``core.confirmation``), and nothing else writes to the
    # Profile to reconcile it.
    reconcile(profile)


class DuplicateGroupId(ValueError):
    """Another group in this site already answers to this group id."""


def refuse_duplicate_group(group, event) -> None:
    """Refuse a second group content object claiming an existing group id.

    A group id is the object's own id, and object ids are unique only within
    one container. Once a group may be filed *inside* another group, two
    containers can each hold a ``developers`` -- and a group id is what local
    roles, sharing entries and every ``group_ids`` field in the site are
    written in terms of. Two objects answering to one would mean membership
    that resolves to whichever the catalog returned first, and a removal that
    deletes one and leaves the other still granting.

    So it is refused at the point it is created, where the message can name
    the group that is already using the id. The alternative -- letting both
    exist and picking one -- is a site that looks fine and grants the wrong
    access.

    Bound to the group marker rather than to the portal type, so a site's own
    group type is held to the same rule. Registered for the *move* event
    rather than the add: adding is one of the ways a group arrives at an id
    and renaming is the other, and a rename fires no add event at all -- so a
    guard on adding alone is one ``manage_renameObject`` away from the
    duplicate it exists to prevent.

    Whichever order this and the indexing subscriber run in, the group's own
    record is the one path that must not count as a collision: it is either
    already written at the new path, or not yet written anywhere.

    :param group: The group that has just arrived at a path.
    :param event: The move event; adding and renaming are both one.
    :raises DuplicateGroupId: When another group already uses this id.
    """
    if event.newParent is None:
        # On its way out of the site. Nothing arrives at an id here.
        return
    catalog = query_catalog()
    if catalog is None:
        return
    group_id = group.getId()
    own_path = "/".join(group.getPhysicalPath())
    for brain in catalog.unrestrictedSearchResults(
        portal_type=GROUP_PORTAL_TYPE, group_id=group_id
    ):
        # Its own record, whether or not the indexing subscriber has run yet:
        # both orderings are legal and neither is worth depending on.
        if brain.getPath() == own_path:
            continue
        raise DuplicateGroupId(
            f"The group id {group_id!r} is already used by the group at "
            f"{brain.getPath()}. Group ids are what roles and memberships are "
            f"stored in terms of, so they are unique across the site rather "
            f"than within a folder."
        )


__all__ = [
    "DuplicateGroupId",
    "on_authenticated",
    "on_claims_refreshed",
    "on_email_identity_changed",
    "on_identity_linked",
    "on_logged_in",
    "on_profile_modified",
    "refuse_duplicate_group",
]
