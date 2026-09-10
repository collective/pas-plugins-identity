"""``@my-profile`` as a plone.restapi expandable component.

The profile gate asks this question on every navigation, and every navigation
to a content route is already a content request. Riding on it turns two round
trips into one, and the answer arrives exactly as fresh as the page it came
with -- which is what the gate needs, since saving the profile form is itself
a navigation.

**Absent for an anonymous caller, not an ``@id``.** Every other component in
this package follows the usual contract, where unexpanded costs a URL so a
client that did not ask still learns where to look. This one does not, and the
reason is the mechanism at the other end: Volto's ``apiExpanders`` has no
per-entry way to say *authenticated only* -- ``addExpandersToPath`` receives
``isAnonymous`` but the filter using it is a hardcoded list of ``types`` and
``translations`` -- so ``?expand=my-profile`` arrives on anonymous content
requests too. Publishing a URL that can only answer ``401`` would offer an
anonymous visitor a door that is never open, on every page of a public site.
Omitting the component keeps an anonymous content response byte-identical to
what it was before this existed.

A per-entry predicate for ``apiExpanders`` is proposed upstream as
plone/volto#8422. If it lands, what goes away is the wasted query parameter on
anonymous content URLs -- this rule stays either way, since a component with
nothing useful to say to an anonymous caller is right to say nothing.

**The ``@id`` is the site's, not the context's.** The endpoint is registered
``for="ISiteRoot"``, so ``/some/page/@my-profile`` does not resolve. An
expander that published ``self.context.absolute_url()`` -- which is what
copying the ``@login-providers`` component would give, since that one only
ever adapts the site root -- would hand out a 404 from every page but the
front one.
"""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.services.myprofile import profile_state
from pas.plugins.identity.core.services.myprofile import site_url
from plone import api
from plone.restapi.interfaces import IExpandableElement
from zope.component import adapter
from zope.interface import implementer
from zope.interface import Interface


@implementer(IExpandableElement)
@adapter(Interface, Interface)
class MyProfile:
    """Offer the caller's Profile state as ``my-profile``."""

    def __init__(self, context, request) -> None:
        """Bind the component.

        :param context: The content being served.
        :param request: The current request.
        """
        self.context = context
        self.request = request

    def __call__(self, expand: bool = False) -> JSONDict:
        """Render the component.

        :param expand: Whether the caller asked for the full answer.
        :returns: The component keyed by its own name, or an empty mapping
            for an anonymous caller.
        """
        if api.user.is_anonymous():
            return {}

        base = site_url()
        if not expand:
            return {"my-profile": {"@id": f"{base}/@my-profile"}}
        return {"my-profile": profile_state(api.user.get_current().getId(), base)}
