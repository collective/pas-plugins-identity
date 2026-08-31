"""Interfaces for the ``[server]`` layer.

Kept in one module so the GenericSetup profile, the client registry and the
endpoints can all name them without importing each other.
"""

from pas.plugins.identity import _
from zope import schema
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
