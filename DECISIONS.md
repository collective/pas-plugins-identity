# Decisions

Decisions taken while building this package, with the reason. A decision here
is one that a later reader might otherwise reopen, get wrong, or "clean up".
Mechanics live in commit messages; this is for the *why*.

The plan (`.claude/PLAN.local.md`) carries the decisions taken before any code
was written. This file carries the ones taken since.

---

## Core

**The user id is a random UUID, minted once.** Never derived from an email
address, a username, or a hash of the first identity. All of those change, and
a hash leaks which provider somebody signed up with.

**Extraction and authentication run at callback time only.** An ordinary
request rides the `plone.session` ticket or the `jwt_auth` token the plugin
issued. The PAS plugin never does per-request network I/O.

**The flow session is a signed cookie of our own.** There is no
`session_data_manager` in Plone 6.2 — verified, `api.portal.get_tool` raises in
a stock site — so the storage had to be ours. Signed with a key derived from
the `plone.keyring` `_system` ring and verified against every key in it, so
rotating the ring does not strand an in-flight login. `SameSite=Lax`, because
`Strict` would withhold the cookie on the provider's redirect back.

**A link collision is an error, not a merge.** An identity already linked to
one user id is never attached to another. Merge tooling is out of scope, and
"helpfully" merging accounts is how one compromised provider account becomes
two.

**Deleting a provider leaves its identities alone.** A configuration change is
not an instruction to lock people out.

**A masked secret is rendered into the control-panel field, not blanked.**
Saving it back unchanged is what preserves the stored secret. Blanking would
send an empty string, which is a different instruction.

---

## `[profile]` extra

**The dedicated catalog subclasses Plone's `CatalogTool`** (Érico,
2026-08-21) rather than being a bare `ZCatalog`, so the standard indexing
machinery applies unchanged. That inheritance brings two behaviours that are
wrong here and are overridden: `searchResults` filters by
`allowedRolesAndUsers`, and the indexing methods route through CMFCore's
*global* queue whose only processor is `portal_catalog` — through the queue an
object bound for this catalog lands in the site catalog instead, silently.

**Where Profiles live is configuration** (Érico, 2026-08-21): parent, id,
title and content type are four registry records. The catalog is deliberately
*not* scoped to that container, so reorganising content is not a
deauthentication.

**Profiles and Groups share one catalog**, distinguished by a `portal_type`
index, rather than having one catalog each. Groups are few, and a second
catalog would double the install, uninstall, rebuild and consistency-check
machinery.

**`global_allow` is true, with a restrictive add permission.** The other way
round, a Profile cannot be pasted into an ordinary folder at all, which makes
reorganising content silently impossible for the administrator allowed to do
everything else.

**The self-role is `Editor`, computed by a local-role provider.** Not
`Owner`, which carries "may delete" — a user deleting their own Profile leaves
an account whose properties and enumeration stop working while the login keeps
succeeding. Computed rather than assigned, so there is nothing to keep in step
with `userid` and nothing to migrate.

**D2 is one comparison.** The Profile remembers what the provider last wrote,
and the provider may write a field only while the current value still equals
that. This replaces a flag per field, and it gets right the two cases a flag
design usually gets wrong: clearing a field is an edit, and an administrator
who typed a value owns it.

**The login name is never synced from claims.** It is half of the case-folded
index user enumeration queries; a provider renaming somebody should not
silently move their account.

**Group membership lives on the Profile.** `getGroupsForPrincipal` runs on
every permission check touching a local role; `getGroupMembers` runs when
somebody opens a listing. Membership on the member makes the hot question one
metadata read.

**Provider avatars are off by default**, which D5 did not ask for. D5
anticipated portrait storage fighting back; it did not. The exposure is
different: `picture_url` is a claim, and at many providers a claim is whatever
the user typed, so a server-side fetch on the login path makes the backend a
request forger with the response readable off the user's own portrait. No
guard list makes fetching a user-supplied URL safe, so there is a switch.

---

## Withdrawn

**C9 — that `Products.membrane`'s user-properties plugin wakes content
objects.** Written into a module docstring from memory during Gate 6b and
never measured; membrane is not a dependency here, so no test could have
caught it. The claim is withdrawn from the code and is not made in the
documentation. C9 remains open in the plan. What is claimed instead is only
what is tested: that *this* package answers those questions without waking a
content object.

---

## Gate 7 spike (2026-08-21)

The plan requires reading the source of both packages rather than working from
memory. Both were read at the versions checked out locally.

### C5 — walking authomatic's identity records: **VERIFIED**

`pas.plugins.authomatic`'s plugin keeps two BTrees:

- `_userid_by_identityinfo`: `(provider_name, provider_userid) -> userid`
- `_useridentities_by_userid`: `userid -> UserIdentities`

The first is exactly the mapping this package stores. A migration does not
have to reconstruct anything: it reads that BTree directly. `UserIdentities`
additionally carries a per-user `_secret` (used as a password) and a
`PersistentMapping` of `provider_name -> UserIdentity`, each holding the
provider's user dict.

The four user-id factories (`provider user id`, `provider username`,
`username or id`, `uuid`) all produce opaque strings that are already stored,
so a migration preserving the user id verbatim is correct in every mode. The
"both userid modes" check is therefore about the fixture covering them, not
about the migration branching on them.

### D8 — oidc's user-id derivation: **VERIFIED, with a caveat**

`pas.plugins.oidc` derives the user id as:

```python
user_id = userinfo[self.getProperty("user_property_as_userid") or "sub"]
```

It stores **no identity mapping at all**. It creates a `source_users` account
whose id is that claim value, and that is the whole record.

The consequence matters. When the setting is the default `sub`, the Plone user
id *is* the subject, so `(provider, subject) -> userid` can be reconstructed
exactly. When a site changed it — to `email`, say — the `sub` was never stored
anywhere, and a migration cannot recover it. For those sites the only correct
join is to keep using the same claim as the subject, which means this package
needs a **per-provider subject claim** setting rather than the per-driver
`subject_keys` it has today.

### C8 — an authomatic-compatible callback route: **feasible, not free**

authomatic's callback is a server-rendered browser view at
`<portal_url>/authomatic-handler/<provider>`, which both starts and finishes
the flow. This package uses a frontend route that reads `code` and `state` off
the query string and POSTs them to `@identity-callback`.

Serving the old URL is possible: a compatibility view under the same name that
starts our flow on the way out and completes it on the way back, then redirects
to the frontend with a token. It is not free — it is a second entry point into
the flow with its own redirect handling, its own open-redirect surface (S6) and
its own session binding (S1), duplicating the callback service in a different
shape. Whether the zero-touch redirect URI is worth that is a judgement about
the migration audience, not a technical blocker.

**Status: open.** Recorded rather than decided.
