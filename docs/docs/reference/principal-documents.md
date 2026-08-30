---
myst:
  html_meta:
    "description": "The JSON format pas.plugins.identity exports users, groups and identities as, and reads them back from."
    "property=og:description": "The JSON format pas.plugins.identity exports users, groups and identities as, and reads them back from."
    "property=og:title": "Principal documents"
    "keywords": "Plone, pas.plugins.identity, export, import, JSON, migration"
---

(reference-principal-documents)=

# Principal documents

A principal document is a single JSON file holding a site's users, groups and identity join.
`pas.plugins.identity.exportimport` writes one and reads one back.

For the commands that produce and consume it, see {doc}`/how-to-guides/export-and-import-principals`.

## The document

```json
{
  "version": 1,
  "generator": "pas.plugins.identity",
  "created": "2026-08-30T18:04:11+00:00",
  "site": "plone",
  "groups": [
    {
      "group_id": "site-editors",
      "title": "Site Editors",
      "description": "",
      "group_ids": ["staff"]
    }
  ],
  "users": [
    {
      "userid": "8f2c1e5b9a7d4c6e8f0a1b2c3d4e5f60",
      "login": "ericof",
      "fullname": "Érico Andrei",
      "emails": ["erico@plone.org"],
      "home_page": "",
      "description": "",
      "location": "Berlin",
      "group_ids": ["site-editors"],
      "identities": [
        {
          "provider": "github",
          "subject": "1234567",
          "created": "2026-01-04T09:12:00+00:00",
          "last_login": "2026-08-30T07:55:03+00:00",
          "groups": ["site-editors"],
          "claims": {"fullname": "Érico Andrei", "email": "erico@plone.org"}
        }
      ]
    }
  ]
}
```

`version`
:   The format version, an integer.
    A document from a later version than the reader understands is refused rather than read optimistically, because guessing at a newer format leaves a site with half its accounts.

`userid`
:   Required, and carried across verbatim.
    Every local role, ownership and sharing entry in the target site is written against it, so an import that minted new ids would produce a site full of content belonging to nobody.

`group_ids`
:   On a user, the groups they are in.
    On a group, the groups that group is nested inside.

`identities`
:   The `(provider, subject)` pairs that reach this account.
    `provider` and `subject` are both required; either alone identifies nobody.
    `created` and `last_login` may be `null`.

## What a document never contains

Passwords
:   There is no password field, in either direction.
    A hash kept by the password behavior stays in the site that holds it.
    A document is a file that gets copied to a laptop, attached to a ticket, and left in a bucket, and the one thing it must never be is a way in.

Provider configuration
:   Client ids and client secrets are not in the format at all, which is a stronger guarantee than masking them.
    Configure the providers in the target site before anybody signs in.

Audit entries
:   The login history is the most sensitive thing this package stores and, on a site that opted in, includes IP addresses.
    Read it where it lives, under a permission; see {doc}`audit-log`.

## Reading order matters

The importer makes three passes, and the order is not incidental.

1. **Groups**, because a user's `group_ids` names them.
2. **Users**, each with the fields the Profile schema declares.
3. **Membership, then the identity join**, once every principal exists.
   A group's own `group_ids` can name a group that appears later in the same list, which is why this pass comes last.

## What is refused, and what is skipped

A refusal stops the whole run and writes nothing: a malformed document, a document from a newer version, a user with no `userid`, an identity missing its provider or its subject, or a site with no identity plugin.

A skip drops one record and keeps going, because one bad row must not stop the other nine hundred:

| Skipped | Why |
| --- | --- |
| A user with no address | `emails` is required on a Profile and `email` is derived from it. Inventing one produces an account whose owner cannot be reached and cannot be told why. |
| An identity already linked to somebody else | Two people cannot both be the same identity, and moving it quietly is one of them taking the other's account. |

Every skip is listed in the result, so a large import reports what did not land instead of raising on the first surprise.

Membership naming a group the document does not carry is applied without that group: it is logged, and the group is not created.
A group nobody has stated the members and nesting of is a grant nobody decided on.

(reference-authomatic-dumps)=

## The `pas.plugins.authomatic` dump

A second, smaller format, read with `--from-authomatic`.
It exists so that migrating from that package is the ordinary import rather than a second code path.

```json
{
  "source": "pas.plugins.authomatic",
  "users": [
    {
      "userid": "8f2c1e5b9a7d4c6e8f0a1b2c3d4e5f60",
      "login": "ericof",
      "identities": [
        {"provider": "github", "subject": "1234567"},
        {"provider": "google", "subject": "109876543210"}
      ],
      "properties": {
        "name": "Érico Andrei",
        "email": "erico@plone.org",
        "link": "https://kitconcept.com",
        "location": "Berlin"
      }
    }
  ],
  "groups": [
    {"group_id": "site-editors", "title": "Site Editors", "members": ["8f2c1e5b9a7d4c6e8f0a1b2c3d4e5f60"]}
  ]
}
```

The `provider` in each identity is authomatic's provider *name*, which is the key under which that site configured it in `json_config`.
It becomes this package's provider *id*, and the two must match exactly or no migrated account is ever reached again.
The `subject` is the provider's own user id: for Google that is the `sub` claim, which is what this package's Google driver reads, so the join survives without translation.

