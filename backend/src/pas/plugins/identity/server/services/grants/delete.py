"""``DELETE @oauth-grants/<client_id>`` -- withdraw one agreement."""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.services.base import IdentityService
from pas.plugins.identity.server.pas import PLUGIN_ID
from pas.plugins.identity.server.grants.tokens import TTL_RECORD
from plone import api
from Products.CMFPlone.Portal import PloneSite
from zope.interface import alsoProvides
from zope.interface import implementer
from zope.publisher.interfaces import IPublishTraverse
from ZPublisher.HTTPRequest import HTTPRequest

import plone.protect.interfaces


@implementer(IPublishTraverse)
class GrantsDelete(IdentityService):
    """Withdraw the caller's agreement with one client."""

    def __init__(self, context: PloneSite, request: HTTPRequest) -> None:
        """Bind the service and prepare to consume path segments.

        :param context: The context the service was traversed on.
        :param request: The current request.
        """
        super().__init__(context, request)
        self.segments: list[str] = []

    def publishTraverse(self, request: HTTPRequest, name: str) -> "GrantsDelete":
        """Collect ``<client_id>`` from the URL.

        :param request: The current request.
        :param name: The next path segment.
        :returns: This service.
        """
        self.segments.append(name)
        return self

    def reply(self) -> JSONDict:
        """Forget the agreement and cut off what it already granted.

        Both halves, because either alone is a lie. Forgetting the record
        only decides what happens the next time that client asks; revoking
        the refresh tokens is what ends the access it already has.

        Access tokens are not reached and cannot be: they are self-encoded
        with no denylist. The answer says how long one may still work rather
        than leaving a screen to imply an instant cutoff.

        :returns: What was withdrawn, or an error body.
        """
        # Volto sends its own token rather than a Plone form authenticator,
        # and this only ever touches the caller's own agreements.
        alsoProvides(self.request, plone.protect.interfaces.IDisableCSRFProtection)

        if api.user.is_anonymous():
            return self._error(
                401,
                "Not authenticated",
                "Only a signed-in user has anything to withdraw.",
            )

        if len(self.segments) != 1:
            return self._error(
                400,
                "Bad request",
                "Expected @oauth-grants/<client_id>",
            )
        client_id = self.segments[0]

        userid = api.user.get_current().getId()
        plugin = api.portal.get_tool("acl_users")[PLUGIN_ID]

        if not plugin.consent.forget(userid, client_id):
            # Nothing agreed to, or already withdrawn. Reported as 404
            # rather than as success: a screen that says "revoked" for an
            # application the user never authorized is telling them
            # something false about their own account.
            return self._error(
                404,
                "Not authorized",
                f"You have no standing agreement with {client_id!r}.",
            )

        revoked = plugin.refresh.revoke_for_client(userid, client_id)
        return {
            "client_id": client_id,
            # How many of this user's sessions with that client ended now.
            "refresh_tokens_revoked": revoked,
            # And the window in which one of its access tokens may still be
            # accepted, which is what the screen has to say out loud.
            "access_token_ttl": int(
                api.portal.get_registry_record(TTL_RECORD, default=900)
            ),
        }
