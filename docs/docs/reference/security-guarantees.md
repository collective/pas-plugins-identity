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

**Automatic linking by email is off by default.**
When enabled, it matches only addresses this site itself verified by sending a link to them, and only on a literal `True`.
A forged unverified email claim cannot link.

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

**The layer boundary is enforced in CI.**
Core never imports from `[content]` or `[server]`, and neither optional layer imports the other.
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

**A provider's groups grant nothing until you map them.**
A group map starts empty, an unmapped provider group grants nothing and is never created locally, and a row pointing at a group this site does not have is skipped and logged.
Every sign-in reconciles, and it takes back only what that same provider granted, so a group granted by hand or by another provider survives.
See {doc}`/how-to-guides/configure-a-provider`.

**Access tokens cannot be recalled.**
They are self-encoded and there is no denylist, so a revoked client's tokens die when they expire, at most the configured access-token TTL.
See {doc}`/how-to-guides/enable-back-channel-logout`.
