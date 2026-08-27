"""Patches applied to packages this one does not own.

One patch, applied by :mod:`pas.plugins.identity.core`. It is here rather
than fixed in place because the defect is in PlonePAS, and a site running
this package cannot delete a group until it is repaired.
"""

from AccessControl.requestmethod import postonly
from pas.plugins.identity import logger
from Products.PlonePAS.tools.groups import GroupsTool
from Products.PlonePAS.tools.groups import NotSupported
from Products.PluggableAuthService.events import GroupDeleted
from Products.PluggableAuthService.PluggableAuthService import (
    _SWALLOWABLE_PLUGIN_EXCEPTIONS,
)
from zope.event import notify


def removeGroup(self, group_id, REQUEST=None):
    """Remove a single group, tolerating a manager that never had it.

    Replaces :meth:`Products.PlonePAS.tools.groups.GroupsTool.removeGroup`,
    which loops every ``IGroupManagement`` plugin and lets whatever the last
    one raises escape.

    That loop is right -- a group id is not owned by one plugin, and the tool
    cannot know which of them holds it -- but the plugins it drives are not
    written to be asked about a group they do not have.
    ``ZODBGroupManager.removeGroup`` documents that it raises ``KeyError``
    for an unknown group and ends in a bare ``del self._groups[group_id]``,
    so on any site with a second group-management plugin the tool aborts the
    transaction. Ours deletes the content object, ``source_groups`` raises on
    the same id, and the successful delete rolls back with it: the caller
    sees a 503 and the group is still there.

    The repair is the idiom this same file already uses fifteen lines above,
    in ``addGroup``: swallow ``_SWALLOWABLE_PLUGIN_EXCEPTIONS`` per plugin and
    keep going. A plugin that declines by raising is then indistinguishable
    from one that declines by returning false, which is what the loop needed
    all along.

    ``NotSupported`` still propagates. A site with no group-management plugin
    at all is misconfigured rather than being asked about a group it lacks.

    :param self: The group tool.
    :param group_id: The group to remove.
    :param REQUEST: Present for ``postonly``; unused.
    :returns: Whether any plugin removed the group.
    """
    retval = False
    managers = self._getGroupManagers()
    if not managers:
        raise NotSupported("No plugins allow for group management")

    for mid, manager in managers:
        try:
            removed = manager.removeGroup(group_id)
        except _SWALLOWABLE_PLUGIN_EXCEPTIONS:
            logger.debug("Group manager %s declined to remove %r", mid, group_id)
            continue
        if removed:
            # Once per plugin that removed it, as upstream does. The event
            # carries only the id, so a listener cannot tell the difference
            # and deduplicating would change behavior no one asked about.
            notify(GroupDeleted(group_id))
            retval = True

    return retval


def apply_patches() -> None:
    """Install the patches.

    Called from :mod:`pas.plugins.identity.core`, which the layer's ZCML
    imports. Idempotent: reapplying it replaces the method with the same
    function.
    """
    # ``postonly`` is what upstream wraps the method in, and it is not
    # inherited by replacing the attribute. The security assertion is, since
    # ``ClassSecurityInfo`` maps the permission to the *name*.
    GroupsTool.removeGroup = postonly(removeGroup)
