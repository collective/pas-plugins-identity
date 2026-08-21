# Providers and secrets

A provider is a configured instance of a driver. The driver knows how to talk
to a kind of service; the provider record holds this site's credentials for
one particular one. Two GitHub organizations are two providers sharing one
driver.

Configuration lives in the registry as a single JSON record, which keeps the
whole thing exportable and importable through GenericSetup in one place.

## The control panel

**Identity providers** lists what is configured and offers a form per driver.
The form is generated from the driver's published schema, so a site that
installs a third-party driver gets its form with no frontend change.

Each provider has a **test connection** action, which fetches the provider's
discovery document (or validates the static configuration, for drivers that
have no discovery) and reports what it found. It clears the discovery cache
first: a button that reports the answer from twelve hours ago is worse than no
button.

## Secrets are write-only

Client secrets never leave the backend.

- The REST API and the control panel serialize a stored secret as a mask,
  never as its value.
- Saving the form back with the mask unchanged preserves the stored secret.
  That is what the mask is *for* — blanking the field would send an empty
  string, which is a different instruction and would destroy the secret.
- GenericSetup export omits secrets.
- The audit log never records credentials or tokens.

:::{warning}
This means a GenericSetup export of your provider configuration is not enough
to rebuild a working site. The secrets have to travel separately, by whatever
means your deployment already uses for secrets.
:::

## Deleting a provider

Deleting a provider removes its configuration. It does **not** delete the
identities linked through it: those are account data, and a configuration
change is not an instruction to lock people out. If you want the identities
gone as well, remove them first.

## Drivers shipped with the package

`github`
: GitHub OAuth. Uses GitHub's published endpoints rather than discovery,
  because GitHub does not publish a discovery document.

`google`
: Google, via OIDC discovery.

`oidc-generic`
: Any OpenID Connect provider, configured with its discovery URL.

`email`
: Magic-link sign-in. No external provider at all; the site emails a
  single-use signed token. See below.

## Magic links

The `email` driver sends a signed, single-use token with a lifetime of at most
fifteen minutes whatever you configure. The send endpoint is rate limited per
address **and** per IP — limiting per address alone misses the enumeration
attack, which uses a fresh address every time.

The send endpoint answers identically whether or not the address belongs to an
account. That is deliberate: a different answer is an account-existence oracle.

## Writing your own driver

See {doc}`drivers`.
