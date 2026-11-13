"""What the ``personal_tools`` actions need to know about the current user.

An action's expressions run in restricted Python, which cannot import this
package's helpers, and the one fact the menu turns on -- where the user's
profile is -- depends on whether the site keeps its users as content. This
view answers it for an expression to read as ``portal/@@identity-profile-url``.
"""

from pas.plugins.identity.core.principal_types import users_as_content
from pas.plugins.identity.core.profiles import profile_brain
from plone import api
from Products.Five.browser import BrowserView


#: Where Volto edits the signed-in user's own properties.
PERSONAL_INFORMATION = "personal-information"


class IdentityProfileUrl(BrowserView):
    """The URL of the current user's own profile."""

    def __call__(self) -> str:
        """Return the URL of the current user's profile.

        * Anonymous: empty, so an ``available_expr`` can test it for truth.
        * On a site that keeps its users as content: the user's Profile, or
          empty for a user who has none. The ``profile`` action is offered to
          that user instead.
        * On any other site: Volto's own personal information form, which is
          where that user's properties are kept. The ``profile`` action then
          stands aside, so the menu has one entry for the profile either way.

        Only ever the caller's own URL, which the ``@users`` payload already
        hands them as ``profile_url``.

        :returns: The URL, or an empty string.
        """
        if api.user.is_anonymous():
            return ""
        if not users_as_content():
            return f"{api.portal.get().absolute_url()}/{PERSONAL_INFORMATION}"
        brain = profile_brain(api.user.get_current().getId())
        return brain.getURL() if brain is not None else ""
