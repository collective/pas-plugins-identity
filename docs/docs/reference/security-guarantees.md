---
myst:
  html_meta:
    "description": "The security properties the pas.plugins.identity test suite enforces, and what to know before deploying."
    "property=og:description": "The security properties the pas.plugins.identity test suite enforces, and what to know before deploying."
    "property=og:title": "Security guarantees"
---

(reference-security-guarantees)=

# Security guarantees

These are the properties the test suite enforces.
Each has at least one test that fails if the property stops holding.

```{seealso}
To report a vulnerability, follow [SECURITY.md](https://github.com/collective/pas-plugins-identity/blob/main/SECURITY.md).
Please do not use the public issue tracker.
```

## What the package guarantees

**Every flow carries state, PKCE, and a nonce**, and a callback is bound to the session that started it.
A linking flow additionally requires an authenticated session at initiation and completion by the same session.
Holding the code, the state, and the flow cookie is not enough to attach an identity to somebody else's account.

**Automatic linking by email needs two switches, and both are off by default.**
It matches only an address this site holds as verified, and only when the provider now asserting it is one the operator marked as trusting -- so a provider nobody trusts cannot reach an account by asserting an address some other route verified.
Only a literal `True` counts.
A forged unverified email claim cannot link.

**A provider's `email_verified` counts only where an operator said it does.**
{guilabel}`This provider's email verification counts` is off unless a driver knows the provider really checks; Google and GitHub ship with it on, everything else off.
Switched on, that provider's verified addresses are recorded exactly as a magic link records one -- there is one notion of verified and no second flag to drift.

**A link collision is a hard error.**
An external identity already linked to one user id is never attached to another.
There is no merge, and adding one is out of scope.

**Unlinking your last way in is refused**, unless you have a verified email identity or a real password.

**Magic-link tokens are single-use**, expire in at most fifteen minutes, and are burned server-side.
The send endpoint is rate limited per address and per IP, and answers identically for known and unknown addresses.

**Post-login redirect targets are validated** against the portal, on both the backend and the frontend.
A target that never reaches the backend cannot be checked by it.

**This package's vocabularies require a permission.**
`plone.restapi` serves a vocabulary to anonymous callers unless it is named in `plone.app.content.browser.vocabulary.PERMISSIONS`, and `pas.plugins.identity.Groups` lists every group on the site.
Both of this package's vocabularies are registered at `Modify portal content`.

**Secrets are write-only everywhere**, including GenericSetup export.
The audit log never records credentials or tokens.

**A magic link is only ever sent to an address already on your profile.**
The proof it produces is proof of control over whatever address it was sent to, so a free-text box would verify any mailbox somebody can reach -- which is exactly what automatic linking attaches an account to.
A caller with no profile is not held to this, because there is no list to name an address on.

**A provider icon is sanitized as it is stored, not as it is rendered.**
An icon is an SVG document, rendered inside the page so it can take the button's colour, which means it is markup rather than an image: it can carry a script, a stylesheet, and references to other documents.
Only the shapes and attributes on a fixed list survive, an element not on that list is dropped with everything inside it rather than unwrapped, no attribute value may reference an address elsewhere, and the result is serialized from the parsed tree rather than sliced out of the input.
A document that is not an SVG is refused.
Sanitizing on save rather than on render is what keeps the registry, a GenericSetup export, and anything else reading the record from holding the dangerous version.

**The layer boundary is enforced in CI.**
Core never imports from `[server]`.
See {doc}`/concepts/layers`.

**Protocol messages are never constructed by hand.**
A grep-level CI rule fails the build if authorization URLs, token requests, or JWT parsing appear outside the flow modules, which delegate to authlib.

## Things to know before deploying

**The user id is permanent and opaque.**
It is a random UUID minted once, never derived from an email address or a username, because both change.
Nothing in this package rewrites it.

**Provider avatars are off by default**, and should stay off unless you have read why.
See {doc}`/concepts/profiles-and-groups`.

**Enabling IP and user-agent recording in the audit log stores personal data.**
See {doc}`audit-log`.

**The audit log is not a session ledger.**
It records authentication events, not sessions.

**A relying party granted the `profile` scope receives the group list.**
`groups` rides on `profile` rather than on a scope of its own, so a client asking for a display scope also learns which groups a user is in.
`AuthenticatedUsers` is never released, and a user in no other group gets no claim at all.
If your group names are themselves sensitive, do not grant `profile` to a client you would not grant them to.
See {doc}`claims`.

**A group inside a group grants through it.**
Everybody in an inner group is a member of every group it is nested inside, at any depth, so a nesting is a grant and reviewing one group's access means reviewing what feeds into it.
An inactive group grants nothing and passes nothing through.
A cycle terminates rather than raising; it means both groups grant each other.

**A membership list is personal data about other people.**
`@group-members` needs `Manage users` or membership of the group itself, and `@user-account` needs `Manage users` except when a caller asks about their own account.

**A provider's groups grant nothing until you map them.**
A group map starts empty, an unmapped provider group grants nothing and is never created locally, and a row pointing at a group this site does not have is skipped and logged.
Every sign-in reconciles, and it takes back only what that same provider granted, so a group granted by hand or by another provider survives.
See {doc}`/how-to-guides/configure-a-provider`.

**Access tokens cannot be recalled.**
They are self-encoded and there is no denylist, so a revoked client's tokens die when they expire, at most the configured access-token TTL.
See {doc}`/how-to-guides/enable-back-channel-logout`.
