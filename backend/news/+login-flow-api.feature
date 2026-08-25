Added the login-flow REST services. `GET @login-providers` lists the providers a user may log in with, `GET @login-providers/<id>` starts an authorization-code flow and returns the URL to send the browser to, and `POST @identity-callback` completes one and answers with a `jwt_auth` token — the same token `@login` issues, so everything downstream of signing in is unchanged.

The callback identifies the flow from the `state` a provider redirects back with, which is what a provider actually sends; requiring the caller to name the provider as well made every browser login fail at the last step.

`@login-providers` is also a plone.restapi expandable component, because the sign-in buttons are wanted alongside something else more often than on their own: the identities page lists what a user has linked *and* what they could link, which is one screen and now one request.

Magic-link login is its own driver. `POST @magic-link` mails a signed, single-use, short-lived link and `POST @magic-link-confirm` redeems it for a `jwt_auth` token. Tokens are authlib-signed from the same keyring the flow session uses, rate-limited per address, and the endpoint says the same thing whether or not the address is known — an endpoint that answers differently is an account-enumeration oracle with a friendly message. @ericof
