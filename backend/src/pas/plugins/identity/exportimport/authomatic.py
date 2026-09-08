"""A ``pas.plugins.authomatic`` dump, converted into a document.

The old site does not need this package installed, and does not need to be
running when the import happens. Somebody extracts a JSON file from it, that
file comes here, and what comes out is an ordinary document the importer
already knows how to write. Migrating from authomatic is then the same code
path as restoring a backup, which is the point: one importer to get right.

**The input format.** Read off authomatic's own storage, which was checked
against its source rather than remembered. Its plugin keeps two BTrees:
``_userid_by_identityinfo``, mapping ``(provider_name, provider_user_id)`` to
a userid, and ``_useridentities_by_userid``, mapping a userid to a
``UserIdentities`` object holding one ``UserIdentity`` per provider plus a
derived property sheet. A dump is those two, flattened:

.. code-block:: json

   {
     "source": "pas.plugins.authomatic",
     "users": [
       {
         "userid": "8f2c1e5b9a7d4c6e8f0a1b2c3d4e5f60",
         "identities": [
           {"provider": "github", "subject": "1234567"},
           {"provider": "google", "subject": "109...4"}
         ],
         "properties": {
           "fullname": "Érico Andrei",
           "email": "erico@plone.org",
           "location": "Berlin"
         }
       }
     ],
     "groups": [
       {"group_id": "site-editors", "title": "Site Editors", "members": ["8f2c..."]}
     ]
   }

``groups`` is optional and is not something authomatic holds -- it keeps no
groups at all. It is here because a real migration is moving a *site*, and
whoever writes the extraction script will have ``source_groups`` in front of
them; carrying the membership across in the same file beats a second one.

**Userids come across verbatim, in every authomatic mode.** Its four user-id
factories -- provider user id, provider username, username-or-id, and uuid --
all produce an opaque string that is already stored against the identity, so
preserving it is correct without branching on which mode a site used, and
every local role and ownership in the old site keeps pointing at the right
person. This is the same finding
:mod:`pas.plugins.identity.migration.authomatic` rests on.

**What does not come across.**

*Passwords.* authomatic gives each user a random ``_secret`` and treats it as
a password. No human knows it and none could type it, so carrying it over
would move a credential nobody can use. People sign in through their provider
exactly as before.

*Provider configuration.* Client ids, secrets and scopes stay behind. A
document is a file that gets copied around and a client secret must never be
in one, and a scope means different things to the two packages. Configure the
providers in the target site first -- the import does not need them, but the
first login does.

**The target site's property maps are consulted, and they win.** This is the
one piece of provider configuration that is not translated but *read*, because
it is the only thing that says what the dump's keys mean. A dump carries the
provider's own vocabulary, and the provider decides it: GitHub sends both
``blog`` and ``html_url``, and only the site's map says which one is a
homepage. Left to itself this module guessed with :data:`PROPERTY_MAP` and got
it wrong for every site that had configured better -- ``html_url`` reached
``home_page``, so everybody's homepage became their GitHub profile, and a
``bio`` this module has no name for was dropped entirely.

The map is read per user, from the record for the provider *that user actually
signed in with*, and :data:`PROPERTY_MAP` fills only what it leaves unset. A
provider with no record in the target site falls back to it, which is reported
rather than done quietly: it is the case that loses data.

**The dump's properties are carried whole, as well as mapped.** The map moves
the handful of keys this package has a field for; everything else in the dump
goes into the identity's ``raw`` claims, because the import fires
``IdentityLinked`` and a site's profile enrichers run against exactly that.
An enricher exists to reach what the map cannot -- a list field, a key nobody
here has a name for -- and it can only do so if the payload survives the
conversion. Credentials do not: see
:func:`~pas.plugins.identity.core.utils.claims.scrub_payload`.
"""

from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.utils.claims import scrub_payload
from pas.plugins.identity.core.utils.propertymap import apply_property_map
from pas.plugins.identity.exportimport.schema import DOCUMENT_VERSION
from pas.plugins.identity.exportimport.schema import ExportImportError
from pas.plugins.identity.exportimport.schema import GENERATOR
from pas.plugins.identity.exportimport.schema import USER_FIELDS
from typing import Any
from typing import cast


#: What an authomatic dump must say it is. Checked rather than assumed: the
#: two formats are similar enough that feeding one to the other's reader
#: half-works, and a half-worked import of accounts is the failure this
#: package exists to avoid.
SOURCE = "pas.plugins.authomatic"

