"""The identities and URLs the two demo sites agree on.

The credentials are fixed literals, and that is the whole point: the IdP
profile and the RP profile are applied in two separate containers that never
talk to each other at install time, so the only way the RP can hold a
credential the IdP will accept is for both to be written from the same value.

Which is also why this package must never be published, and why
:func:`identitydemo.setuphandlers.guard` refuses to install without an
explicit opt-in. A site that applied ``identitydemo:idp`` by accident would
have a registered OAuth client whose secret is in a public git repository.

The *URLs* are not fixed, because there are two demo deployments and they do
not agree on them. The hermetic federation stack publishes ports and reaches
Plone at ``/Plone``; the manual stack puts Traefik in front and serves each
site at the root of its own hostname. Both are read from the environment with
the hermetic values as defaults, so the test stack needs no configuration and
the manual stack overrides four variables.

Every one of these is read *at import time* rather than looked up per call:
the setup handlers write them into the site, and a value that could change
between two handlers in one install would be a demo that half agrees with
itself.
"""

import os


def _url(name: str, default: str) -> str:
    """Read a URL from the environment, without a trailing slash.

    A trailing slash is the difference between an issuer that matches and one
    that does not: it is compared as a string, never parsed.

    :param name: Environment variable to read.
    :param default: Value for the hermetic test stack.
    :returns: The configured URL.
    """
    return (os.environ.get(name) or default).rstrip("/")


#: Environment variable that has to be set, to anything non-empty, before
#: either profile will install. See :func:`identitydemo.setuphandlers.guard`.
OPT_IN_ENV = "IDENTITY_DEMO"

#: Where the IdP is reachable *from the browser*. The authorization redirect
#: and the consent screen happen in the user agent, so this has to resolve on
#: the developer's machine. It is also the issuer, byte for byte: discovery
#: publishes one, and the relying party compares it as a string.
IDP_PUBLIC_URL = _url("DEMO_IDP_URL", "http://id.localhost:8080/Plone")

#: Where the identity provider asks a user to approve an authorization
#: request. The frontend route, so the question is rendered in the site's own
#: look rather than by the standalone page the server falls back to. Derived
#: from the issuer because in this stack Volto and the backend answer on the
#: same host; a deployment where they do not would configure it separately.
IDP_CONSENT_URL = f"{IDP_PUBLIC_URL.rstrip('/')}/oauth-consent"

#: Where the RP is reachable from the browser.
RP_PUBLIC_URL = _url("DEMO_RP_URL", "http://plone.localhost:8081/Plone")

#: Where the identity provider sends the browser back to. A frontend route
#: rather than a backend view: the frontend reads code and state off the query
#: string and posts them to ``@identity-callback``.
#:
#: In the hermetic stack nothing serves it, and nothing needs to -- the flow
#: test reads the redirect the way the frontend would. In the manual stack
#: Volto serves it for real, which is the difference between the two.
#:
#: This same value is the relying party's ``callback_url`` record and the
#: identity provider's registered redirect URI. They are compared byte for
#: byte at the token endpoint, so it existing once is the point.
DEMO_REDIRECT_URI = _url(
    "DEMO_REDIRECT_URI", "http://plone.localhost:8081/login-identity"
)

#: The client the RP authenticates as.
DEMO_CLIENT_ID = "demo-rp"
DEMO_CLIENT_TITLE = "Plone Content Site"

#: Fixed, and therefore worthless outside this stack. The server stores only a
#: scrypt hash of it, so the IdP profile hashes this literal at install time
#: rather than calling ``add_client``, which mints a secret nobody could then
#: hand to the other container.
DEMO_CLIENT_SECRET = "demo-secret-not-for-any-real-site"  # noqa: S105

#: The provider id the RP files the IdP under. Never reused for a different
#: provider: doing so silently re-points every stored identity.
DEMO_PROVIDER_ID = "demo-idp"

#: The demo user. They exist on the IdP only; the relying party learns about
#: them through the flow, which is the thing being demonstrated.
#:
#: Four literals rather than a ``plone.exportimport`` payload, which is what
#: this was. A payload cannot carry the one thing this user needs: their
#: password lives in an annotation on their Profile, and an annotation is
#: exactly what an export does not serialize -- which is the point of keeping
#: a credential there rather than in a field. Importing them as principals
#: instead is what the old payload did, and that is how the provider ended up
#: with its demo user in ``source_users``: the store this demo exists to show
#: a site does not need.
DEMO_USER_ID = "dana"
DEMO_USER_EMAIL = "dana@id.localhost"
DEMO_USER_FULLNAME = "Dana Example"

#: What a reader is told to type, and what the flow test types.
DEMO_USER_PASSWORD = "dana-demo-password"  # noqa: S105

#: The demo group, and the role it carries.
#:
#: A group here is a content object, the same bargain the demo user is: it
#: lives beside the Profiles rather than in ``source_groups``, and membership
#: is a field on the *member* rather than a list on the group. Created through
#: ``api.group.create`` for the reason the user is created through
#: ``api.user.create`` -- a principals payload would import it the way Plone
#: has always made groups, into the store this demo exists to show a site
#: does not need.
#:
#: It carries a role so that belonging to it *does* something. A group with no
#: role demonstrates that groups can exist, which is not the interesting
#: claim; this one is why the demo user can edit the provider's own content.
DEMO_GROUP_ID = "site-editors"
DEMO_GROUP_TITLE = "Site Editors"
DEMO_GROUP_DESCRIPTION = "Demo group: its members may edit this site."
DEMO_GROUP_ROLES = ("Editor",)
