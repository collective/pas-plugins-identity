# Security

## Reporting a vulnerability

Please report security issues privately rather than in the public issue
tracker.

<!-- TODO: replace with the project's real reporting address before the
     first public release. -->

Contact: `security@example.org`

We will acknowledge a report within a few working days and keep you informed
while we work on it.

## What this package guarantees

These are the properties the test suite enforces. Each has at least one test
that fails if it stops holding.

**Every flow carries state, PKCE and a nonce**, and a callback is bound to the
session that started it. A linking flow additionally requires an authenticated
session at initiation *and* completion by the same session — holding the code,
the state and the flow cookie is not enough to attach an identity to somebody
else's account.

**Auto-link-by-email is off by default.** When enabled, it matches only
addresses this site itself verified by sending a link to them, and only on a
literal `True`. A forged unverified email claim cannot link.

**A link collision is a hard error.** An external identity already linked to
one user id is never attached to another. There is no merge, and adding one is
out of scope.

**Unlinking your last way in is refused** unless you have a verified email
identity or a real password.

**Magic-link tokens are single-use**, expire in at most fifteen minutes, and
are burned server-side. The send endpoint is rate limited per address *and*
per IP, and answers identically for known and unknown addresses.

**Post-login redirect targets are validated** against the portal, on both the
backend and the frontend — a target that never reaches the backend cannot be
checked by it.

**Secrets are write-only everywhere**, including GenericSetup export, and the
audit log never records credentials or tokens.

## Things to know before deploying

**The user id is permanent and opaque.** It is a random UUID minted once, never
derived from an email address or a username, because both change. Nothing in
this package rewrites it.

**Provider avatars are off by default** and should stay off unless you have
read why. See {doc}`profiles`.

**Enabling IP and user-agent recording in the audit log** stores personal data.
See {doc}`audit-log`.

**The audit log is not a session ledger.** It records authentication events,
not sessions.
