"""``POST @confirm-email`` -- which verified address stands for the caller.

``{"email": "<address>"}``
    Answers the question ``@my-profile`` reports as ``confirm_email``: the
    address moves to the front of the caller's addresses, the Profile stops
    waiting, and the body is the caller's ``@my-profile`` as it is now.

Only ever the caller's own Profile, so the body takes no userid.

The refusals, in the order they are checked:

``401``
    Anonymous.
``404``
    The caller has no Profile.
``400``
    No address in the body.
``409``
    The Profile is not waiting on a confirmation. The endpoint is the answer
    to a question, not a second way to reorder addresses: that is a ``PATCH``
    on the Profile.
``400``
    The address is not one of the Profile's verified addresses.
"""

from pas.plugins.identity.core.confirmation import confirm
from pas.plugins.identity.core.confirmation import NotAVerifiedAddress
from pas.plugins.identity.core.confirmation import NothingToConfirm
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.profiles import get_profile
from pas.plugins.identity.core.services.base import IdentityService
from pas.plugins.identity.core.services.myprofile import profile_state
from plone import api
from plone.restapi.deserializer import json_body
from zope.interface import alsoProvides

import plone.protect.interfaces


class ConfirmEmailPost(IdentityService):
    """Record which verified address stands for the caller."""

    def reply(self) -> JSONDict:
        """Confirm one of the caller's verified addresses.

        :returns: The caller's ``@my-profile`` body, or an error body.
        """
        # Volto sends a token rather than a Plone form token, the request is
        # authenticated, and it only ever writes the caller's own Profile.
        alsoProvides(self.request, plone.protect.interfaces.IDisableCSRFProtection)

        if api.user.is_anonymous():
            return self._error(401, "Not authenticated", "Log in first.")
        userid = api.user.get_current().getId()

        profile = get_profile(userid)
        if profile is None:
            return self._error(404, "No profile", "This user has no profile.")

        address = json_body(self.request).get("email")
        if not isinstance(address, str) or not address.strip():
            return self._error(400, "Missing parameters", "Required: email")

        try:
            # Elevated: the write ends in a modification event, and
            # autoversioning answers that with a save the owner may not be
            # allowed to make. Whose Profile it is was settled above.
            with api.env.adopt_roles(["Manager"]):
                confirm(profile, address)
        except NothingToConfirm:
            return self._error(
                409, "Nothing to confirm", "This profile is not waiting on one."
            )
        except NotAVerifiedAddress:
            return self._error(
                400,
                "Not a verified address",
                "Choose one of the verified addresses on your profile.",
            )

        return profile_state(userid, self.context.absolute_url())


__all__ = ["ConfirmEmailPost"]
