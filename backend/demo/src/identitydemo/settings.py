"""The fixed identities the two demo sites agree on.

Everything here is a constant rather than a generated value, and that is the
whole point: the IdP profile and the RP profile are applied in two separate
containers that never talk to each other at install time, so the only way the
RP can hold a credential the IdP will accept is for both to be written from
the same literal.

Which is also why this package must never be published, and why
:func:`identitydemo.setuphandlers.guard` refuses to install without an
explicit opt-in. A site that applied ``identitydemo:idp`` by accident would
have a registered OAuth client whose secret is in a public git repository.
"""

#: Environment variable that has to be set, to anything non-empty, before
#: either profile will install. See :func:`identitydemo.setuphandlers.guard`.
OPT_IN_ENV = "IDENTITY_DEMO"

#: Where the IdP is reachable *from the RP container*. The RP fetches
#: discovery server to server, so this is a compose service name, not a
#: browser-facing host.
IDP_INTERNAL_URL = "http://idp:8080/Plone"

#: Where the IdP is reachable *from the browser*. The authorization redirect
#: and the consent screen happen in the user agent, so this one has to resolve
#: on the developer's machine. Discovery publishes a single issuer, so these
#: two being different is the first thing to check when a flow half works.
IDP_PUBLIC_URL = "http://id.localhost:8080/Plone"

#: Where the RP is reachable from the browser.
RP_PUBLIC_URL = "http://plone.localhost:8081/Plone"

#: Where the identity provider sends the browser back to. A frontend route
#: rather than a backend view: the frontend reads code and state off the query
#: string and posts them to ``@identity-callback``. Nothing serves it in this
#: demo, and nothing needs to -- the flow test reads the redirect the way the
#: frontend would.
#:
#: The same literal is the relying party's ``callback_url`` record and the
#: identity provider's registered redirect URI. They are compared byte for
#: byte at the token endpoint, so this constant existing once is the point.
DEMO_REDIRECT_URI = "http://plone.localhost:8081/login-identity"

#: The client the RP authenticates as.
DEMO_CLIENT_ID = "demo-rp"
DEMO_CLIENT_TITLE = "Demo relying party"

#: Fixed, and therefore worthless outside this stack. The server stores only a
#: scrypt hash of it, so the IdP profile hashes this literal at install time
#: rather than calling ``add_client``, which mints a secret nobody could then
#: hand to the other container.
DEMO_CLIENT_SECRET = "demo-secret-not-for-any-real-site"  # noqa: S105

#: The provider id the RP files the IdP under. Never reused for a different
#: provider: doing so silently re-points every stored identity.
DEMO_PROVIDER_ID = "demo-idp"

#: The demo user, created on the IdP only. The RP learns about them through
#: the flow, which is the thing being demonstrated.
DEMO_USER_ID = "alice"
DEMO_USER_EMAIL = "alice@id.localhost"
DEMO_USER_PASSWORD = "alice-demo-password"  # noqa: S105
DEMO_USER_FULLNAME = "Alice Example"
