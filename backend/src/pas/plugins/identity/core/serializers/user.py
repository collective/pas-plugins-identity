"""What ``@users`` says about a user, once this package is installed.

Three things a site with external identities needs and Plone has no place to
put: which identities a user has linked, which PAS plugin the userid actually
came from, and where the user's Profile lives when they have one, are
installed.

**How the source is decided.** PAS stamps it. ``searchUsers`` aggregates the
registered enumeration plugins and returns a record carrying ``pluginid``,
which is the plugin that answered -- so this reads an answer rather than
deriving one. Iterating ``IUserEnumerationPlugin`` by hand would reimplement
that aggregation, and the acquisition parent of a user object is no help at
all: ``api.user.get`` hands back a ``MemberData`` whose ``aq_parent`` is
``None``, wrapping a ``PloneUser`` that carries no plugin on its chain.

``exact_match=True`` is not optional. ``searchUsers(id=...)`` is a substring
search, so ``alice`` would otherwise also match ``alice2`` and the source
reported would be whichever record came back first.
"""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.core.portraits import picture_url
from pas.plugins.identity.core.profiles import get_profile
from pas.plugins.identity.interfaces import IBrowserLayer
from plone import api
from plone.restapi.interfaces import ISerializeToJson
from plone.restapi.serializer.user import SerializeUserToJson
from Products.CMFCore.interfaces._tools import IMemberData
from zope.component import adapter
from zope.interface import implementer


def source_of(userid: str) -> str | None:
    """Return the id of the PAS plugin a userid came from.

    :param userid: Canonical Plone userid.
    :returns: The plugin id, or ``None`` when no plugin claims the userid.
    """
    acl = api.portal.get_tool("acl_users")
    for record in acl.searchUsers(id=userid, exact_match=True):
        # The first record is the one PAS itself resolved to; a second would
        # mean two plugins both claim the userid, which is a broken site
        # rather than something to report per-plugin here.
        return record.get("pluginid")
    return None


def identities_of(userid: str) -> list[JSONDict]:
    """Return the external identities linked to a userid.

    :param userid: Canonical Plone userid.
    :returns: One entry per linked identity, oldest first as stored.
    """
    acl = api.portal.get_tool("acl_users")
    plugin = getattr(acl, PLUGIN_ID, None)
    if plugin is None:
        # The core plugin is what stores identities; without it there are
        # none rather than an error. A site can have this package's code on
        # the path without its profile applied.
        return []
    return [
        {
            "provider": record.provider,
            "subject": record.subject,
            "created": record.created.isoformat(),
            "last_login": (
                record.last_login.isoformat() if record.last_login else None
            ),
        }
        for record in plugin.store.identities_for(userid)
    ]


@implementer(ISerializeToJson)
@adapter(IMemberData, IBrowserLayer)
class SerializeIdentityUserToJson(SerializeUserToJson):
    """``@users`` plus what this package knows about the user."""

    def __call__(self) -> JSONDict:
        """Serialize the user.

        :returns: The default payload, with the identity fields added.
        """
        data = super().__call__()
        userid = self.context.getUserId()
        data["source"] = source_of(userid)
        data["identities"] = identities_of(userid)
        profile = get_profile(userid)
        data["profile_url"] = profile.absolute_url() if profile is not None else None
        # The Profile's own picture wins over the member portrait: a picture on
        # the Profile is one somebody chose and uploaded, while the member
        # portrait is where a provider-synced avatar lands, and a claim a
        # provider supplied should not overwrite a decision a person made.
        #
        # Set only when there is one. `portrait` already holds the member
        # portrait, and overwriting it with `None` would take away the
        # provider-synced avatar this is meant to take precedence over.
        picture = picture_url(userid)
        if picture is not None:
            data["portrait"] = picture
        return data
