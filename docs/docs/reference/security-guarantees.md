---
myst:
  html_meta:
    "description": "The security properties the pas.plugins.identity test suite enforces, and what to know before deploying."
    "property=og:description": "The security properties the pas.plugins.identity test suite enforces, and what to know before deploying."
    "property=og:title": "Security guarantees"
---

(reference-security-guarantees)=

# Security guarantees

Each property below has at least one test that fails if it stops holding.

```{seealso}
To report a vulnerability, follow [SECURITY.md](https://github.com/collective/pas-plugins-identity/blob/main/SECURITY.md).
Please do not use the public issue tracker.
```

## What the package guarantees

### Authentication flows

| Property | Detail |
|---|---|
| Every flow carries `state`, PKCE and a `nonce` | A callback is bound to the session that started it. |
| A linking flow needs an authenticated session | At initiation **and** at completion, and by the same session. Holding the code, the state and the flow cookie is not enough to attach an identity to somebody else's account. |
| A link collision is a hard error | An external identity already linked to one userid is never attached to another. There is no merge, and adding one is out of scope. |
| Unlinking your last way in is refused | Unless you have a verified email identity or a real password. |
| Post-login redirect targets are validated | Against the portal, on the backend **and** the frontend. A target that never reaches the backend cannot be checked by it. |

### Email verification and linking

| Property | Detail |
|---|---|
| Automatic linking needs two switches, both off by default | It matches only an address this site holds as verified, and only when the provider now asserting it is one the operator marked as trusting. |
| Only a literal `True` counts | A forged unverified email claim cannot link. |
| A provider's `email_verified` counts only where an operator said it does | Off unless a driver knows the provider really checks. `google` and `github` ship with it on; everything else off. |
| There is one notion of verified | A trusted provider's verified addresses are recorded exactly as a magic link records one. No second flag to drift. |
| A magic link only goes to an address already on your profile | The proof is proof of control over whatever address it was sent to, so a free-text box would verify any mailbox somebody can reach. A caller with no profile is not held to this: there is no list to name an address on. |
| Magic-link tokens | Single use, burned server side, at most fifteen minutes. The send endpoint is rate limited per address **and** per IP, and answers identically for known and unknown addresses. |

### The authorization server

| Property | Detail |
|---|---|
| Redirect URIs are matched exactly | Unless the operator registered a wildcard. See below. |
| The scheme and the port are never widened | A wildcard registration cannot be downgraded to plain HTTP. |
| Client secrets are hashed with scrypt | Parameters are stored in each hash, so a hash written before a parameter change keeps verifying. |
| A malformed stored secret verifies as false | Never an exception. This runs on the token endpoint, where a raised error would be a distinguishable answer. |
| A public client has no secret | Presenting any is wrong. |
| Grants are validated at registration | Not at the token endpoint, where an unknown grant reads as a client bug rather than a registration mistake. |

#### What a redirect URI must satisfy to be registered

<!-- source: backend/src/pas/plugins/identity/server/controlpanel/interfaces.py -->

| Rule | Refused because |
|---|---|
| Absolute, with a scheme and a host | Matching is exact string comparison, and a relative value can never match what a client sends. |
| No fragment | The Security BCP requires refusing one: the authorization response appends its own, and a registered fragment silently changes what the browser receives. |
| A safe scheme | `https`, a private-use reverse-domain scheme for a native app, or `http` on loopback. Never `javascript:` or `data:`. |
| A `*` only where one is allowed | See the next table. |

#### What a wildcard covers

| Pattern | Stands for | Does **not** cover |
|---|---|---|
| `https://*.example.org/callback` | Exactly one further label: `app.example.org` | `a.b.example.org`, or the bare `example.org`. Each needs its own entry. |
| `https://example.org/*` | Any path on that host, and any query string with it | A different host or port. |

A `*` is refused anywhere else: in a port, a user name, a query string, in the
middle of a label such as `https://a*.example.org`, in the middle of a path, or
directly under a public suffix such as `https://*.com`.

```{warning}
Registering a wildcard is a real widening and should be a deliberate one. Every
name it covers is somewhere this server will send a browser carrying an
authorization code. A subdomain that is taken over, forgotten, or serving
somebody else's content is a valid redirect target for as long as the
registration stands.
```

### Storage and exposure

| Property | Detail |
|---|---|
| Secrets are write-only everywhere | Including GenericSetup export. The audit log never records credentials or tokens. |
| This package's vocabularies require a permission | `plone.restapi` serves a vocabulary anonymously unless it is named in `plone.app.content.browser.vocabulary.PERMISSIONS`, and `pas.plugins.identity.Groups` lists every group on the site. Both vocabularies are registered at `Modify portal content`. |
| A provider icon is sanitized **as it is stored** | An icon is an SVG rendered inline so it can take the button's colour, which makes it markup: it can carry a script, a stylesheet, and references to other documents. Only shapes and attributes on a fixed list survive; an element off the list is dropped with everything inside it rather than unwrapped; no attribute value may reference an address elsewhere; the result is serialized from the parsed tree rather than sliced out of the input. A document that is not an SVG is refused. |

Sanitizing on save rather than on render is what keeps the registry, a
GenericSetup export, and anything else reading the record from holding the
dangerous version.

### Enforced in CI

| Rule | Enforced by |
|---|---|
| Core never imports from `[server]` | `import-linter`. See {doc}`/concepts/layers`. |
| Protocol messages are never constructed by hand | A grep-level rule failing the build if authorization URLs, token requests, or JWT parsing appear outside the flow modules, which delegate to authlib. |

## Things to know before deploying

| | |
|---|---|
| **The userid is permanent and opaque** | A random UUID minted once, never derived from an email address or a username, because both change. Nothing in this package rewrites it. |
| **Provider avatars are off by default** | Keep them off unless you have read why. See {doc}`/concepts/profiles-and-groups`. |
| **IP and user-agent recording stores personal data** | Off by default. See {doc}`audit-log`. |
| **The audit log is not a session ledger** | It records authentication events, not sessions. |
| **Deleting a user keeps their identities and audit entries** | Each keeps personal data against a userid that no longer resolves: a claims snapshot on the identity, a login history on the audit entries. Unlink the identities **before** deleting the user if you have an erasure obligation. See {doc}`user-content`. |
| **A client granted `profile` receives the group list** | `groups` rides on `profile` rather than a scope of its own. `AuthenticatedUsers` is never released, and a user in no other group gets no claim at all. See {doc}`claims`. |
| **A group inside a group grants through it** | At any depth, so a nesting is a grant and reviewing one group's access means reviewing what feeds into it. An inactive group grants nothing and passes nothing through. A cycle terminates rather than raising; it means both groups grant each other. |
| **A membership list is personal data about other people** | `@group-members` needs `Manage users` or membership of the group; `@user-account` needs `Manage users` except for a caller asking about themselves. |
| **A provider's groups grant nothing until you map them** | A group map starts empty, an unmapped provider group grants nothing and is never created locally, and a row pointing at a group this site does not have is skipped and logged. Every sign-in reconciles, and takes back only what that same provider granted. See {doc}`/how-to-guides/map-provider-groups`. |
| **Access tokens cannot be recalled** | They are self-encoded and there is no denylist, so a revoked client's tokens die when they expire—at most the configured access-token TTL. See {doc}`/how-to-guides/enable-back-channel-logout`. |

## Related

- {doc}`/concepts/threat-model`—what this package does and does not defend against
- {doc}`permissions`—who holds what
- {doc}`stability`—which of these are contracts
- {doc}`/concepts/secrets`—where secrets live and where they do not
