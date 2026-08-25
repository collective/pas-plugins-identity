---
myst:
  html_meta:
    "description": "Why a provider secret can be echoed back and a client secret cannot, in pas.plugins.identity."
    "property=og:description": "Why a provider secret can be echoed back and a client secret cannot, in pas.plugins.identity."
    "property=og:title": "About secrets"
---

(concepts-secrets)=

# About secrets

The package handles two kinds of secret, and it treats them in opposite ways.
The difference confuses people until they see which side of the conversation the site is standing on.

## When the site is the client

A provider secret is this site's credential at somebody else's service.

The site has to keep sending it, on every token request, forever.
So the site has to keep the plaintext.

Given that, the goal is only to stop the plaintext leaving.
The REST API and the control panel serialize a stored secret as a mask.
GenericSetup export omits it entirely.
The audit log never records it.

The mask is a real value that round-trips.
Saving the form back with the mask unchanged preserves the stored secret, which is what makes editing a provider possible without retyping its credential every time.

That is also the trap.
Blanking the field is not the same instruction as leaving the mask alone.
An empty string means the secret is now empty, and the package does what it was told.

```{warning}
A GenericSetup export of your provider configuration is not enough to rebuild a working site.
The secrets have to travel separately, by whatever means your deployment already uses for secrets.
This is a deliberate trade, and the alternative is an export file that is a credential.
```

## When the site is the server

A client secret is somebody else's credential at this site.

The site never needs to send it anywhere.
It only ever needs to check that an incoming one matches.
So the site does not keep the plaintext at all: it keeps a scrypt hash, exactly as it would for a password.

That single decision produces the behavior people find surprising.

The secret appears in exactly one response, the one that mints it, at registration or at rotation.
There is no endpoint that reads it back, because nothing on the server knows it any more.
If it is lost, you rotate.

## Why not make both work the same way

Because making them the same would mean picking one of two bad options.

Storing client secrets in plaintext, so they could be read back, turns the client registry into a file full of live credentials for other people's applications.
Hashing provider secrets is impossible, because the site has to send them.

The asymmetry is not an inconsistency.
It is the same rule applied twice: keep the plaintext only when you cannot do the job without it.

## What deleting a client actually does

Removing a client's registration, or setting `enabled: false`, stops its tokens working immediately.

Access tokens carry the client id as their audience, and the Bearer plugin looks that id up in the registry on every request.
With no denylist, that lookup is the only revocation this server has.

Which is worth knowing before you delete a client to tidy up.

## Where to go next

-   {doc}`/how-to-guides/configure-a-provider` for the client side.
-   {doc}`/how-to-guides/register-an-oauth-client` for the server side.
