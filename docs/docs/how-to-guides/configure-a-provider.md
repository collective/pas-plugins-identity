---
myst:
  html_meta:
    "description": "Add, test, edit, and delete an identity provider from the Plone control panel."
    "property=og:description": "Add, test, edit, and delete an identity provider from the Plone control panel."
    "property=og:title": "How to configure a provider"
---

(how-to-configure-a-provider)=

# How to configure a provider

This guide shows you how to register an identity provider, test it, and remove it.

A provider is a configured instance of a driver.
The driver knows how to talk to a kind of service, and the provider record holds this site's credentials for one particular service.
Two GitHub organizations are two providers sharing one driver.

For the drivers you can choose from, see {doc}`/reference/shipped-drivers`.

## Add a provider

1.  Open the **Identity providers** control panel.
2.  Choose a driver.
3.  Fill in the form.

The form is generated from the driver's published schema, so a site that installs a third-party driver gets that driver's form with no frontend change.

Configuration lives in the registry as a single JSON record, which keeps the whole thing exportable and importable through GenericSetup in one place.

## Test the connection

Each provider has a **Test connection** action.

It fetches the provider's discovery document, or validates the static configuration for drivers that have no discovery, and reports what it found.
It clears the discovery cache first, because a button that reports the answer from twelve hours ago is worse than no button at all.

## Change a secret, or keep it

The control panel serializes a stored client secret as a mask, never as its value.

-   To keep the stored secret, save the form with the mask unchanged.
-   To replace the secret, type the new one over the mask.

```{warning}
Do not clear the field to keep the existing secret.
Blanking it sends an empty string, which is a different instruction, and it destroys the stored secret.
```

A GenericSetup export omits secrets, so an export of your provider configuration is not enough to rebuild a working site.
The secrets have to travel separately, by whatever means your deployment already uses for secrets.

Read {doc}`/concepts/secrets` for why secrets behave differently here than they do when the site acts as an authorization server.

## Delete a provider

Deleting a provider removes its configuration.

It does **not** delete the identities linked through it.
Those are account data, and a configuration change is not an instruction to lock people out.
If you want the identities gone as well, remove them first.

## Configure magic-link sign-in

The `email` driver needs no external provider.
The site emails a signed, single-use token instead.

Add a provider using the `email` driver, and the sign-in option appears on the login page.

The token lives for at most fifteen minutes whatever you configure, and it is burned server-side after one use.
The send endpoint is rate limited per address and per IP, and answers identically whether or not the address belongs to an account.

## Next steps

-   {doc}`enable-back-channel-logout`, so a sign-out at the provider ends the session here.
-   {doc}`/reference/audit-log`, to confirm that sign-ins are landing.
