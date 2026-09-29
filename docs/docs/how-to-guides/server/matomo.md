---
myst:
  html_meta:
    "description": "Let Matomo sign its users in against a Plone site running the server layer, with the RebelOIDC plugin."
    "property=og:description": "Let Matomo sign its users in against a Plone site running the server layer, with the RebelOIDC plugin."
    "property=og:title": "Client recipe: Matomo"
---

(how-to-client-matomo)=

# Matomo

Let Matomo sign its users in with accounts from your Plone site, using the
[RebelOIDC](https://github.com/Digitalist-Open-Cloud/Matomo-Plugin-RebelOIDC)
plugin.

```{note}
Verified on 2026-09-28.
```

The examples use `https://id.example.org` as the issuer and
`https://stats.example.org` as Matomo.

## 1. Register the client

Follow {doc}`/how-to-guides/server/register-an-oauth-client` with:

| Field | Value |
|---|---|
| Client ID | Any, for example `stats-example-org` |
| Redirect URI | `https://stats.example.org/index.php?module=RebelOIDC&action=callback&provider=oidc` |
| Grant | Authorization code |
| Scope | `openid`, `profile`, `email` |
| Secret | Yes. Matomo is a confidential client |

The redirect URI is matched exactly, query string included.

Capture the client secret from the response. It is shown once.

## 2. Configure Matomo

Install and activate the RebelOIDC plugin. Then, as a super user, open
{menuselection}`Administration --> System --> General settings` and find the
**RebelOIDC** section:

| Setting | Value |
|---|---|
| {guilabel}`Name` | The label on the login button, for example `id.example.org` |
| {guilabel}`Authorize URL` | `https://id.example.org/@@oauth-authorize` |
| {guilabel}`Token URL` | `https://id.example.org/@@oauth-token` |
| {guilabel}`Userinfo URL` | `https://id.example.org/@@oauth-userinfo` |
| {guilabel}`Logout URL` | empty |
| {guilabel}`Userinfo ID` | `sub`, the default |
| {guilabel}`Username Attribute from OIDC claim` | `preferred_username`, the default |
| {guilabel}`Fallback to Email` | on, the default |
| {guilabel}`Client ID` | The client ID from step 1 |
| {guilabel}`Client Secret` | The client secret from step 1 |
| {guilabel}`OAuth Scopes` | `openid profile email` |
| {guilabel}`Redirect URI override` | empty |
| {guilabel}`Restrict user login with specific role` | empty |
| {guilabel}`Enable auto linking` | on, to link existing Matomo users by email |
| {guilabel}`Create new users when users try to log in with unknown OIDC accounts` | on or off; see below |
| {guilabel}`Initial site id` | `none`, or the site new users may view |

Save the settings.

## Verify

1. Sign out of Matomo. Its login page offers a button with the
   {guilabel}`Name` you set.
2. Choosing it takes you to your Plone site, which asks you to approve Matomo
   once.
3. You come back to Matomo signed in. An existing user with the same email
   address is the one signed in, not a new, empty account.

## Known quirks

- **The accounts are linked by {guilabel}`Userinfo ID`.** `sub` is the Plone
  user id, which never changes. `preferred_username` is only the name a new Matomo user is given.
- **Auto linking needs the `email` scope.** It matches existing Matomo users
  by the `email` claim. Without the scope, each existing user gets a second,
  empty account.
- **New users:** with account creation on, anybody who can sign in to your
  Plone site can get a Matomo user. With **Initial site id** at `none`, they
  see nothing until a super user grants them a site. To keep Matomo to some
  people, restrict the client to their groups instead.
- **Leave Logout URL empty.** This server has no OpenID Connect logout
  endpoint.
- **Leave the role restriction empty.** It reads a `roles` claim, which this
  server does not issue. Use Matomo's own permissions, or the client's
  **Allowed groups**.
- **The secret travels in the request body** (`client_secret_post`), which
  this server accepts.

## Related

- {doc}`/how-to-guides/server/index`—the other client recipes, and what every client needs
- {doc}`/how-to-guides/server/register-an-oauth-client`—restricting Matomo to some groups, and
  redirect URIs that carry a query string
- {doc}`/reference/claims`—what the `profile` and `email` scopes release
