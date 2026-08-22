"""Letting a Volto-authenticated browser reach the authorization endpoint.

``@@oauth-authorize`` is a browser view, so the visitor arriving at it has to
be authenticated *as a Zope principal*. A user who signed in through Volto is
not: Volto keeps its ``jwt_auth`` token in an ``auth_token`` cookie and sends
it as an ``Authorization`` header on its own API calls, and
``plone.restapi``'s JWT plugin reads only that header. A top-level browser
navigation carries the cookie and no header, so the visitor is anonymous, is
challenged, and signs in a second time to a site they are already signed in
to.

Measured rather than assumed: on a running site, ``@@oauth-authorize`` with
only the cookie answers as an anonymous request, and the same request with the
token in an ``Authorization`` header authenticates.

This plugin closes exactly that gap and nothing wider. ``plone.restapi``
declines to read the cookie for a good reason -- a bearer credential the
browser attaches on its own turns every browser view into a CSRF target -- so
extraction here is refused unless the request is *for the authorization
endpoint itself*. Every other view in the site is left exactly as
``plone.restapi`` left it.

What that leaves exposed is one GET that renders a consent screen. The
decision on that screen is a POST, and it carries a form token that a forged
submission does not have.
"""

from AccessControl.class_init import InitializeClass
from pas.plugins.identity import logger
from pas.plugins.identity.core.interfaces import JSONDict
from plone import api
from Products.PluggableAuthService.interfaces.plugins import IAuthenticationPlugin
from Products.PluggableAuthService.interfaces.plugins import IExtractionPlugin
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements
from ZPublisher.HTTPRequest import HTTPRequest


#: Id of the plugin in ``acl_users``.
PLUGIN_ID = "identity_authorize_session"

#: Label shown in the ZMI.
PLUGIN_TITLE = "Identity: Volto session at the authorization endpoint"

#: The cookie Volto keeps its ``jwt_auth`` token in. Named by ``@plone/volto``
#: and not configurable there, so it is a constant here too.
COOKIE_NAME = "auth_token"

#: The one view this plugin will authenticate. Matched against the browser
#: facing URL rather than ``PATH_INFO``: behind a virtual host monster the
#: path still carries the rewriting prefix, and the point of this check is
#: what the *browser* asked for.
AUTHORIZE_VIEW = "@@oauth-authorize"

#: Id of ``plone.restapi``'s JWT plugin, whose key, algorithm and expiry this
#: plugin borrows rather than reimplements. A second opinion on how to read
#: the site's own token is a second thing to keep in step.
JWT_PLUGIN_ID = "jwt_auth"


class IdentityAuthorizeSessionPlugin(BasePlugin):
    """Authenticate the authorization endpoint from Volto's session cookie."""

    meta_type = "Identity Authorize Session Plugin"

    def __init__(self, id: str = PLUGIN_ID, title: str = PLUGIN_TITLE) -> None:
        """Build the plugin.

        :param id: Plugin id in ``acl_users``.
        :param title: Label shown in the ZMI.
        """
        self._setId(id)
        self.title = title

    # ------------------------------------------------------------------
    # IExtractionPlugin
    # ------------------------------------------------------------------

    def _wants_the_authorization_endpoint(self, request: HTTPRequest) -> bool:
        """Report whether this request is for the authorization endpoint.

        :param request: The current request.
        :returns: Whether the browser asked for :data:`AUTHORIZE_VIEW`.
        """
        return AUTHORIZE_VIEW in (request.get("ACTUAL_URL") or "")

    def extractCredentials(self, request: HTTPRequest) -> JSONDict:
        """Read Volto's token off the cookie, for one view only.

        The scope check runs *first*, so on every other request in the site
        this plugin costs one string comparison and reads no cookie at all.

        :param request: The current request.
        :returns: Credentials mapping, empty when this is not an
            authorization request or carries no Volto session.
        """
        if not self._wants_the_authorization_endpoint(request):
            return {}

        # An Authorization header outranks the cookie: it is the credential
        # the caller chose to present, and plone.restapi will read it anyway.
        # Extracting the cookie as well would let a stale cookie decide a
        # request that named a different principal.
        if getattr(request, "_auth", None):
            return {}

        token = request.cookies.get(COOKIE_NAME) or ""
        if not token:
            return {}
        return {"extractor": self.getId(), "token": token}

    # ------------------------------------------------------------------
    # IAuthenticationPlugin
    # ------------------------------------------------------------------

    def authenticateCredentials(self, credentials: JSONDict) -> tuple[str, str] | None:
        """Resolve Volto's token to a Plone principal.

        The token is decoded by ``plone.restapi``'s own plugin, so the key,
        the algorithm, the expiry and any token store it is configured with
        all apply unchanged. This plugin decides *when* the site's session
        cookie may be read, never *whether* the token in it is valid.

        :param credentials: Mapping from :meth:`extractCredentials`.
        :returns: ``(userid, login)`` on success, ``None`` otherwise -- for
            every failure without distinction.
        """
        if credentials.get("extractor") != self.getId():
            return None

        jwt_plugin = api.portal.get_tool("acl_users").get(JWT_PLUGIN_ID)
        if jwt_plugin is None:
            # A site without plone.restapi's JWT plugin has no Volto session
            # to read. Nothing is wrong; there is simply nothing here.
            return None

        payload = jwt_plugin._decode_token(credentials["token"]) or {}
        userid = payload.get("sub", "")
        if not userid or api.user.get(userid=userid) is None:
            logger.info(
                "Refused a Volto session cookie for %r, which is not a user "
                "in this site",
                userid,
            )
            return None
        return (userid, userid)


classImplements(
    IdentityAuthorizeSessionPlugin,
    IExtractionPlugin,
    IAuthenticationPlugin,
)

InitializeClass(IdentityAuthorizeSessionPlugin)
