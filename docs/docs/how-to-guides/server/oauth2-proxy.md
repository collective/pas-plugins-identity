---
myst:
  html_meta:
    "description": "Put an application behind oauth2-proxy, signing people in against a Plone site running the server layer."
    "property=og:description": "Put an application behind oauth2-proxy, signing people in against a Plone site running the server layer."
    "property=og:title": "Client recipe: oauth2-proxy"
---

(how-to-client-oauth2-proxy)=

# oauth2-proxy

Put an application that has no sign-in of its own behind
[oauth2-proxy](https://oauth2-proxy.github.io/oauth2-proxy/), so only people
with an account on your Plone site reach it.

```{warning}
**Not verified.** Nobody has run this recipe against this server yet. The
oauth2-proxy side follows its own documentation, which is the part to trust
when the two disagree:
[OpenID Connect provider](https://oauth2-proxy.github.io/oauth2-proxy/configuration/providers/openid_connect).
```

The examples use `https://id.example.org` as the issuer and
`https://app.example.org` as the application behind the proxy.

## 1. Register the client

Follow {doc}`/how-to-guides/server/register-an-oauth-client` with:

| Field | Value |
|---|---|
| Redirect URI | `https://app.example.org/oauth2/callback` |
| Grant | Authorization code |
| Scope | `openid`, `profile`, `email` |
| Secret | Yes. oauth2-proxy is a confidential client |

Capture the client secret from the response. It is shown once.

To let only some people through, give the client **Allowed groups**. Your site
then refuses everybody else before oauth2-proxy sees them.

## 2. Configure oauth2-proxy

Start it with the OpenID Connect provider:

```shell
oauth2-proxy \
  --provider=oidc \
  --oidc-issuer-url=https://id.example.org \
  --client-id=CLIENT_ID \
  --client-secret=CLIENT_SECRET \
  --redirect-url=https://app.example.org/oauth2/callback \
  --scope="openid profile email" \
  --code-challenge-method=S256 \
  --email-domain="*" \
  --cookie-secret=COOKIE_SECRET \
  --upstream=http://app:8080
```

Replace `CLIENT_ID` and `CLIENT_SECRET` with the values from step 1,
`COOKIE_SECRET` with a random 32-byte value, and the upstream with the
application's address.

## Verify

1. Opening `https://app.example.org` takes you to oauth2-proxy's sign-in page,
   or straight to your Plone site.
2. Your site asks you to approve the proxy once.
3. You come back to the application.

## Known quirks

<!-- source: backend/src/pas/plugins/identity/server/claims.py -->

- **Unverified addresses are refused.** oauth2-proxy rejects a user whose
  `email_verified` claim is `false`. This server sends `true` only for an
  address it holds as verified, so a user whose address is unverified here
  cannot get through. See {doc}`/concepts/email-verification`.
- **Groups:** `--allowed-group` checks the `groups` claim, which the `profile`
  scope releases. Restricting the client on your site does the same job
  earlier, and in one place.
- **Logout ends only the proxy's session.** This server has no
  `end_session_endpoint`.

## Related

- {doc}`/how-to-guides/server/index`—the other client recipes, and what every client needs
- {doc}`/how-to-guides/server/register-an-oauth-client`—restricting the client to some groups
- {doc}`/reference/claims`—what the `profile` and `email` scopes release