#: Dump property keys mapped onto Profile fields, when the site's own map has
#: not answered.
#:
#: A **fallback**, applied per field after
#: :func:`site_propertymaps` has had its say. It knows the two vocabularies a
#: dump can honestly carry and nothing about the provider beyond them, which is
#: why it cannot be the only answer -- see the module docstring.
#:
#: Both halves of the vocabulary, because a dump can honestly contain either.
#: A dump built from authomatic's *property sheet* carries Plone field names,
#: because that is what its ``propertymap`` translated them into. A dump built
#: from the stored identity -- which is what the documented extraction does,
#: and for good reason -- carries the provider's own names, because that is
#: what the provider sent.
#:
#: ``link`` is the one that matters: it is what OAuth2 providers call a
#: homepage, and authomatic's own shipped property maps translate it to
#: ``home_page``. A converter that did not know it silently dropped the field.
#: Confirmed against a real authomatic 2.0.0 store on RelStorage, whose Google
#: map was ``{email, link, name, first_name, last_name, picture}``.
#:
#: A key with no Profile field -- ``picture``, ``first_name``, ``last_name`` --
#: is dropped rather than carried, because an attribute nothing declares is
#: invisible to every form and permission in the site.
PROPERTY_MAP = {
    "fullname": "fullname",
    "name": "fullname",
    "location": "location",
    "home_page": "home_page",
    "link": "home_page",
    "description": "description",
}


def _scalar(value: Any) -> str:
    """Render a claim as the text a document field carries.

    :param value: Whatever the map resolved to.
    :returns: The text, or ``""`` for anything that is not a single value.
    """
    if isinstance(value, (list, tuple, set, dict)):
        # A document field is text. The same refusal as the login path makes:
        # a structured claim reaching a text field is a map that means
        # something this format cannot express.
        return ""
    return str(value)


def _properties(
    user: dict[str, Any],
    propertymaps: dict[str, dict[str, str]],
) -> dict[str, str]:
    """Map one user's dump properties onto Profile fields.

    The site's map for the provider the user signed in with is applied first,
    and :data:`PROPERTY_MAP` fills only the fields it left unset. A user with
    two identities gets both maps, in the order the dump lists them, so the
    first provider to answer for a field keeps it.

    A key this package has no field for is dropped rather than carried: the
    Profile schema is what a site's forms and permissions are written against,
    and an attribute nothing declares is invisible to all of them. That covers
    a site map naming ``portrait`` or ``email`` as readily as an unmapped
    ``picture`` -- :data:`~pas.plugins.identity.exportimport.schema.USER_FIELDS`
    is what a document carries, and the address has its own path.

    :param user: One user from the dump.
    :param propertymaps: Provider id to that provider's claim map.
    :returns: Profile field name to value.
    """
    source = user.get("properties") or {}
    resolved: dict[str, str] = {}

    for identity in user.get("identities") or ():
        mapping = propertymaps.get(identity.get("provider") or "")
        if not mapping:
            continue
        # A dump is flat: the extraction merges the provider's own document
        # into the stored identity, so there is no separate raw payload for a
        # dotted path to reach into. ``resolve_claim`` reads it as claims.
        for field, value in apply_property_map(mapping, cast(Claims, source)).items():
            text = _scalar(value)
            if field in USER_FIELDS and field not in resolved and text:
                resolved[field] = text

    for key, field in PROPERTY_MAP.items():
        if field in resolved:
            # An earlier key already answered; ``fullname`` wins over ``name``
            # because it is the one Plone's own property sheet uses, and the
            # site's own map wins over both.
            continue
        value = source.get(key)
        if value:
            resolved[field] = str(value)

    return {name: resolved.get(name, "") for name in USER_FIELDS}


def _addresses(user: dict[str, Any]) -> list[str]:
    """Return the addresses to put on the Profile.

    :param user: One user from the dump.
    :returns: The addresses, in order, deduplicated.
    """
    source = user.get("properties") or {}
    candidates = [source.get("email"), *(user.get("emails") or ())]
    found: list[str] = []
    for address in candidates:
        address = (address or "").strip().lower()
        if address and address not in found:
            found.append(address)
    return found


