"""Events the authorization server fires.

The server-side half of the event contract. The events in
:mod:`pas.plugins.identity.core.events` describe this site signing people in
*against* a provider; these describe this site being the provider. They live
in the ``[server]`` layer because only that layer fires them, and core must
not import it.
"""

from pas.plugins.identity.core.events import IIdentityEvent
from zope.interface import Attribute
from zope.interface import implementer


class IClientAuthorized(IIdentityEvent):
    """Fired when a user authorizes a client, as the code is issued.

    It fires for every authorization code issued, which includes a silent
    ``prompt=none`` sign-in and one whose consent was already on record. So a
    subscriber runs on every sign-in through a client, not only the first.
    Write only when something changes, or every sign-in costs a ZODB write.

    It does not fire when the flow stops before a code is issued (sign-in
    required, an incomplete profile, consent pending or refused), nor for the
    client-credentials grant, where no person is present.
    """

    client_id = Attribute("The client the code was issued to.")
    scope = Attribute("The granted scope, space-separated, as requested.")


@implementer(IClientAuthorized)
class ClientAuthorized:
    """See :class:`IClientAuthorized`."""

    def __init__(self, userid: str, client_id: str, scope: str) -> None:
        """Record that a user authorized a client.

        :param userid: The Plone userid the code was issued for: its ``sub``.
        :param client_id: The client the code was issued to.
        :param scope: The granted scope, space-separated.
        """
        self.userid = userid
        self.client_id = client_id
        self.scope = scope
