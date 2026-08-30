"""A document into a site.

The half that can do damage, so it is the half with the refusals.

**Groups first, then users, then nesting.** A user's ``group_ids`` names
groups, so the groups have to exist; a group's own ``group_ids`` can name a
group further down the same list, so nesting is applied only once every group
is in place. Three passes rather than one, and the ordering is the reason.

**A bad record is a skip, not a refusal.** One user whose identity is already
linked to somebody else must not stop the other nine hundred, and an operator
importing a large dump needs the list of what did not land far more than they
need a traceback. :meth:`Result.skipped` is that list. Refusals are reserved
for conditions that make the whole run meaningless -- no plugin, no catalog, a
document from a newer version of this package.

**The provider names are checked before anything is written.** The identity
key is ``(provider, subject)``, and the name half is authomatic's
``json_config`` key on one side and a string an operator typed into a control
panel on the other. A mismatch raises nothing at import time and orphans every
migrated account at the first login, so it is a refusal here rather than a
discovery later. ``allow_unknown_providers`` is for the deliberate order --
import first, configure afterwards -- and for nothing else.

**Idempotent.** Running the same document twice writes the same site: an
existing user is updated rather than duplicated, and an identity already
pointing at the right userid is left alone rather than re-added. A migration
you cannot re-run is a migration nobody dares run, which is the same rule
:mod:`pas.plugins.identity.migration` states.

**A dry run writes nothing at all.** Not "writes and rolls back" -- the write
is never attempted, so a dry run cannot leave a half-applied transaction
behind if something outside this package commits. Read the report first.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.catalog import GROUP_PORTAL_TYPE
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.catalog import query_catalog
from pas.plugins.identity.core.container import get_container
from pas.plugins.identity.core.container import GROUP
from pas.plugins.identity.core.container import PROFILE
from pas.plugins.identity.core.interfaces import IdentityCollision
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from pas.plugins.identity.core.verification import record_verified_addresses
from pas.plugins.identity.exportimport.schema import ExportImportError
from pas.plugins.identity.exportimport.schema import GROUP_FIELDS
from pas.plugins.identity.exportimport.schema import Result
from pas.plugins.identity.exportimport.schema import USER_FIELDS
from pas.plugins.identity.exportimport.schema import validate
from plone import api
from typing import Any


def _plugin():
    """Return the identity plugin, or refuse.

    :returns: The plugin.
    :raises ExportImportError: When the add-on is not installed here.
    """
    plugin = api.portal.get_tool("acl_users").get(PLUGIN_ID)
    if plugin is None:
        raise ExportImportError(
            "This site has no identity plugin, so there is nowhere to import "
            "to. Install pas.plugins.identity here first."
        )
    return plugin


def _existing(portal_type: str, index: str, value: str):
    """Return an existing principal object, or ``None``.

    :param portal_type: ``UserProfile`` or ``UserGroup``.
    :param index: The catalog index to match on.
    :param value: The value to match.
    :returns: The object, or ``None``.
    """
    catalog = query_catalog()
    if catalog is None:
        return None
    brains = catalog.unrestrictedSearchResults(**{
        "portal_type": portal_type,
        index: value,
    })
    return brains[0]._unrestrictedGetObject() if brains else None


def _import_group(group: dict[str, Any], result: Result, dry_run: bool) -> None:
    """Create or update one group, without its nesting.

    :param group: The group record.
    :param result: The result to record into.
    :param dry_run: Whether to write.
    """
    group_id = group["group_id"]
    existing = _existing(GROUP_PORTAL_TYPE, "group_id", group_id)
    fields = {name: group.get(name) or "" for name in GROUP_FIELDS}

    if existing is not None:
        if not dry_run:
            for name, value in fields.items():
                setattr(existing, name, value)
            existing.reindexObject()
        result.groups.append(group_id)
        return

    if dry_run:
        result.groups.append(group_id)
        return

    container = get_container(create=True, kind=GROUP)
    if container is None:  # pragma: no cover - refused upstream
        result.skipped.append(f"group {group_id}: no container to file it in")
        return
    api.content.create(
        container=container,
        type=GROUP_PORTAL_TYPE,
        id=group_id,
        group_id=group_id,
        **fields,
    )
    result.groups.append(group_id)


def _import_user(user: dict[str, Any], result: Result, dry_run: bool) -> None:
    """Create or update one user's Profile, without its identities.

    :param user: The user record.
    :param result: The result to record into.
    :param dry_run: Whether to write.
    """
    userid = user["userid"]
    existing = _existing(PROFILE_PORTAL_TYPE, "userid", userid)
    emails = [address for address in user.get("emails") or () if address]
    if not emails:
        # ``emails`` is required on the Profile and ``email`` is derived from
        # it, so a user with none cannot be created at all. Reported rather
        # than defaulted: inventing an address would produce an account whose
        # owner cannot be reached and cannot be told why.
        result.skipped.append(
            f"user {userid}: no email address, which a profile requires"
        )
        return

    fields = {name: user.get(name) or "" for name in USER_FIELDS}
    login = user.get("login") or userid

    if existing is not None:
        if not dry_run:
            for name, value in fields.items():
                setattr(existing, name, value)
            existing.login = login
            existing.emails = tuple(emails)
            existing.reindexObject()
        result.users.append(userid)
        return

    if dry_run:
        result.users.append(userid)
        return

    container = get_container(create=True, kind=PROFILE)
    if container is None:  # pragma: no cover - refused upstream
        result.skipped.append(f"user {userid}: no container to file it in")
        return
    api.content.create(
        container=container,
        type=PROFILE_PORTAL_TYPE,
        id=userid,
        userid=userid,
        login=login,
        emails=tuple(emails),
        **fields,
    )
    result.users.append(userid)


def _apply_membership(record: dict[str, Any], portal_type: str, dry_run: bool) -> None:
    """Write a principal's group membership, once every group exists.

    ``portal_type`` is passed rather than inferred from the record's keys. A
    document is a file somebody may have written by hand, so "it has a
    ``userid`` key, therefore it is a user" is a guess about untrusted input
    at exactly the point where being wrong writes the membership onto the
    wrong object.

    :param record: The user or group record.
    :param portal_type: Which of the two types this record is.
    :param dry_run: Whether to write.
    """
    wanted = [group_id for group_id in record.get("group_ids") or () if group_id]
    if not wanted or dry_run:
        return
    index = "userid" if portal_type == PROFILE_PORTAL_TYPE else "group_id"
    obj = _existing(portal_type, index, record[index])
    if obj is None:  # pragma: no cover - written a moment ago
        return
    known = [
        group_id
        for group_id in wanted
        if _existing(GROUP_PORTAL_TYPE, "group_id", group_id) is not None
    ]
    missing = sorted(set(wanted) - set(known))
    if missing:
        # Named rather than created. A group this document does not carry is
        # a group whose members and nesting nobody has stated, and inventing
        # one produces a grant nobody decided on.
        logger.warning(
            "%r names groups this site does not have, which were not created: %s",
            record[index],
            ", ".join(missing),
        )
    obj.group_ids = tuple(known)
    obj.reindexObject()


def _import_identities(
    user: dict[str, Any],
    plugin,
    result: Result,
    dry_run: bool,
    trust_verified_emails: bool = False,
) -> None:
    """Write one user's identity join.

    :param user: The user record.
    :param plugin: The identity plugin.
    :param result: The result to record into.
    :param dry_run: Whether to write.
    :param trust_verified_emails: Record an address the source's provider
        called verified as verified here, whatever this site's provider record
        says about trusting that provider at a login.
    """
    userid = user["userid"]
    store = plugin.store
    for identity in user.get("identities") or ():
        provider = identity["provider"]
        subject = identity["subject"]
        owner = store.userid_for(provider, subject)

        if owner == userid:
            # Already ours. This is what makes a second run a no-op.
            continue
        if owner is not None:
            # The one case that must never be resolved by guessing: two
            # people cannot both be the same identity, and quietly moving it
            # is one of them taking the other's account.
            result.skipped.append(
                f"identity {provider}:{subject}: already linked to {owner}, "
                f"not to {userid}"
            )
            continue

        if not dry_run:
            try:
                record = plugin.link(
                    userid, provider, subject, identity.get("claims") or {}
                )
            except (
                IdentityCollision
            ) as error:  # pragma: no cover - the store was read a line above
                result.skipped.append(f"identity {provider}:{subject}: {error}")
                continue
            record.groups = tuple(identity.get("groups") or ())
            # ``plugin.link`` has already fired ``IdentityLinked``, and the
            # subscriber answered it exactly as it answers a login -- applying
            # the claims and asking the provider record whether to believe
            # ``email_verified``. So on a site that trusts this provider,
            # the addresses are recorded already and the call below is a
            # no-op returning nothing.
            #
            # It is here for the site that does *not* trust it at login and
            # still wants the addresses its old site had already collected.
            # That is a different question -- one about history rather than
            # about every future sign-in -- and answering it by switching the
            # login policy on and back off again would leave a window where
            # real logins are judged by the temporary setting.
            if trust_verified_emails:
                for address in record_verified_addresses(
                    userid, provider, identity.get("claims") or {}, trust=True
                ):
                    result.identities.append((EMAIL_PROVIDER, address, userid))
        result.identities.append((provider, subject, userid))


def _check_providers(document: dict[str, Any]) -> str:
    """Refuse when the site has no provider for a name the document uses.

    The identity key is ``(provider, subject)``. The subject is the
    provider's own and survives a migration untouched; the *name* does not,
    because it is authomatic's ``json_config`` key on one side and a string
    an operator types into a control panel on the other. When they differ,
    nothing raises: the import reports success, and then every migrated
    person signs in, matches no identity, and is given a second account
    beside the one waiting for them -- which keeps their name and their
    groups and belongs to nobody who can sign in.

    So it is checked here, before anything is written, rather than
    discovered at the first login. Checked against *configured* providers
    rather than enabled ones: an operator may reasonably import before
    switching a provider on, and being switched off does not break the join.

    :param document: The document about to be imported.
    :returns: A refusal message, or the empty string when every name matches.
    """
    from pas.plugins.identity.core.controlpanel import get_providers

    wanted = {
        identity["provider"]
        for user in document.get("users") or []
        for identity in user.get("identities") or []
        if identity.get("provider")
    }
    # ``email`` is not a provider anybody configures. It is the store's own
    # marker for "this site has proved this address belongs to this person",
    # written as an identity so that one BTree answers both questions -- see
    # ``core.utils.emails.verified_addresses``. Requiring it to be configured
    # would refuse every document exported from a site that has ever verified
    # an address, which is most of them.
    wanted.discard(EMAIL_PROVIDER)
    if not wanted:
        return ""

    configured = {provider.provider_id for provider in get_providers()}
    missing = sorted(wanted - configured)
    if not missing:
        return ""

    lines = [
        f"This site has no provider named {', '.join(repr(m) for m in missing)}, "
        f"which {'is' if len(missing) == 1 else 'are'} named by the identities "
        f"in this document."
    ]
    # A near miss is the likely case and the one worth naming, because the
    # two strings look the same in a control panel listing.
    folded = {p.casefold(): p for p in configured}
    near = [(m, folded[m.casefold()]) for m in missing if m.casefold() in folded]
    if near:
        lines.append(
            "Configured but spelled differently: "
            + ", ".join(f"{found!r} for {want!r}" for want, found in near)
            + "."
        )
    lines.append(
        f"Configured here: "
        f"{', '.join(repr(p) for p in sorted(configured)) or '(none)'}."
    )
    lines.append(
        "The provider id is half of every identity key, so importing against "
        "the wrong one gives every migrated person a second account at their "
        "first login and leaves the migrated one unreachable. Configure a "
        "provider under the name the document uses, or pass "
        "--allow-unknown-providers to import now and configure it afterwards."
    )
    return " ".join(lines)


def _preflight(document: Any, allow_unknown_providers: bool) -> tuple:
    """Check everything that makes a run meaningless, before writing.

    Every condition here is one where continuing would produce a site nobody
    asked for: a document that is not one, a site that cannot hold principals,
    or providers that no login will ever match.

    :param document: The document offered.
    :param allow_unknown_providers: Skip the provider-name check.
    :returns: ``(document, plugin)`` once both are known good.
    :raises ExportImportError: On the first condition that fails.
    """
    document = validate(document)
    plugin = _plugin()
    if query_catalog() is None:
        raise ExportImportError(
            "This site has no identity catalog, so imported principals "
            "would be invisible to enumeration."
        )
    if not allow_unknown_providers:
        complaint = _check_providers(document)
        if complaint:
            raise ExportImportError(complaint)
    return document, plugin


def import_site(
    document: Any,
    dry_run: bool = False,
    allow_unknown_providers: bool = False,
    trust_verified_emails: bool = False,
) -> Result:
    """Write a document's principals into this site.

    :param document: The parsed JSON document.
    :param dry_run: Report what would happen and write nothing.
    :param allow_unknown_providers: Import even when the site has no provider
        for a name the document uses. For the deliberate order -- import
        first, configure the providers afterwards -- and for nothing else.
    :param trust_verified_emails: Accept the addresses the source's provider
        called verified, whatever this site's provider record says about
        trusting that provider at a login. A decision about the history being
        imported rather than about future sign-ins, which is why it is asked
        here and not read from ``trust_email_verification``.
    :returns: What was done, or would be.
    :raises ExportImportError: When the document is not one, or when this site
        cannot receive it.
    """
    result = Result(dry_run=dry_run)
    try:
        document, plugin = _preflight(document, allow_unknown_providers)
    except ExportImportError as error:
        result.refusals.append(str(error))
        return result

    groups = document.get("groups") or []
    users = document.get("users") or []

    # Elevated throughout: filing a principal needs an add permission that no
    # ordinary member holds, and this runs from a console script whose
    # security context is whatever the caller set up.
    with api.env.adopt_roles(["Manager"]):
        for group in groups:
            _import_group(group, result, dry_run)
        for user in users:
            _import_user(user, result, dry_run)
        # Nesting last, so a group may name one that came after it.
        for group in groups:
            _apply_membership(group, GROUP_PORTAL_TYPE, dry_run)
        for user in users:
            if user["userid"] in result.users:
                _apply_membership(user, PROFILE_PORTAL_TYPE, dry_run)
        for user in users:
            if user["userid"] in result.users:
                _import_identities(user, plugin, result, dry_run, trust_verified_emails)

    logger.info(
        "Imported %d users, %d groups and %d identities%s",
        len(result.users),
        len(result.groups),
        len(result.identities),
        " (dry run)" if dry_run else "",
    )
    return result


__all__ = ["import_site"]
