"""Where the ``[server]`` layer listens to the core layer.

The one place the two ends of a federated site meet. Core cannot import
``server`` -- the import-linter contract forbids it -- so when a provider
back-channels a logout to this site, core ends the Plone session and fires
:class:`~pas.plugins.identity.core.events.SessionsRevoked`, and this
subscriber revokes the refresh tokens this site issued as an authorization
server.

That chain is what makes a logout at the top of a federation reach the bottom
of it. What it cannot reach is an access token already in flight: those are
self-encoded and there is no denylist, so they live out their lifetime.
The refresh tokens are the part that would otherwise let a client keep
renewing access long after the person behind it signed out somewhere else.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.events import ISessionsRevoked
from pas.plugins.identity.server.pas import PLUGIN_ID
from plone import api
from zope.component import adapter


@adapter(ISessionsRevoked)
def revoke_refresh_tokens(event) -> None:
    """Revoke the refresh tokens issued for a user who has been logged out.

    :param event: The :class:`ISessionsRevoked` event.
    """
    acl_users = api.portal.get_tool("acl_users")
    plugin = acl_users.get(PLUGIN_ID)
    if plugin is None:
        # This site is a relying party but not an authorization server, so
        # there are no refresh tokens of its own to revoke. The [server]
        # profile is what installs the plugin, and a site may well never
        # apply it.
        return
    revoked = plugin.refresh.revoke_for_subject(event.userid)
    if revoked:
        logger.info(
            "Back-channel logout from %s revoked %s refresh token(s) for %s",
            event.provider,
            revoked,
            event.userid,
        )
