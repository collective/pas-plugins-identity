"""The self-Owner local role.

A user may edit their own Profile and nobody else's. Expressed as a local role
provider rather than as a local role *assignment* because the assignment would
have to be written at creation, kept in step with ``userid``, and migrated for
every Profile that predates a change of mind. The provider computes it, so it
is right by construction and there is nothing to drift.

``Owner`` rather than ``Editor``. Owner is what Plone means by "this object
is yours", and it is the role the Sharing tab, the ownership machinery and
every other add-on already understand -- Editor is a site role somebody may
also be granted globally, which would have made "may edit their own Profile"
indistinguishable from "is an editor of this site".

Owner carries more than Editor does, and the difference is not cosmetic.
Stock Plone grants Owner sixteen permissions with acquisition on, ``Delete
objects`` among them, and a user deleting their own Profile would leave an
account whose properties and enumeration stop working while the login keeps
succeeding. ``user_profile_workflow`` therefore *manages* every one of those
that matters and grants it to administrators only: deleting, adding content
inside somebody's profile, rewriting its view template, editing its ZODB
properties, opening it in the management screens. What Owner means on a
Profile is exactly what Editor meant, and the workflow is where that is
written down.
"""

from borg.localrole.interfaces import ILocalRoleProvider
from collections.abc import Iterator
from pas.plugins.identity.core.interfaces import IUserProfile
from pas.plugins.identity.core.profile import UserProfile
from zope.component import adapter
from zope.interface import implementer


#: The role a user gets on their own Profile.
SELF_ROLE = "Owner"


@implementer(ILocalRoleProvider)
@adapter(IUserProfile)
class ProfileSelfRole:
    """Grants ``Owner`` on a Profile to the user it belongs to."""

    def __init__(self, context: UserProfile) -> None:
        """Bind to the Profile.

        :param context: The Profile.
        """
        self.context = context

    def getRoles(self, principal_id: str) -> tuple[str, ...]:
        """Return the roles this principal has on the Profile.

        :param principal_id: A user or group id.
        :returns: ``("Owner",)`` for the Profile's own user, else empty.
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
