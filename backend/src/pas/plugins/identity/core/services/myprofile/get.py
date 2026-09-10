"""``GET @my-profile`` -- the endpoint.

The body it answers with is :func:`~.profile_state`, which this module shares
with :mod:`.expander`. What is here is the endpoint's own concern: refusing an
anonymous caller with a JSON body rather than a login form.
"""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.services.base import IdentityService
from pas.plugins.identity.core.services.myprofile import profile_state
from plone import api


class MyProfileGet(IdentityService):
    """Report the caller's own Profile."""

    def reply(self) -> JSONDict:
        """Return the caller's Profile URL and workflow state.

        :returns: The body, or an error body.
        """
        if api.user.is_anonymous():
            return self._error(401, "Not authenticated", "Log in first.")

        return profile_state(
            api.user.get_current().getId(),
            self.context.absolute_url(),
        )


__all__ = ["MyProfileGet"]
