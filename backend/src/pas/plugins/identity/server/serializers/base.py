"""The base class every scope serializer subclasses.

Separate from the lookup in this package's ``__init__``, the way
:mod:`pas.plugins.identity.core.drivers.base` is separate from the driver
registry: a downstream package imports the class and never the lookup, and a
caller asking which scopes exist imports the lookup and never the class.
"""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.server.interfaces import IScopeSerializer
from plone.base.interfaces import IPloneSiteRoot
from zope.component import adapter
from zope.interface import implementer
from zope.publisher.interfaces.browser import IBrowserRequest


@implementer(IScopeSerializer)
@adapter(IPloneSiteRoot, IBrowserRequest)
class ScopeSerializer:
    """Base class for the serializer of one scope.

    Subclass it, declare :attr:`claims`, and implement :meth:`__call__`. A
    downstream package subclasses one of the shipped serializers instead and
    calls ``super().__call__(user)``, which is the same shape a
    ``plone.restapi`` serializer is extended in.

    **Why the site and not the user.** Adapting the user would read naturally
    for the values and then fail the three callers that need scope and claim
    *names* with nobody signed in: ``scopes_supported`` and
    ``claims_supported`` in the discovery document, which is published to an
    unauthenticated caller, and the consent screen, which lists what a scope
    releases before anybody has agreed to it. Adapting the site keeps one
    registration answering both questions -- the declaration is a class
    attribute, and the user is an argument to the call.

    The request is in the signature for the other half of that: it is what
    lets a policy package register for its own browser layer, which is more
    specific than the ``IBrowserRequest`` this package registers for and
    therefore wins with no ``overrides.zcml``.
    """

    #: The claim names this scope releases. See
    #: :class:`~pas.plugins.identity.server.interfaces.IScopeSerializer`: this
    #: is read with no user in hand and must not depend on who is signing in.
    claims: tuple[str, ...] = ()

    def __init__(self, context, request):
        """Adapt the site and the request.

        :param context: The Plone site.
        :param request: The current request.
        """
        self.context = context
        self.request = request

    def __call__(self, user) -> JSONDict:
        """Return this scope's claims for one user.

        :param user: The Plone user the token acts for.
        :returns: Claim name to value. Empty here: a base class that released
            something would put it in every scope that forgot to override.
        """
        return {}
