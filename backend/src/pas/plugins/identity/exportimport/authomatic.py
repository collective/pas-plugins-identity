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

*Provider configuration.* Client ids, secrets, property maps and scopes stay
behind. A document is a file that gets copied around and a client secret must
never be in one; the rest is configuration whose meaning differs between the
two packages, and translating it silently would produce a provider that looks
configured and behaves differently. Configure the providers in the target site
first -- the import does not need them, but the first login does.
"""

from pas.plugins.identity.exportimport.schema import DOCUMENT_VERSION
from pas.plugins.identity.exportimport.schema import ExportImportError
from pas.plugins.identity.exportimport.schema import GENERATOR
from pas.plugins.identity.exportimport.schema import USER_FIELDS
from typing import Any


#: What an authomatic dump must say it is. Checked rather than assumed: the
#: two formats are similar enough that feeding one to the other's reader
#: half-works, and a half-worked import of accounts is the failure this
#: package exists to avoid.
SOURCE = "pas.plugins.authomatic"

#: Dump property keys mapped onto Profile fields.
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


def _properties(user: dict[str, Any]) -> dict[str, str]:
    """Map an authomatic property sheet onto Profile fields.

    A key this package has no field for is dropped rather than carried: the
    Profile schema is what a site's forms and permissions are written against,
    and an attribute nothing declares is invisible to all of them.

    :param user: One user from the dump.
    :param returns: Profile field name to value.
    :returns: The fields that resolved.
    """
    source = user.get("properties") or {}
    resolved: dict[str, str] = {}
    for key, field in PROPERTY_MAP.items():
        if field in resolved:
            # An earlier key already answered; ``fullname`` wins over ``name``
            # because it is the one Plone's own property sheet uses.
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


def convert_authomatic(dump: Any) -> dict[str, Any]:
    """Turn an authomatic dump into a document.

    Structural conversion only. Whether a userid collides, whether an identity
    is already linked and whether an address is usable are questions about the
    *target* site, and the importer asks them there -- one record at a time,
    so a single bad row is a skip rather than a refusal.

    :param dump: The parsed JSON dump.
    :returns: A document in this package's format.
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

    converted_users = []
    for user in users:
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
            "emails": _addresses(user),
            **_properties(user),
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
                    "claims": identity.get("claims") or {},
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


__all__ = ["PROPERTY_MAP", "SOURCE", "convert_authomatic"]
