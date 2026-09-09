"""Interfaces for the ``[server]`` layer.

Kept in one module so the GenericSetup profile, the client registry and the
endpoints can all name them without importing each other.
"""

from pas.plugins.identity import _
from zope import schema
from zope.interface import Attribute
from zope.interface import Interface
from zope.publisher.interfaces.browser import IDefaultBrowserLayer


class IIdentityServerLayer(IDefaultBrowserLayer):
    """Browser layer installed by the ``server`` GenericSetup profile.

    Registrations that must not exist in a site which has not switched the
    authorization server on are bound to this layer. That matters more here
    than for the rest of the add-on: an unwanted ``/authorize`` endpoint is
    an attack surface, not merely an unused feature.
    """


#: The authorization code grant: a human authorized this at ``/authorize``.
AUTHORIZATION_CODE = "authorization_code"

#: The client-credentials grant: no human, no redirect, no code. The client
#: authenticates as itself and acts as its registered service user.
CLIENT_CREDENTIALS = "client_credentials"

#: The refresh grant: exchange a refresh token for a new access token, and a
#: new refresh token.
REFRESH_TOKEN = "refresh_token"  # noqa: S105 - a grant name, not a credential

#: Every grant the token endpoint implements. Named here rather than in the
#: endpoint so the discovery document can advertise exactly what is served
#: without importing a browser view -- an advertised grant nothing implements
#: is a lie a client acts on.
GRANT_TYPES = (AUTHORIZATION_CODE, CLIENT_CREDENTIALS, REFRESH_TOKEN)

#: Auth method of a client that has no secret.
#:
#: Public clients are the ones PKCE is mandatory for: a native or browser
#: app cannot keep a secret, so the proof of possession has to come from the
#: exchange itself. Named here rather than in ``clients`` because the client
#: *schema* needs it and the schema must not import the storage it describes.
PUBLIC_AUTH_METHOD = "none"


class ServerError(Exception):
    """A request to the authorization server cannot be honoured.

    Raised for conditions the caller can be told about without leaking
    anything -- an unknown client, a redirect URI that does not match. It is
    deliberately *not* used for a bad client secret, which must not be
    distinguishable from an unknown client.
    """


class IScopeSerializer(Interface):
    """Declares one OIDC scope and produces its claims for a user.

    Registered as a *named* multi-adapter on the site and the request, where
    the name **is** the scope. One serializer per scope, because scope is the
    unit a relying party asks in and a person consents to: two packages adding
    different scopes never collide, and replacing one is a deliberate act
    aimed at that scope rather than at everything this server releases.

    **Two halves, and both are needed.** ``claims`` is a declaration read with
    no user in hand; :meth:`__call__` produces values for one. A serializer
    that only did the second could not answer the three callers that ask what
    this server *could* emit -- the discovery document's ``scopes_supported``
    and ``claims_supported``, which are published to an unauthenticated
    caller, and the consent screen, which lists what a scope releases before
    anybody has agreed to it. A scope whose claims the consent screen cannot
    enumerate tells a person they are releasing less than they are, which is
    a consent defect rather than a cosmetic one.

    The two halves must agree. Nothing enforces it -- a serializer returning a
    claim it did not declare is released and simply never advertised -- but
    the declaration is what the person consenting was shown, so a value with
    no declaration is data released outside the consent.

    **Extending.** A downstream package adds a scope by registering another
    named adapter, and changes a shipped one by subclassing it and registering
    for its own browser layer, which is more specific and therefore wins. It
    calls ``super().__call__(user)`` and adds to the result, the way a
    ``plone.restapi`` serializer does. See
    :doc:`/how-to-guides/serialize-a-claim`.

    **What is not reachable from here.** ``sub`` is minted by
    :func:`~pas.plugins.identity.server.claims.claims_for` and belongs to no
    scope. It is the join every relying party stores against its local
    account, so a serializer able to change it could silently re-identify
    every federated user at every relying party, with nothing to migrate back
    from. ``iss``, ``aud``, ``exp`` and ``iat`` are set when a token is signed
    and likewise overwrite anything a serializer returns under those names.
    """

    claims = Attribute(
        "The claim names this scope releases, as a tuple. Read with no user "
        "in hand, for the discovery document and the consent screen, so it "
        "must not depend on who is signing in."
    )

    def __call__(user):
        """Return this scope's claims for one user.

        :param user: The Plone user the token acts for.
        :returns: A mapping of claim name to value. A claim this server has
            no value for may be omitted or returned as ``None`` or an empty
            string, list or mapping -- ``claims_for`` drops those either way,
            so OIDC's "absent rather than blank" rule holds for every
            serializer without each one having to remember it. ``False`` is a
            value and survives, which is what lets ``email_verified`` say the
            site checked and found nothing.
        """


class IServerSettings(Interface):
    """Registry settings for the ``[server]`` layer.

    Every record the layer reads is declared here, so the profile XML has a
    schema to be named after and a site administrator has one place to look.
    """

    server_clients = schema.Text(
        title=_("Registered OAuth clients"),
        description=_(
            "JSON list of client registrations. Written through the control "
            "panel rather than by hand; client secrets are stored hashed and "
            "cannot be read back."
        ),
        required=False,
        default="",
    )

    server_signing_keys = schema.Text(
        title=_("Signing key ring"),
        description=_(
            "JSON list of private JWKs, newest first. Generated when the "
            "server profile is applied and rotated from the control panel; "
            "never edited by hand. Only the public halves are published, as "
            "the JWKS relying parties fetch."
        ),
        required=False,
        default="",
    )

    server_issuer = schema.TextLine(
        title=_("Issuer URL"),
        description=_(
            "The `iss` value this server puts in tokens, and the base for its "
            "discovery document. Configured rather than derived from the "
            "portal URL, because it must stay byte-identical across every "
            "deployment detail that can rewrite a URL -- a proxy, a virtual "
            "host, a trailing slash -- or clients will reject the tokens."
        ),
        required=False,
        default="",
    )

    server_consent_url = schema.TextLine(
        title=_("Consent screen URL"),
        description=_(
            "Where to send the browser to ask a user whether they agree to "
            "an authorization request. Set it to the frontend route that "
            "renders the consent screen, and the question is asked in the "
            "site's own look; leave it empty and the server renders a "
            "standalone page of its own. The authorization request is "
            "appended as the query string, and the screen sends the browser "
            "back to the authorization endpoint with the answer."
        ),
        required=False,
        default="",
    )

    server_refresh_token_ttl = schema.Int(
        title=_("Refresh token lifetime (seconds)"),
        description=_(
            "Refresh tokens are rotated on every use, so this is how long a "
            "client may stay away before a human has to sign in again."
        ),
        required=False,
        default=1209600,
    )

    server_access_token_ttl = schema.Int(
        title=_("Access token lifetime (seconds)"),
        description=_(
            "Access tokens are self-encoded and there is no denylist, so "
            "this is also the worst-case window between a revocation and the "
            "last token honouring it."
        ),
        required=False,
        default=900,
    )
