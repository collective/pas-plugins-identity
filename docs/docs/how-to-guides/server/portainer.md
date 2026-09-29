---
myst:
  html_meta:
    "description": "Let Portainer sign its users in against a Plone site running the server layer."
    "property=og:description": "Let Portainer sign its users in against a Plone site running the server layer."
    "property=og:title": "Client recipe: Portainer"
---

(how-to-client-portainer)=

# Portainer

Let Portainer sign its users in with accounts from your Plone site, using its
custom OAuth provider.

```{note}
Verified on 2026-09-24.
```

The examples use `https://id.example.org` as the issuer and
`https://portainer.example.org` as Portainer.

## 1. Register the client

Follow {doc}`/how-to-guides/server/register-an-oauth-client` with:

| Field | Value |
|---|---|
| Redirect URI | `https://portainer.example.org` |
| Grant | Authorization code |
| Scope | `openid`, `profile`, `email` |
| Secret | Yes. Portainer is a confidential client |

Capture the client secret from the response. It is shown once.

## 2. Configure Portainer

Portainer does not read a discovery document, so every endpoint is typed in.

Open {menuselection}`Settings --> Authentication`, choose **OAuth**, then the
**Custom** provider, and fill in:

| Field | Value |
|---|---|
| {guilabel}`Client ID` | The client ID from step 1 |
| {guilabel}`Client secret` | The client secret from step 1 |
| {guilabel}`Authorization URL` | `https://id.example.org/@@oauth-authorize` |
| {guilabel}`Access token URL` | `https://id.example.org/@@oauth-token` |
| {guilabel}`Resource URL` | `https://id.example.org/@@oauth-userinfo` |
| {guilabel}`Redirect URL` | `https://portainer.example.org` |
| {guilabel}`Logout URL` | `https://id.example.org/logout` |
| {guilabel}`User identifier` | `preferred_username`, or `sub` |
| {guilabel}`Scopes` | `openid profile email` |
| {guilabel}`Auth Style` | {guilabel}`In Header` |

Save the settings.

## Verify

1. Sign out of Portainer. Its login page offers **Login with OAuth**.
2. Choosing it takes you to your Plone site, which asks you to approve
   Portainer once.
3. You come back to Portainer signed in, as the user named by the claim in
   **User identifier**.

## Known quirks

- **User identifier:** `preferred_username` is the Plone login name, which
  Portainer shows as the user name. `sub`, the Plone user id, never changes and
  is the safer choice if login names might.
- **Logout ends the Plone session only.** This server has no OpenID Connect
  logout endpoint, so the **Logout URL** above signs the user out of your Plone
  site and does nothing else.
- **Teams:** the `profile` scope also releases a `groups` claim, which
  Portainer's automatic team membership can read.

## Related

- {doc}`/how-to-guides/server/index`—the other client recipes, and what every client needs
- {doc}`/how-to-guides/server/register-an-oauth-client`—restricting Portainer to some groups
- {doc}`/reference/claims`—what the `profile` and `email` scopes release
