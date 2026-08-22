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
    than for the ``[profile]`` layer: an unwanted ``/authorize`` endpoint is
    an attack surface, not merely an unused feature.
    """


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

    server_access_token_ttl = schema.Int(
        title=_("Access token lifetime (seconds)"),
        description=_(
            "D3: access tokens are self-encoded and there is no denylist, so "
            "this is also the worst-case window between a revocation and the "
            "last token honouring it."
        ),
        required=False,
        default=900,
    )
