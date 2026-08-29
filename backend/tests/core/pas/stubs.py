"""A content type that is a user, a type that is a group, and something that can see them.

Core creates users and groups as content without knowing what type they are.
It deliberately does **not** enumerate them: answering "which users match
this?" without waking every object needs a catalog, and a catalog is what the
the profile plugin provides. One plugin creating and another enumerating
is the split, and it is not optional in either direction -- PAS looks a
principal straight back up after adding it, so creation with nothing to find
it afterwards fails at ``setMemberProperties`` rather than producing a user.

These stubs are the smallest thing that makes that pair whole, so a test can
exercise the real ``api.user.create`` path instead of calling ``doAddUser``
and hoping. They are stubs on purpose: using ``Profile`` would prove only
that core works with the one type this package ships.

The enumerator here scans its container, which is exactly what the shipped
layer must never do. That is fine for a handful of test objects and is the
reason core does not offer one.
"""

from AccessControl.class_init import InitializeClass
from pas.plugins.identity.core.interfaces import IGroupContent
from pas.plugins.identity.core.interfaces import IUserContent
from plone import api
from plone.dexterity.fti import DexterityFTI
from Products.PlonePAS.interfaces.group import IGroupIntrospection
from Products.PlonePAS.plugins.group import PloneGroup
from Products.PluggableAuthService.interfaces.plugins import IGroupEnumerationPlugin
from Products.PluggableAuthService.interfaces.plugins import IUserEnumerationPlugin
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements
from zope.interface import Interface


USER_TYPE = "StubUser"
GROUP_TYPE = "StubGroup"
NOT_A_USER = "StubDocument"
USERS = "people"
GROUPS = "teams"
STUB_PLUGIN_ID = "stub_content_principals"


class IStubUserSchema(IUserContent):
    """A schema that declares itself a user."""


class IStubGroupSchema(IGroupContent):
    """A schema that declares itself a group."""


class IStubDocumentSchema(Interface):
    """A schema that declares itself neither, so a refusal has a subject."""


class StubContentPrincipals(BasePlugin):
    """Enumerates the content objects core created, by scanning.

    The half core does not provide. Deliberately naive: correctness here is
    what lets a test assert on the real ``api.user.create`` path, and
    performance is the shipped layer's problem, solved with a catalog.
    """

    meta_type = "Stub Content Principals"

    def _objects(self, path: str, portal_type: str) -> list:
        """Return the content objects of one type in one container.

        :param path: Container path, relative to the site root.
        :param portal_type: The type to return.
        :returns: The matching objects.
        """
        portal = api.portal.get()
        container = portal.unrestrictedTraverse(path, None)
        if container is None:
            return []
        return [
            obj
            for obj in container.objectValues()
            if getattr(obj, "portal_type", None) == portal_type
        ]

    def enumerateUsers(
        self,
        id=None,
        login=None,
        exact_match=False,
        sort_by=None,
        max_results=None,
        **kw,
    ):
        """Answer PAS's user enumeration from the content objects.

        :param id: Userid to match.
        :param login: Login name to match.
        :param exact_match: Whether a match must be exact.
        :param sort_by: Ignored.
        :param max_results: Ignored.
        :param kw: Ignored.
        :returns: One record per matching user.
        """
        wanted = id or login
        results = []
        for obj in self._objects(USERS, USER_TYPE):
            userid = getattr(obj, "userid", None)
            if not userid:
                continue
            if wanted and (userid != wanted if exact_match else wanted not in userid):
                continue
            results.append({
                "id": userid,
                "login": getattr(obj, "login", userid),
                "pluginid": self.getId(),
            })
        return tuple(results)

    def enumerateGroups(
        self, id=None, exact_match=False, sort_by=None, max_results=None, **kw
    ):
        """Answer PAS's group enumeration from the content objects.

        :param id: Group id to match.
        :param exact_match: Whether a match must be exact.
        :param sort_by: Ignored.
        :param max_results: Ignored.
        :param kw: Ignored.
        :returns: One record per matching group.
        """
        results = []
        for obj in self._objects(GROUPS, GROUP_TYPE):
            group_id = getattr(obj, "group_id", None)
            if not group_id:
                continue
            if id and (group_id != id if exact_match else id not in group_id):
                continue
            results.append({
                "id": group_id,
                "title": obj.title,
                "pluginid": self.getId(),
            })
        return tuple(results)

    # -- IGroupIntrospection ----------------------------------------------
    #
    # Enumeration is not enough on the group side. PlonePAS looks a group
    # back up through ``getGroup``, which walks IGroupIntrospection and not
    # IGroupEnumerationPlugin, so without this ``addGroup`` succeeds and the
    # tool then falls over on ``setGroupProperties``.

    def getGroupById(self, group_id: str, default=None):
        """Return a decorated group, the way PlonePAS builds its own.

        :param group_id: The group id.
        :param default: Returned when there is no such group.
        :returns: The group, or ``default``.
        """
        if group_id not in self.getGroupIds():
            return default
        group = PloneGroup(group_id, group_id).__of__(self)
        group._addRoles(["Authenticated"])
        return group.__of__(self)

    def getGroupIds(self) -> list:
        """Return every group id, sorted so listings are stable.

        :returns: The ids.
        """
        return sorted(
            obj.group_id for obj in self._objects(GROUPS, GROUP_TYPE) if obj.group_id
        )

    def getGroups(self) -> list:
        """Return every group, decorated.

        :returns: The groups.
        """
        return [self.getGroupById(gid) for gid in self.getGroupIds()]

    def getGroupMembers(self, group_id: str) -> list:
        """Return the userids in a group.

        Read off each *user*, because that is where this design keeps
        membership.

        :param group_id: The group id.
        :returns: The userids.
        """
        return [
            obj.userid
            for obj in self._objects(USERS, USER_TYPE)
            if group_id in (getattr(obj, "group_ids", ()) or ())
        ]


classImplements(
    StubContentPrincipals,
    IUserEnumerationPlugin,
    IGroupEnumerationPlugin,
    IGroupIntrospection,
)

InitializeClass(StubContentPrincipals)


def add_type(portal, name: str, schema: str) -> None:
    """Register a Dexterity type in the test site.

    :param portal: The Plone site.
    :param name: Portal type id.
    :param schema: Dotted path of the schema interface.
    """
    fti = DexterityFTI(name)
    fti.klass = "plone.dexterity.content.Container"
    fti.schema = schema
    fti.global_allow = True
    fti.filter_content_types = False
    portal.portal_types._setObject(name, fti)


def install_enumerator(acl_users) -> None:
    """Register the stub enumerator, above the stock plugins.

    :param acl_users: The site's PAS instance.
    """
    if STUB_PLUGIN_ID not in acl_users:
        acl_users._setObject(STUB_PLUGIN_ID, StubContentPrincipals(STUB_PLUGIN_ID))
    plugins = acl_users.plugins
    for interface in (
        IUserEnumerationPlugin,
        IGroupEnumerationPlugin,
        IGroupIntrospection,
    ):
        if STUB_PLUGIN_ID not in plugins.listPluginIds(interface):
            plugins.activatePlugin(interface, STUB_PLUGIN_ID)
