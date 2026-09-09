"""One row of ``@group-members``, and the place to add a field to it.

A membership row is built from a catalog brain and from nothing else. That is
the endpoint's whole premise -- a group of a thousand members must not become a
thousand object loads to draw one page of it -- and it is easy to lose, because
losing it looks like calling a helper that takes a userid.

It had been lost. The row filled ``profile_url`` by calling
``profile_url(brain.userid)``, which searches the catalog a second time and
then wakes the object to ask for its URL, once per person on the page. A brain
already knows its own URL, so :meth:`GroupMemberSerializer.__call__` asks it.
"""

from pas.plugins.identity.core.interfaces import IGroupMemberSerializer
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.interfaces import IBrowserLayer
from Products.CMFCore.interfaces import ISiteRoot
from Products.ZCatalog.CatalogBrains import AbstractCatalogBrain
from zope.component import adapter
from zope.interface import implementer


@implementer(IGroupMemberSerializer)
@adapter(ISiteRoot, IBrowserLayer)
class GroupMemberSerializer:
    """Render a Profile brain as a membership row.

    Adapts the site rather than the brain, for the reason set out on
    :class:`~pas.plugins.identity.core.interfaces.IGroupMemberSerializer`: a
    brain cannot be marked, and the only registration a brain could carry
    would answer for every brain in the site.
    """

    def __init__(self, context: ISiteRoot, request: IBrowserLayer) -> None:
        """Bind the serializer.

        :param context: The site the listing was asked of.
        :param request: The current request.
        """
        self.context = context
        self.request = request

    def __call__(self, brain: AbstractCatalogBrain) -> JSONDict:
        """Render one member.

        :param brain: A Profile brain from this package's catalog.
        :returns: JSON-ready mapping. Enough to draw a row and to follow
            through to the person; no address, because a membership listing is
            not a directory of contact details.
        """
        url = brain.getURL()
        return {
            # The person's Profile. It used to be the listing's own URL with
            # the userid appended, which is not a resource: the service takes
            # exactly one path segment, so following it answered 400.
            "@id": url,
            "id": brain.userid,
            "fullname": brain.fullname or brain.login or brain.userid,
            "login": brain.login,
            # The same URL as ``@id`` now, and kept because clients written
            # against the broken ``@id`` were told to use this one.
            "profile_url": url,
            # Which groups this person is actually in. A page listing an outer
            # group's people can then say where each of them came from, rather
            # than presenting one flat list nobody can account for.
            "through": sorted(getattr(brain, "group_ids", None) or ()),
        }