def _carried(identity: dict[str, Any]) -> dict[str, Any]:
    """Return the claims a dump states for one identity, scrubbed.

    A dump may carry its own snapshot per identity rather than leaving it to
    be built from ``properties``, and that one is preferred: whoever wrote the
    extraction knew the provider. It gets the same treatment on the way in,
    for the same reason :func:`_claims` does -- a snapshot is persisted and
    re-exported, and the extraction script is not ours.

    :param identity: One identity from the dump.
    :returns: The claims, with ``raw`` scrubbed, or an empty mapping when the
        dump states none.
    """
    claims = identity.get("claims")
    if not isinstance(claims, dict) or not claims:
        return {}
    return {**claims, "raw": scrub_payload(claims.get("raw"))}


def _claims(user: dict[str, Any], addresses: list[str]) -> dict[str, Any]:
    """Build the claims snapshot for one user's identities.

    Only the address facts. A claims snapshot is refreshed wholesale at the
    next login, so carrying more of the dump into it buys nothing and invites
    the question of which provider's copy won when a person has two.

    ``email_verified`` is carried because it is the one claim that is not
    merely data: it is the provider *asserting* something, and it is what
    :func:`~pas.plugins.identity.core.verification.record_verified_addresses`
    reads. Whether this site believes the assertion is not decided here --
    that is the target provider's ``trust_email_verification``, applied at
    import time, exactly as it would be at a login. A dump cannot grant
    itself trust.

    ``raw`` carries the dump's own ``properties``. That is the one part of a
    snapshot the next login does *not* make redundant, because the import
    fires ``IdentityLinked`` and its subscriber runs the site's installed
    :class:`~pas.plugins.identity.core.interfaces.IProfileEnricher` utilities
    against these claims. An enricher reads ``raw`` and nothing else: it is
    what a site has instead of the property map, which refuses a structured
    claim on purpose. Left empty, every enricher ran against ``{}`` and wrote
    nothing, so a migrated Profile came out missing exactly the fields an
    enricher was installed to fill, and no error said so.

    It is scrubbed on the way in. A snapshot is stored on the identity record
    and written out again by the exporter, so an extraction script that put a
    whole token response into ``properties`` would otherwise put an access
    token in the ZODB and in every document exported afterwards. See
    :func:`~pas.plugins.identity.core.utils.claims.scrub_payload`.

    :param user: One user from the dump.
    :param addresses: The addresses already resolved for them.
    :returns: Normalized claims, empty when there is no address.
    """
    if not addresses:
        return {}
    source = user.get("properties") or {}
    # Literally ``True`` -- a string "true" and a 1 are both truthy and
    # neither is a provider saying yes. The same rule as everywhere else this
    # package reads the flag.
    verified = source.get("email_verified") is True
    return {
        "email": addresses[0],
        "email_verified": verified,
        "emails": [{"address": address, "verified": verified} for address in addresses],
        "raw": scrub_payload(source),
    }


def site_propertymaps() -> dict[str, dict[str, str]]:
    """Read every configured provider's property map out of the registry.

    Needs an active site, which is why it is not called by
    :func:`convert_authomatic` -- that stays a function over plain data, so it
    can be tested and scripted without a Plone site anywhere near it. A caller
    that has a site reads the maps with this and passes them in.

    A provider with an empty map is left out rather than carried as an empty
    one: the two mean the same thing here, and leaving it out is what makes
    :func:`unmapped_providers` report it.

    :returns: Provider id to that provider's claim map.
    """
    # Imported here rather than at module scope on purpose. The control panel
    # pulls in the registry and half of Plone with it, and this module is
    # otherwise importable with nothing but the standard library -- which is
    # what lets a dump be converted and inspected outside a Zope instance.
    from pas.plugins.identity.core.controlpanel import get_providers

    return {
        provider.provider_id: dict(provider.propertymap)
        for provider in get_providers()
        if provider.propertymap
    }


def unmapped_providers(
    dump: Any,
    propertymaps: dict[str, dict[str, str]],
) -> dict[str, int]:
    """Count the users whose provider the target site has no map for.

    Those users convert on :data:`PROPERTY_MAP` alone, which knows two
    vocabularies and not the provider's. It is the case that silently loses a
    field, so a caller reports it rather than discovering it in the site
    afterwards.

    :param dump: The parsed JSON dump.
    :param propertymaps: Provider id to that provider's claim map.
    :returns: Provider name to the number of users carrying it, worst first.
    """
    counts: dict[str, int] = {}
    for user in (dump.get("users") if isinstance(dump, dict) else None) or ():
        if not isinstance(user, dict):
            continue
        seen = set()
        for identity in user.get("identities") or ():
            if not isinstance(identity, dict):
                continue
            name = identity.get("provider") or ""
            if name and name not in propertymaps and name not in seen:
                seen.add(name)
                counts[name] = counts.get(name, 0) + 1
    return dict(sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])))


