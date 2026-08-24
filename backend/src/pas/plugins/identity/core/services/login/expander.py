"""``@login-providers`` as a plone.restapi expandable component.

The sign-in buttons are wanted alongside something else more often than on
their own: the identities page lists what a user has linked *and* what they
could link next, which was two round-trips for one screen. Registering the
listing as an expandable component lets a caller ask for both in one request
without this package inventing a combined endpoint that would then have to be
kept in step with the one it duplicates.

Unexpanded it costs a URL, which is the contract every other component
follows -- a client that does not ask still learns where to look.
"""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.services.login import provider_listing
from plone.restapi.interfaces import IExpandableElement
from Products.CMFCore.interfaces import ISiteRoot
from Products.CMFPlone.Portal import PloneSite
from zope.component import adapter
from zope.interface import implementer
from ZPublisher.HTTPRequest import HTTPRequest


@implementer(IExpandableElement)
@adapter(ISiteRoot, HTTPRequest)
class LoginProviders:
    """Offer the enabled providers as ``login-providers``."""

    def __init__(self, context: PloneSite, request: HTTPRequest) -> None:
        """Bind the component.

        :param context: The site the providers are configured on.
        :param request: The current request.
        """
        self.context = context
        self.request = request

    def __call__(self, expand: bool = False) -> JSONDict:
        """Render the component.

        :param expand: Whether the caller asked for the full listing.
        :returns: The component, keyed by its own name.
        """
        base = f"{self.context.absolute_url()}/@login-providers"
        if not expand:
            return {"login-providers": {"@id": base}}
        return {"login-providers": provider_listing(self.context)}
