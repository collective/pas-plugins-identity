"""Whether a client admits the person a grant is for.

A client may be registered for members of some groups only. The authorization
endpoint asks before a code exists, and the refresh grant asks again at every
rotation, so somebody removed from those groups stops getting tokens once
their access token expires rather than for as long as a refresh token lives.
"""

from pas.plugins.identity.core import audit
from pas.plugins.identity.server.controlpanel.clients import ClientConfig
from plone import api
from zope.globalrequest import getRequest

import logging


logger = logging.getLogger(__name__)


def admitted(client: ClientConfig, userid: str, stage: str) -> bool:
    """Whether the client admits a user, recording a refusal when it does not.

    Group membership is PAS's own answer, so it includes groups reached
    through a nested group and through any other group plugin. A user PAS
    cannot resolve is in no group.

    :param client: The client the grant is for.
    :param userid: The user the grant is for.
    :param stage: Where the question is asked, ``authorize`` or ``refresh``,
        recorded with a refusal so an operator can tell the two apart.
    :returns: Whether the grant may proceed.
    """
    if not client.allowed_groups:
        return True
    user = api.user.get(userid=userid)
    groups = user.getGroups() if user is not None else []
    if client.admits(groups):
        return True
    # The person is told only that they may not use this client. Which groups
    # would have let them in is for the operator, who reads the log and the
    # audit trail.
    logger.info(
        "Refused %s for client %s at %s: in none of its allowed groups",
        userid,
        client.client_id,
        stage,
    )
    audit.record(
        userid,
        audit.CLIENT_REFUSED,
        client.client_id,
        False,
        {"client_id": client.client_id, "stage": stage},
        request=getRequest(),
    )
    return False
