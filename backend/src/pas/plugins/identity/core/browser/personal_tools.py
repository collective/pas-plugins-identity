"""What the ``personal_tools`` actions need to know about the current user.

An action's expressions run in restricted Python, which cannot import this
package's helpers, and the one fact the menu turns on -- whether the user has
a Profile -- lives in the identity catalog. This view answers it for an
expression to read as ``portal/@@identity-profile-url``.
"""

from pas.plugins.identity.core.profiles import profile_brain
from plone import api
from Products.Five.browser import BrowserView


class IdentityProfileUrl(BrowserView):
    """The URL of the current user's own Profile."""

    def __call__(self) -> str:
        """Return the current user's Profile URL.

        Empty for anonymous and for a user without a Profile, so an
        ``available_expr`` can test it for truth. Only ever the caller's own
        URL, which the ``@users`` payload already hands them as
        ``profile_url``.

        :returns: The URL, or an empty string.
        """
        if api.user.is_anonymous():
            return ""
        brain = profile_brain(api.user.get_current().getId())
        return brain.getURL() if brain is not None else ""