def validate_dump(dump: Any) -> list:
    """Check that a dump is one, and return its users.

    Separate from :func:`convert_authomatic` because the conversion needs the
    target site and this does not. A command reads the file, checks it here,
    and only then starts Zope -- so pointing ``--from-authomatic`` at one of
    this package's own documents is answered in a second rather than after a
    site has been opened.

    Structural and top-level only. A bad *row* is the importer's business, one
    record at a time, so that one of them is a skip rather than a refusal.

    :param dump: The parsed JSON dump.
    :returns: The dump's users.
    :raises ExportImportError: When the dump is not one.
    """
    if not isinstance(dump, dict):
        raise ExportImportError("The dump is not a JSON object")
    source = dump.get("source")
    if source != SOURCE:
        raise ExportImportError(
            f"The dump says its source is {source!r}, not {SOURCE!r}. The two "
            f"formats are close enough that reading one as the other "
            f"half-works, so this refuses rather than guesses."
        )
    users = dump.get("users")
    if not isinstance(users, list):
        raise ExportImportError("The dump has no 'users' list")
    return users


def convert_authomatic(
    dump: Any,
    propertymaps: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Turn an authomatic dump into a document.

    Structural conversion only. Whether a userid collides, whether an identity
    is already linked and whether an address is usable are questions about the
    *target* site, and the importer asks them there -- one record at a time,
    so a single bad row is a skip rather than a refusal.

    **Pass the target site's property maps.** Without them a dump is converted
    on this module's guess at what its keys mean, which is right for a dump in
    authomatic's own vocabulary and wrong for one carrying the provider's --
    the shape the documented extraction produces. :func:`site_propertymaps`
    reads them, and needs a site; this does not, so the two are separate.

    :param dump: The parsed JSON dump.
    :param propertymaps: Provider id to that provider's claim map. Omitted,
        every user converts on :data:`PROPERTY_MAP` alone.
    :returns: A document in this package's format.
    :raises ExportImportError: When the dump is not one.
    """
    users = validate_dump(dump)

    # Group membership is carried on the group in an authomatic dump and on
    # the principal in a document, so it is inverted here rather than in the
    # importer, which should only ever see one shape.
    groups = dump.get("groups") or []
    memberships: dict[str, list[str]] = {}
    for group in groups:
        group_id = group.get("group_id")
        if not group_id:
            continue
        for member in group.get("members") or ():
            memberships.setdefault(member, []).append(group_id)

    maps = propertymaps or {}
    converted_users = []
    for user in users:
        addresses = _addresses(user)
        if not isinstance(user, dict):
            raise ExportImportError("A user in the dump is not an object")
        userid = user.get("userid")
        if not userid:
            raise ExportImportError(
                "A user in the dump has no userid. It cannot be invented: "
                "preserving it verbatim is what keeps the old site's local "
                "roles and ownerships pointing at the right person."
            )
        converted_users.append({
            "userid": userid,
            "login": user.get("login") or userid,
            "emails": addresses,
            **_properties(user, maps),
            "group_ids": memberships.get(userid, []),
            "identities": [
                {
                    "provider": identity.get("provider", ""),
                    "subject": identity.get("subject", ""),
                    # authomatic keeps no timestamps on an identity, so these
                    # are absent rather than invented. A record imported this
                    # way reads as never having been used, which is true of
                    # this site.
                    "created": None,
                    "last_login": None,
                    "groups": [],
                    "claims": _carried(identity) or _claims(user, addresses),
                }
                for identity in user.get("identities") or ()
            ],
        })

    return {
        "version": DOCUMENT_VERSION,
        "generator": f"{GENERATOR} (converted from {SOURCE})",
        "created": dump.get("created") or "",
        "site": dump.get("site") or "",
        "groups": [
            {
                "group_id": group["group_id"],
                "title": group.get("title") or "",
                "description": group.get("description") or "",
                "group_ids": list(group.get("group_ids") or ()),
            }
            for group in groups
            if group.get("group_id")
        ],
        "users": converted_users,
    }


__all__ = [
    "PROPERTY_MAP",
    "SOURCE",
    "convert_authomatic",
    "site_propertymaps",
    "unmapped_providers",
    "validate_dump",
]
