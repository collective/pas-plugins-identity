---
myst:
  html_meta:
    "description": "Let a self-managed GitLab instance sign its users in against a Plone site running the server layer."
    "property=og:description": "Let a self-managed GitLab instance sign its users in against a Plone site running the server layer."
    "property=og:title": "Client recipe: GitLab"
---

(how-to-client-gitlab)=

# GitLab

Let a self-managed GitLab instance sign its users in with accounts from your
Plone site, using GitLab's OpenID Connect provider.

```{warning}
**Not verified.** Nobody has run this recipe against this server yet. The
GitLab side follows GitLab's own documentation, which is the part to trust
when the two disagree:
[Use OpenID Connect as an authentication provider](https://docs.gitlab.com/administration/auth/oidc/).
```

The examples use `https://id.example.org` as the issuer and
`https://gitlab.example.org` as GitLab, installed with the Linux package.

## 1. Register the client

Follow {doc}`/how-to-guides/server/register-an-oauth-client` with:

| Field | Value |
|---|---|
| Redirect URI | `https://gitlab.example.org/users/auth/openid_connect/callback` |
| Grant | Authorization code |
| Scope | `openid`, `profile`, `email` |
| Secret | Yes. GitLab is a confidential client |

Capture the client secret from the response. It is shown once.

## 2. Configure GitLab

Add a provider to `/etc/gitlab/gitlab.rb`:

```ruby
gitlab_rails['omniauth_allow_single_sign_on'] = ['openid_connect']
gitlab_rails['omniauth_providers'] = [
  {
    name: "openid_connect",
    label: "id.example.org",
    args: {
      name: "openid_connect",
      scope: ["openid", "profile", "email"],
      response_type: "code",
      issuer: "https://id.example.org",
      discovery: true,
      client_auth_method: "basic",
      uid_field: "sub",
      pkce: true,
      client_options: {
        identifier: "CLIENT_ID",
        secret: "CLIENT_SECRET",
        redirect_uri: "https://gitlab.example.org/users/auth/openid_connect/callback"
      }
    }
  }
]
```

Replace `CLIENT_ID` and `CLIENT_SECRET` with the values from step 1, then
apply the change:

```shell
sudo gitlab-ctl reconfigure
```

## Verify

1. GitLab's sign-in page offers a button labeled with the **label** you set.
2. Choosing it takes you to your Plone site, which asks you to approve GitLab
   once.
3. You come back to GitLab signed in.

## Known quirks

<!-- source: backend/src/pas/plugins/identity/server/discovery.py, metadata -->

- **`uid_field` is `sub`.** It is the Plone user id, which never changes. The
  login name, `preferred_username`, can.
- **`issuer` has no trailing slash**, and must equal the issuer your site is
  configured with. GitLab compares it with the discovery document's `issuer`.
- **Logout ends only the GitLab session.** This server has no
  `end_session_endpoint`.

## Related

- {doc}`/how-to-guides/server/index`—the other client recipes, and what every client needs
- {doc}`/how-to-guides/server/register-an-oauth-client`—restricting GitLab to some groups
- {doc}`/reference/claims`—what the `profile` and `email` scopes release
