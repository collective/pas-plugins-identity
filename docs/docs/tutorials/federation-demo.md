---
myst:
  html_meta:
    "description": "Run two Plone sites in Docker and sign in to one of them against the other."
    "property=og:description": "Run two Plone sites in Docker and sign in to one of them against the other."
    "property=og:title": "Federate two Plone sites"
---

(tutorial-federation-demo)=

# Federate two Plone sites

In this tutorial you start two complete Plone sites and sign in to one of them using an account that exists only on the other.

By the end you will have seen a full OpenID Connect flow between two Plone sites, a consent screen, a magic-link sign-in, and a federated identity you can unlink.
Along the way you will learn where this package puts each of those things, which is what makes the rest of the documentation readable.

The two sites are:

| Host | Role | Layers |
| --- | --- | --- |
| `http://id.localhost` | The identity provider | `core`, `profile`, and `server` |
| `http://plone.localhost` | The relying party | `core`, with the generic OIDC driver |

You need Docker, and the repository checked out.
Everything else the demo needs, it builds.

## Start the stack

Run this from the repository root:

```shell
make demo-stack-start
```

The first run builds images and takes a few minutes.
When it finishes, both sites are listening.

Open <http://plone.localhost> in a browser.
Notice that the login page offers exactly one way in, and does not wait for you to click it.
That site has no local password form, because the demo builds its frontend with `RAZZLE_IDENTITY_SHOW_PLONE_LOGIN` set to `false`.

## Sign in as somebody who does not exist here

You are redirected to `http://id.localhost`.
Look at the address bar.
You have left the relying party entirely, and you are now on the identity provider's own Volto login page.

Sign in as:

| Field | Value |
| --- | --- |
| Username | `dana` |
| Password | `dana-demo-password` |

A consent screen appears, rendered by the provider's own frontend in the provider's own look.
It names the relying party and lists what that party is asking for.
Approve it.

You land back on `http://plone.localhost`, signed in.

Alice exists only on `id.localhost`.
The account you are now using on `plone.localhost` was created by the sign-in you just completed.

## Watch consent happen only once

Sign out of the relying party, then sign in again.

This time you are redirected straight back with no consent screen.
Consent is recorded once per user and client, and the second visit reuses it.

## Look at the identity you just created

Open <http://plone.localhost/identities>.

Your federated identity is listed there, naming the provider it came from.
You can unlink it from this page.
Do not unlink it yet, because it is currently your only way in to this site.

## Sign in with a magic link

Go back to the provider at <http://id.localhost/login> and choose the magic-link option.
Type any email address.

The stack has no mail server.
`Products.PrintingMailHost` is switched on instead, so the message is written to the log.
Read it there:

```shell
make demo-stack-logs
```

Find the link in the output and open it.
You are signed in to the provider, with no account created in advance and no password anywhere.

## Fetch the contract

The relying party was configured with an issuer URL and a client credential, and nothing else.
Every endpoint it used, and the keys it verified the `id_token` with, came from one document at runtime.

Fetch that document yourself:

```shell
curl -s http://id.localhost/.well-known/openid-configuration | jq
```

Read the `authorization_endpoint`, `token_endpoint`, and `jwks_uri` fields.
Those are the URLs your browser and the relying party's container have been using for the last few minutes.
Nothing about this provider is special-cased in the relying party.

## Look at the client registration

Open <http://id.localhost/controlpanel/identity-clients> and sign in as `admin` with the password `admin`.

The demo client is registered there.
Its secret is not, and cannot be recovered.
A client secret appears exactly once, in the response that mints it.

## Withdraw consent

Open <http://plone.localhost>, and then, on the provider, visit <http://id.localhost/applications>.

The relying party is listed as an application that uses your data.
Withdraw its access.

Now sign in to `plone.localhost` again.
The consent screen is back, because withdrawing consent deleted the record that let the second sign-in skip it.

## Clean up

```shell
make demo-stack-rm
```

That removes the containers and both databases.

## What you built

You ran a real federation.
Two Plone sites, two databases, real cookies between sibling hosts, and a browser that never saw a shortcut.

```{important}
Every credential in this stack is a fixed literal in `backend/demo/src/identitydemo/settings.py`, and therefore public.
The `identitydemo` package is never published to PyPI, is not installed into the production image, and both of its GenericSetup profiles refuse to install unless `IDENTITY_DEMO` is set in the environment.
```

```{seealso}
{doc}`/concepts/federation` explains why the issuer is configured rather than derived, why one URL has to resolve both inside and outside the containers, and how a Volto login becomes a Zope principal.
Read it when something in this stack does not behave.
```
