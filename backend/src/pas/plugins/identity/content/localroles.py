"""The self-Editor local role.

A user may edit their own Profile and nobody else's. Expressed as a local role
provider rather than as a local role *assignment* because the assignment would
have to be written at creation, kept in step with ``userid``, and migrated for
every Profile that predates a change of mind. The provider computes it, so it
is right by construction and there is nothing to drift.

``Editor`` rather than ``Owner``: Owner in Plone carries "may delete", and a
user deleting their own Profile would leave an account whose properties and
enumeration silently stop working while the login keeps succeeding.
"""

from borg.localrole.interfaces import ILocalRoleProvider
from collections.abc import Iterator
from pas.plugins.identity.content.interfaces import IUserProfile
from pas.plugins.identity.content.profile import UserProfile
from zope.component import adapter
from zope.interface import implementer


#: The role a user gets on their own Profile.
SELF_ROLE = "Editor"


@implementer(ILocalRoleProvider)
@adapter(IUserProfile)
class ProfileSelfRole:
    """Grants ``Editor`` on a Profile to the user it belongs to."""

    def __init__(self, context: UserProfile) -> None:
        """Bind to the Profile.

        :param context: The Profile.
        """
        self.context = context

    def getRoles(self, principal_id: str) -> tuple[str, ...]:
        """Return the roles this principal has on the Profile.

        :param principal_id: A user or group id.
        :returns: ``("Editor",)`` for the Profile's own user, else empty.
        """
        userid = getattr(self.context, "userid", None)
        if userid and principal_id == userid:
            return (SELF_ROLE,)
        return ()

    def getAllRoles(self) -> Iterator[tuple[str, tuple[str, ...]]]:
        """Yield every principal/roles pair on the Profile.

        Used by the Sharing tab to show what is already granted.

        :returns: Iterator of ``(principal_id, roles)``.
        """
        userid = getattr(self.context, "userid", None)
        if userid:
            yield (userid, (SELF_ROLE,))


__all__ = ["SELF_ROLE", "ProfileSelfRole"]
