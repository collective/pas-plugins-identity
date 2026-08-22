"""``@identities`` -- see, link and unlink your own external identities.

Three shapes:

``GET @identities``
    List the identities the authenticated user owns.

``POST @identities`` with ``{"provider": "<id>"}``
    Start a linking flow and answer with the authorize URL. The attempt
    remembers whose account it is linking to, and the callback refuses to
    complete it as anybody else.

``DELETE @identities/<provider>/<subject>``
    Unlink, unless it is the user's last way in.

Every one of them is about *your own* account. There is no shape here that
takes a userid: an administrator repairing someone else's identities is a
different feature with a different permission, and conflating the two is how
an ordinary user ends up able to attach their provider account to somebody
else's login.
"""

from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.core.pas.plugin import IdentityPlugin
from pas.plugins.identity.core.services.base import IdentityService
from plone import api
from Products.CMFPlone.Portal import PloneSite
from zope.interface import alsoProvides
from zope.interface import implementer
from zope.publisher.interfaces import IPublishTraverse
from ZPublisher.HTTPRequest import HTTPRequest

import plone.protect.interfaces


@implementer(IPublishTraverse)
class IdentitiesBase(IdentityService):
    """Shared plumbing for the three ``@identities`` shapes.

    plone.rest registers one factory per HTTP method, so the verbs are three
    classes rather than three branches.
    """

    def __init__(self, context: PloneSite, request: HTTPRequest) -> None:
        """Bind the service and prepare to consume path segments.

        :param context: The context the service was traversed on.
        :param request: The current request.
        """
        super().__init__(context, request)
        self.segments: list[str] = []

    def publishTraverse(self, request: HTTPRequest, name: str) -> "IdentitiesBase":
        """Collect ``<provider>`` and ``<subject>`` from the URL.

        :param request: The current request.
        :param name: The next path segment.
        :returns: This service.
        """
        self.segments.append(name)
        return self

    def _userid(self) -> str | None:
        """Return the authenticated userid.

        :returns: The userid, or ``None`` when nobody is logged in.
        """
        user = api.user.get_current()
        return None if api.user.is_anonymous() else user.getId()

    def _plugin(self) -> IdentityPlugin:
        """Return the identity plugin.

        :returns: The plugin installed in this site.
        """
        return api.portal.get_tool("acl_users")[PLUGIN_ID]

    def _disable_csrf(self) -> None:
        """Exempt a write from plone.protect's form authenticator.

        Volto sends a token, not a Plone form token. The request is
        authenticated and the action only ever touches the caller's own
        account, which is what makes this safe to do here.
        """
        alsoProvides(self.request, plone.protect.interfaces.IDisableCSRFProtection)
