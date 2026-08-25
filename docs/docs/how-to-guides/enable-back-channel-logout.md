---
myst:
  html_meta:
    "description": "Register the back-channel logout endpoint and turn on the per-user keyring that makes it work."
    "property=og:description": "Register the back-channel logout endpoint and turn on the per-user keyring that makes it work."
    "property=og:title": "How to enable back-channel logout"
---

(how-to-enable-back-channel-logout)=

# How to enable back-channel logout

This guide shows you how to make a sign-out at the provider end the matching session on this site.

Back-channel logout runs server to server, with no browser involved, which is exactly why it still works after the user has closed the tab.

Two steps are required, and skipping the second leaves you with an endpoint that validates tokens and ends nothing.

## Register the endpoint with the provider

Register this URL with the provider as the client's back-channel logout URI:

```text
https://your-site.example.org/@@backchannel-logout
```

One endpoint serves every configured provider.
The logout token names its issuer, and that is how the package chooses the provider, and therefore the key to verify the signature with.

## Turn on per-user keyrings

A `plone.session` ticket is stateless and signed from a keyring, so there is normally no way to end one person's session without ending everybody's.
`plone.session` has a switch for exactly this case.

1.  Go to `acl_users/session` in the ZMI.
2.  Open the **Manage secrets** tab.
3.  Enable **per user keyring**.

Each user then gets their own signing ring, and a back-channel logout clears and rotates only theirs.

```{warning}
Without `per_user_keyring`, the endpoint still accepts and validates the provider's token, but it cannot end the user's Plone session.
Their existing ticket stays valid until it times out.
The package logs the failure as an error rather than passing over it quietly, and the `sessions_ended` attribute on the `SessionsRevoked` event reports `False`.
```

## Verify it

Sign in through the provider, then sign out at the provider rather than at this site.

The audit log records the logout.
See {doc}`read-the-audit-log`.

## Know what a logout reaches

| Credential | Effect |
| --- | --- |
| Plone session tickets | Ended, with `per_user_keyring` on. |
| Refresh tokens issued by the `[server]` layer | Revoked, across every client. The logout was about the person, not one application. |
| Access tokens issued by the `[server]` layer | Not revoked. They are self-encoded and there is no denylist, so they live out their lifetime, at most the configured access-token TTL of fifteen minutes by default. |

That last row is the cost of the self-encoded design.
The access-token lifetime is also the worst case between a logout and the last token honoring it going quiet.

For what the endpoint refuses and why, see {doc}`/reference/security-guarantees`.
