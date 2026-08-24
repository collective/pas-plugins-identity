"""What ``@users`` says about a user, once this package is installed.

Three things a site with external identities needs and Plone has no place to
put: which identities a user has linked, which PAS plugin the userid actually
came from, and where the user's Profile lives when the ``[profile]`` layer is
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


def profile_url_of(userid: str) -> str | None:
    """Return the URL of a user's Profile, when there is one.

    :param userid: Canonical Plone userid.
    :returns: The absolute URL, or ``None`` when the ``[profile]`` layer is
        not installed or the user has no Profile yet.
    """
    try:
        from pas.plugins.identity.profile.subscribers import get_profile
    except ImportError:  # pragma: no cover - the extra is always importable
        return None
    profile = get_profile(userid)
    return profile.absolute_url() if profile is not None else None


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
        data["profile_url"] = profile_url_of(userid)
        return data
