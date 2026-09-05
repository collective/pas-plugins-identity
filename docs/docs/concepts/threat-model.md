---
myst:
  html_meta:
    "description": "What pas.plugins.identity trusts, what it never trusts, and which configurations reopen a hole."
    "property=og:description": "What pas.plugins.identity trusts, what it never trusts, and which configurations reopen a hole."
    "property=og:title": "Threat model"
---

(concepts-threat-model)=

# Threat model

What this package trusts, what it refuses to trust, and which settings hand back
a protection it gives you.

{doc}`/reference/security-guarantees` lists the properties the test suite
enforces. This page is the reasoning: what each one is for, and how a
configuration can undo it.

## Trust boundaries

### What the site trusts from a provider

**The subject, and nothing else by default.**

A provider proves that the person at the browser controls an account at that
provider. The `sub` claim identifies which account. That is the whole of what
arrives trusted.

### What it never trusts

**Group names.** A group claim is whatever the far end's directory happens to be
called. Groups grant permissions here, so minting local groups from a claim would
let anyone who can name a group at the provider create one here. An unmapped
group grants nothing and is never created.

**An unverified email address.** An address is matched on only when this site
holds it as verified—proved by a magic link from here, or vouched for by a
provider an operator explicitly marked as trusting.

**A non-boolean `email_verified`.** Only a literal `True` counts. Several
providers send the string `"true"` and several send `1`; a truthy-looking value
that is not `True` is refused, because a forged unverified address that reads as
truthy is an account takeover.

**An absent claim.** Absent is not `true`. A provider that sends no
`email_verified` at all—Microsoft Entra ID, for example—produces no verified
addresses here, whatever the trust switch says.

## Scenarios

### Account takeover through a weak provider

**Attack.** Somebody registers at a provider with an address belonging to one of
your users, and signs in here. Automatic linking attaches them to that user's
account.

**What prevents it.** Linking needs two switches, both off by default, and the
address must be one this site holds as verified. A provider nobody marked as
trusting cannot make an address verified here.

**What reopens it.** Turning on
{guilabel}`This provider's email verification counts` for a provider that does
not actually check. This is the single most consequential setting in the package.
See {doc}`email-verification`.

### Account enumeration through magic-link send

**Attack.** Post addresses to the send endpoint and read the responses to learn
which have accounts here.

**What prevents it.** The endpoint answers identically for known and unknown
addresses, and is rate limited per address **and** per IP.

**What reopens it.** Raising the rate limit far enough to make bulk probing
practical. The identical-response property itself is not configurable.

### Verifying a mailbox the person does not own

**Attack.** Ask for a magic link to an arbitrary address, prove control of it,
and thereby verify an address that then satisfies automatic linking.

**What prevents it.** A magic link is only ever sent to an address already on the
caller's profile. A caller with no profile is not held to this, because there is
no list to name an address on.

**What reopens it.** Nothing in configuration. This one is structural.

### Replay of a sign-in

**Attack.** Capture a callback and replay it.

**What prevents it.** Every flow carries state, PKCE and a nonce, and a callback
is bound to the session that started it. Magic-link tokens are single-use, burned
server-side, and expire in at most fifteen minutes whatever is configured.

**What reopens it.** Nothing in configuration.

### Attaching an identity to somebody else's account

**Attack.** Start a linking flow, and complete it against a different session.

**What prevents it.** A linking flow requires an authenticated session at
initiation **and** completion by the same session. Holding the code, the state
and the flow cookie is not enough.

**What reopens it.** Nothing in configuration.

### Group minting from provider claims

**Attack.** Create a group at the provider named after a privileged Plone group,
and have it granted here.

**What prevents it.** No group is ever created from a claim. A provider group
grants only what the group map says, and a row pointing at a group this site does
not have is skipped and logged.

**What reopens it.** Mapping a provider group to a privileged local group. That
is a deliberate act, and it means whoever administers the provider's directory
can grant that Plone group.

### Group grants that outlive the grant

**Attack.** Keep a permission after being removed from the group that granted it.

**What prevents it.** Every login reconciles, and a login takes back what that
same provider granted.

**What reopens it.** Switching off
{guilabel}`Let this provider set group membership`, which freezes existing
grants. Also note that *clearing* a map does not strip what it granted: a
provider with an empty map touches no membership at all. To revoke, empty the
map's values and let one login reconcile.

### A stolen authorization code redirected elsewhere

**Attack.** Register or take over a host that a client's redirect URI covers, and
receive authorization codes there.

**What prevents it.** Redirect URIs are matched exactly. A registration without a
`*` is compared as a string: no prefix matching, no ignoring the query string, no
treating a trailing slash as equivalent.

**What reopens it.** Registering a wildcard. `https://*.example.org/callback`
covers every single-label subdomain, and each is somewhere this server will send
a browser carrying a code. A subdomain that is taken over, forgotten, or serving
somebody else's content is a valid target for as long as the registration stands.

Wildcards are refused in a port, a user name, a query string, mid-label, mid-path,
and directly under a public suffix. The scheme and port are never widened.

### Secret leakage through configuration export

**Attack.** Read a GenericSetup export, or the control panel, to recover a client
secret.

**What prevents it.** Secrets are write-only everywhere, including export. The
control panel serializes a stored secret as a mask. The audit log never records
credentials or tokens.

**What reopens it.** Nothing in configuration—but note the consequence: an
export is **not** a backup of a working site. Secrets travel separately. See
{doc}`secrets`.

### Script injection through a provider icon

**Attack.** Paste an SVG carrying a script as a provider's icon.

**What prevents it.** The icon is sanitized **on save**, not on render, so the
registry and any export hold only the safe version. Only listed shapes and
attributes survive, an unlisted element is dropped with its contents rather than
unwrapped, no attribute may reference an address elsewhere, and the result is
serialized from the parsed tree rather than sliced out of the input. A document
that is not an SVG is refused.

**What reopens it.** Nothing in configuration.

### Lockout of the last sign-in method

**Attack.** Not an attack—a foot-gun. Unlink your only way in.

**What prevents it.** Unlinking the last method is refused unless there is a
verified email identity or a real password.

**What reopens it.** Nothing in configuration.

### Vocabularies read anonymously

**Attack.** Read the site's group list without an account.

**What prevents it.** `plone.restapi` serves vocabularies to anonymous callers
unless they are named in its `PERMISSIONS` map. Both of this package's
vocabularies are registered at `Modify portal content`.

**What reopens it.** Registering a third-party vocabulary without naming it
there. A driver add-on that ships a vocabulary should check.

## Explicitly out of scope

**Merging accounts.** A link collision is a hard error, and there is no merge.
Combining two people's data is not a decision this software makes.

**Session tracking.** The audit log is an authentication event log, not a session
ledger.

**`sid`-only back-channel logout.** A logout token carrying only a `sid` and no
`sub` cannot be resolved to a session this site knows about.

**Classic UI sign-in.** Not supported yet, so it has no threat surface here. See
{doc}`/reference/stability`.

## Where to go next

- {doc}`/reference/security-guarantees`—the same properties, as a checklist the tests enforce
- {doc}`email-verification`—the trust decision that matters most
- {doc}`secrets`—why secrets behave differently in each direction
- {doc}`/how-to-guides/troubleshoot`—when a protection is doing its job and looks like a bug