`source` must be the string `pas.plugins.authomatic`.
It is checked rather than assumed: the two formats are close enough that reading one as the other half works, which is worse than failing.

`groups` is optional, and is not something `pas.plugins.authomatic` holds, because it keeps no groups at all.
It is in the format because a real migration is moving a site, and membership carried in the same file beats a second one.
Note that membership is on the group here and on the principal in a document; the conversion inverts it.

`properties` keys are mapped onto Profile fields, in both vocabularies.
`fullname` and `name` both answer for the full name, `home_page` and `link` both for the homepage, and `location` and `description` for themselves.
`link` is the one worth naming: it is what an OAuth2 provider calls a homepage, and authomatic's own shipped property maps translate it.
A key with no matching Profile field, such as `picture`, `first_name` or `last_name`, is dropped rather than carried, because an attribute nothing declares is invisible to every form and permission in the site.

### Where the values come from

`pas.plugins.authomatic` keeps two mappings on its plugin object:

`_userid_by_identityinfo`
:   `(provider_name, provider_user_id)` to userid. This is the identity join, and it maps directly onto `identities`.

`_useridentities_by_userid`
:   userid to a `UserIdentities` object, holding one `UserIdentity` per provider and a property sheet derived from each provider's `propertymap`. This is where `properties` comes from.

All four of its user-id factories produce an opaque string already stored against the identity, so preserving `userid` is correct whichever one the old site used.

### Writing the extraction

The dump is produced offline, against the old site, and this package ships no script for it.
The extraction has to run where `pas.plugins.authomatic` is installed, which is not here.
The shape is small enough to state completely:

```python
"""Extract a pas.plugins.authomatic dump.

    SITE_ID=Plone bin/zconsole run instance/etc/zope.conf extract.py > dump.json
"""
import json
import os
import sys

from zope.component.hooks import setSite

SITE_ID = os.environ.get("SITE_ID", "Plone")

site = app.unrestrictedTraverse(SITE_ID, None)
if site is None:
    sys.exit(f"No Plone site at {SITE_ID!r}")
setSite(site)

plugin = site.acl_users.get("authomatic")
if plugin is None:
    sys.exit(f"No authomatic plugin in {SITE_ID}/acl_users")

identities = {}
for (provider, subject), userid in plugin._userid_by_identityinfo.items():
    identities.setdefault(userid, []).append((provider, subject))

users = []
for userid, useridentities in plugin._useridentities_by_userid.items():
    properties = {}
    entries = []
    for provider, subject in identities.get(userid, []):
        raw = dict(useridentities._identities.get(provider) or {})
        raw.pop("credentials", None)      # a token, never a migration input
        nested = raw.pop("data", None) or {}
        entries.append({"provider": provider, "subject": subject})
        for key, value in {**nested, **raw}.items():
            if value and key not in properties and key != "provider_name":
                properties[key] = value
    users.append({
        "userid": userid,
        "identities": entries,
        "properties": properties,
    })

groups = []
source_groups = site.acl_users.get("source_groups")
if source_groups is not None:
    for group_id in source_groups.listGroupIds():
        groups.append({
            "group_id": group_id,
            "title": group_id,
            "members": list(source_groups._group_principal_map.get(group_id, ())),
        })

print(json.dumps(
    {"source": "pas.plugins.authomatic", "users": users, "groups": groups},
    indent=2, ensure_ascii=False,
))
```

Two things in that script are not decoration, and both were found by running it
against a real authomatic store rather than by reading the source.

`setSite(site)` is required
:   `UserIdentities.propertysheet` reads authomatic's configuration out of the
    registry, and the registry is a *local* utility that `queryUtility` finds
    only once the site is the active component site.
    Traversing to `app.Plone` does not make it one.
    Without the call, the script dies on the first user with
    `AttributeError: 'NoneType' object has no attribute 'forInterface'`.
    On a site with no authomatic users it exits `0` and prints an empty,
    perfectly valid dump instead, which is worse.

Read `_identities`, not `propertysheet`
:   The property sheet is *derived*: it is rebuilt by walking the providers
    currently in `json_config` and applying each one's `propertymap`.
    An identity whose provider has since been removed from the
    configuration, or renamed, or never configured on this site, contributes
    nothing to it, silently and without an error.
    The stored `UserIdentity` still holds the name, the address and the rest.
    Reading the sheet would hand you users with no address at all, and every
    one of them is then skipped on import for exactly that reason.

The keys in `properties` are therefore the provider's own (`name`, `link`,
`picture`, `first_name`) rather than Plone's.
The converter understands both vocabularies, because a dump can honestly carry
either.


```{important}
Do not carry `UserIdentities._secret` across.
`pas.plugins.authomatic` gives each user a random secret and treats it as a password.
No human knows it and none could type it, so moving it moves a credential nobody can use into a file that gets copied around.
```

## Alternatives

`pas.plugins.identity.migration`
:   Moves a site **in place**, with both plugins installed in the same instance.
    That is the right tool when there is one site and it is staying put; see {doc}`/how-to-guides/migrate-from-authomatic`.

`plone.exportimport`
:   Moves content.
    It does not know about the identity store, so a site restored with it alone has Profiles that nobody can sign in to.
    The two are complementary: export the content with `plone-exporter` and the principals with `identity-exporter`.
