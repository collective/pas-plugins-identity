"""The authorization server's PAS plugin.

Two jobs, and they arrived in that order.

It is the persistent home for the authorization codes, the recorded consent
and the refresh tokens, because every other persistent store in this package
lives on a PAS plugin -- the identity store, the magic-link burn list and the
audit log all sit on the core one. Putting them in a site annotation instead
would be the only such store in the package, and reaching into core's plugin
from here would cross the layer boundary the import-linter contract exists to
keep.

It is also the Bearer plugin: it turns an access token this server minted back
into a Plone principal. That is what makes a token worth issuing. Extraction
looks at one request header and stops, so an ordinary request pays a
dictionary lookup and nothing else; the signature check only happens for a
request that actually presented a Bearer token.

The plugin does *not* implement ``IChallengePlugin``. A request that fails to
authenticate here falls through to whatever the site already does, which for a
Plone site is a login form. Answering ``WWW-Authenticate: Bearer`` instead
would mean this add-on decided the site is an API, and that is not its call.
"""

from AccessControl.class_init import InitializeClass
from pas.plugins.identity import logger
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.server.clients import get_client
from pas.plugins.identity.server.codes import AuthorizationCodeStore
from pas.plugins.identity.server.consent import ConsentStore
from pas.plugins.identity.server.refresh import RefreshTokenStore
from pas.plugins.identity.server.tokens import decode_access_token
from pas.plugins.identity.server.tokens import TOKEN_TYPE
from pas.plugins.identity.server.tokens import TokenError
from plone import api
from Products.PluggableAuthService.interfaces.plugins import IAuthenticationPlugin
from Products.PluggableAuthService.interfaces.plugins import IExtractionPlugin
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements
from ZPublisher.HTTPRequest import HTTPRequest


#: Id of the plugin in ``acl_users``.
PLUGIN_ID = "identity_server"

#: Label shown in the ZMI.
PLUGIN_TITLE = "Identity: authorization server"

#: The scheme this plugin answers to, with its trailing space. Compared
#: case-insensitively: RFC 7235 makes the scheme token case-insensitive and
#: real clients do send ``bearer``.
BEARER_PREFIX = f"{TOKEN_TYPE} ".lower()


class IdentityServerPlugin(BasePlugin):
    """Persistent home for the server's state, and its Bearer plugin."""

    meta_type = "Identity Server Plugin"

    def __init__(self, id: str = PLUGIN_ID, title: str = PLUGIN_TITLE) -> None:
        """Create the plugin and its stores.

        :param id: Plugin id.
        :param title: Label for the ZMI.
        """
        self._setId(id)
        self.title = title
        self._codes = AuthorizationCodeStore()
        self._consent = ConsentStore()
        self._refresh = RefreshTokenStore()

    @property
    def refresh(self) -> RefreshTokenStore:
        """Return the refresh-token store.

        Created on demand as well as in ``__init__``, like its two
        neighbours. Losing it logs every client out rather than corrupting
        anything, which is survivable and still not worth an upgrade step.

        :returns: The store.
        """
        store = getattr(self, "_refresh", None)
        if store is None:
            store = self._refresh = RefreshTokenStore()
        return store

    @property
    def consent(self) -> ConsentStore:
        """Return the recorded-consent store.

        Created on demand as well as in ``__init__``, for the same reason as
        :attr:`codes` -- except that the stakes are the other way round here.
        A lost code costs somebody one retry; a lost consent record costs
        them a prompt they have already answered. Neither is worth an upgrade
        step, and both are worth surviving the attribute being absent.

        :returns: The store.
        """
        store = getattr(self, "_consent", None)
        if store is None:
            store = self._consent = ConsentStore()
        return store

    @property
    def codes(self) -> AuthorizationCodeStore:
        """Return the authorization code store.

        Created on demand as well as in ``__init__`` so that a plugin
        persisted before this attribute existed keeps working: the alternative
        is an upgrade step for a store whose contents are worthless after
        sixty seconds anyway.

        :returns: The store.
        """
        store = getattr(self, "_codes", None)
        if store is None:
            store = self._codes = AuthorizationCodeStore()
        return store

    # ------------------------------------------------------------------
    # IExtractionPlugin
    # ------------------------------------------------------------------

    def extractCredentials(self, request: HTTPRequest) -> JSONDict:
        """Extract a Bearer token from the request.

        One header read and a prefix test. Nothing is parsed and no signature
        is checked here: extraction runs on every request in the site, and
        this plugin has no business doing cryptography on requests that
        carry no token.

        The header is read off ``request._auth`` rather than through
        ``getHeader``: ZPublisher moves the ``Authorization`` header there
        during request construction and takes it out of the environment, so
        asking for the header by name finds nothing.

        :param request: The current request.
        :returns: Credentials mapping, empty when there is no Bearer token.
        """
        header = getattr(request, "_auth", None) or ""
        if not header.lower().startswith(BEARER_PREFIX):
            return {}
        token = header[len(BEARER_PREFIX) :].strip()
        if not token:
            return {}
        # PAS overwrites this key with the extracting plugin's id anyway; it
        # is set here so that a caller invoking the two methods directly gets
        # the same credentials PAS would have built.
        return {"extractor": self.getId(), "token": token}

    # ------------------------------------------------------------------
    # IAuthenticationPlugin
    # ------------------------------------------------------------------

    def authenticateCredentials(self, credentials: JSONDict) -> tuple[str, str] | None:
        """Resolve an access token to a Plone principal.

        Three things have to hold, and the audience check is the one worth
        explaining. The token's signature and expiry say this server minted it
        and it is still alive; they say nothing about whether the client it
        was minted for is still allowed to exist. Looking the audience up in
        the registry is what makes deleting or disabling a client take effect
        on tokens already in the wild -- which, with no denylist (D3), is the
        only revocation this server has.

        :param credentials: Mapping from :meth:`extractCredentials`.
        :returns: ``(userid, login)`` on success, ``None`` otherwise. ``None``
            for every failure without distinction: a caller that can tell an
            expired token from one signed with the wrong key learns which half
            of a forgery to keep.
        """
        # Plone's own ``jwt_auth`` reads ``Authorization: Bearer`` too, so
        # both plugins extract from the same request and PAS offers every
        # extractor's credentials to every authenticator. The id it stamps on
        # them is how each one recognises its own work.
        if credentials.get("extractor") != self.getId():
            return None

        try:
            claims = decode_access_token(credentials["token"])
        except TokenError:
            return None

        client = get_client(claims.get("aud", ""))
        if client is None or not client.enabled:
            return None

        userid = claims.get("sub", "")
        if not userid or api.user.get(userid=userid) is None:
            # The token outlived the user it was minted for. Authenticating
            # them anyway would put a principal on the request that no roles
            # plugin has heard of.
            logger.info(
                "Refused a token for %r, which is not a user in this site", userid
            )
            return None
        return (userid, userid)


classImplements(
    IdentityServerPlugin,
    IExtractionPlugin,
    IAuthenticationPlugin,
)

InitializeClass(IdentityServerPlugin)
