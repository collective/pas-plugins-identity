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

from pathlib import Path

import json
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

#: The demo user, read from the ``plone.exportimport`` payload that creates
#: them rather than restated here. They exist on the IdP only; the RP learns
#: about them through the flow, which is the thing being demonstrated.
_DEMO_MEMBER = json.loads(
    (Path(__file__).parent / "setuphandlers/idpcontent/principals.json").read_text()
)["members"][0]

DEMO_USER_ID = _DEMO_MEMBER["username"]
DEMO_USER_EMAIL = _DEMO_MEMBER["email"]
DEMO_USER_FULLNAME = _DEMO_MEMBER["fullname"]

#: What a reader is told to type, and therefore the one field that cannot come
#: out of the payload: an export carries the *hash*. It round-trips correctly
#: -- PAS re-encrypts nothing that is already encrypted -- but a hash is not
#: something anybody can log in with, and the flow test types this.
#:
#: The two are kept honest by :func:`demo_password_matches_the_payload`, which
#: the test suite asserts: re-exporting the IdP after changing Alice's
#: password would otherwise leave this line quietly wrong.
DEMO_USER_PASSWORD = "alice-demo-password"  # noqa: S105


def demo_password_matches_the_payload() -> bool:
    """Whether :data:`DEMO_USER_PASSWORD` is the one the payload installs.

    :returns: Whether the stored hash validates the documented password.
    """
    from AccessControl import AuthEncoding

    return bool(AuthEncoding.pw_validate(_DEMO_MEMBER["password"], DEMO_USER_PASSWORD))
