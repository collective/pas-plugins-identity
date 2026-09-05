---
myst:
  html_meta:
    "description": "The six things pas.plugins.identity deals with, how they relate, and what a sign-in does."
    "property=og:description": "The six things pas.plugins.identity deals with, how they relate, and what a sign-in does."
    "property=og:title": "Mental model"
---

(concepts-mental-model)=

# Mental model

Start here. This page names the things this package deals with, shows what a
sign-in actually does, and points you at the right quadrant for what you came to
do.

## The six nouns

A {term}`driver` knows how to talk to a *kind* of service. GitHub, Google,
anything speaking OpenID Connect. It is code, and it ships with the package or
comes from an add-on.

A {term}`provider` is a configured instance of a driver. It holds one service's
credentials—an issuer, a client id, a secret—and the decisions this site has
made about it. Two GitHub organizations are two providers sharing one driver.

An {term}`identity` is one person's account *at* one provider. It records the
{term}`subject` the provider uses for them, and which local user it belongs to.
One person may have several.

A {term}`user id` is the canonical Plone identifier for a person. It is minted
once, it is a random UUID by default, and it never changes—not when they change
their email address, not when they rename their GitHub account.

A {term}`profile` is the content object holding that person's fields: fullname,
email, portrait. It is real Plone content, with a workflow and a place in a
catalog.

A {term}`group` is likewise content, and membership can be granted locally or by
a provider.

```{mermaid}
erDiagram
    DRIVER ||--o{ PROVIDER : "is configured as"
    PROVIDER ||--o{ IDENTITY : "authenticates"
    IDENTITY }o--|| USERID : "belongs to"
    USERID ||--|| PROFILE : "is the account of"
    PROFILE }o--o{ GROUP : "is a member of"
    PROVIDER }o--o{ GROUP : "may grant"
```

The shape worth noticing: **many identities, one user id**. That is the whole
idea. Everything else is arranged around keeping that mapping honest.

## The two layers

```{mermaid}
:config: {"flowchart": {"htmlLabels": false}}

flowchart LR
    core["Core layer — pas.plugins.identity<br/>─────────────────────────<br/>Sign in with external providers<br/>Link and unlink identities<br/>Users and groups as content<br/>Audit log<br/>Control panel"]
    server["Server layer — the [server] extra<br/>─────────────────────────<br/>OAuth 2.1 / OpenID Connect<br/>authorization server<br/>Client registry, signing keys, consent"]
    server -- "imports" --> core
    core -. "never imports" .-> server
```

The core layer makes a Plone site a *client* of other identity providers. The
server layer makes it *be* one.

Core never imports from the server layer, and CI enforces that with an
import-linter contract rather than leaving it to discipline. So installing with
no extras is a configuration that is tested, not assumed.

There is a third extra, `[sql]`, which is not a layer: it adds one audit sink and
installs no profile.

## What a sign-in does

```{mermaid}
sequenceDiagram
    participant U as Person
    participant V as Volto frontend
    participant P as Plone backend
    participant X as Provider

    U->>V: click the provider's button
    V->>X: redirect to the provider
    X->>U: authenticate, and consent if asked
    X->>V: redirect back to /login-identity with a code
    V->>P: POST @identity-callback
    P->>X: exchange the code for tokens
    P->>P: normalize claims
    P->>P: resolve the identity by subject
    alt no identity, and the address is verified and trusted
        P->>P: attach to the existing account
    else no identity, and creation is allowed
        P->>P: mint a user id and create a profile
    else no identity, and creation is refused
        P-->>V: refuse, and record signin-refused
    end
    P->>P: reconcile groups this provider granted
    opt a group restriction is configured
        P->>P: refuse unless the person is in one
    end
    P-->>V: a session
```

Six decisions live in that diagram, and each is a setting:

| Step | Setting | Guide |
|---|---|---|
| resolve by subject | `userid_source` | {doc}`identities` |
| is the address verified | `trust_email_verification` | {doc}`email-verification` |
| attach to an existing account | `auto_link_by_email` | {doc}`/how-to-guides/link-accounts-by-email` |
| create an account | `create_user` | {doc}`/how-to-guides/control-account-creation` |
| reconcile groups | `sync_groups`, the group map | {doc}`/how-to-guides/map-provider-groups` |
| restrict sign-in | `allowed_groups` | {doc}`/how-to-guides/map-provider-groups` |

## Two things this package refuses to guess

**It never merges accounts.** An identity that would attach to a different
account than the one it is already on raises, and records a `link-collision`.
Merging two people's data is not a decision software should make silently.

**It never invents groups.** A provider group with no row in the map grants
nothing and is never created locally. A group claim is whatever the far end's
directory happens to be called, so minting local groups from it would let anyone
who can name a group there create one here.

## Which quadrant you need

`````{grid} 1 1 2 2
:gutter: 3

````{grid-item-card} 🛠️ Administrator
You are setting this up for a site.

{doc}`/how-to-guides/install` → {doc}`/how-to-guides/install-the-frontend` → a
recipe from {doc}`/how-to-guides/providers/index`.

Keep {doc}`/how-to-guides/troubleshoot` open.
````

````{grid-item-card} ⚖️ Integrator
You are deciding what a provider is allowed to mean.

{doc}`email-verification` and {doc}`profiles-and-groups` are the two that change
what you configure.

Then {doc}`threat-model`.
````

````{grid-item-card} 🔌 Driver author
You are adding support for a new provider.

{doc}`/how-to-guides/write-a-driver`, and {doc}`/reference/driver-contract` for
what a driver must implement.
````

````{grid-item-card} 🤝 Federating two Plone sites
You want one to sign in against the other.

{doc}`/tutorials/federation-demo` runs it in Docker.

Then {doc}`federation` for why the issuer is configured rather than derived.
````
`````

## Where to go next

- {doc}`identities`—why the user id is opaque, and what a collision means
- {doc}`layers`—what each layer buys and costs
- {doc}`threat-model`—what is trusted, and what reopens a hole
- {doc}`/glossary`—every term used above
