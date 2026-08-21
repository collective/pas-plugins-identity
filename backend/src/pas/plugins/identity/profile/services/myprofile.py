"""``@my-profile`` -- where the current user's Profile is, and how far along.

``GET @my-profile``
    ``{"profile": <url or null>, "review_state": <state or null>, "userid": …}``

Exists for one job: Volto's first-login routing. A user whose Profile is still
``incomplete`` should land on it and be asked to fill it in; a user whose
Profile is ``complete`` should go wherever they were heading. The frontend
cannot work that out from ``@userschema`` or ``@users/<id>``, because neither
knows anything about the workflow state of a piece of content.

Answered from the catalog, so the routing check every login performs costs no
object load (C6) -- the same discipline as the PAS plugin, for the same
reason.
"""

from pas.plugins.identity.core.services.base import IdentityService
from pas.plugins.identity.profile.catalog import query_catalog
from plone import api
from typing import Any


class MyProfileGet(IdentityService):
    """Report the caller's own Profile."""

    def reply(self) -> dict[str, Any]:
        """Return the caller's Profile URL and workflow state.

        :returns: The body, or an error body.
        """
        if api.user.is_anonymous():
            return self._error(401, "Not authenticated", "Log in first.")

        userid = api.user.get_current().getId()
        body: dict[str, Any] = {
            "@id": f"{self.context.absolute_url()}/@my-profile",
            "userid": userid,
            "profile": None,
            "review_state": None,
        }

        catalog = query_catalog()
        if catalog is None:
            # The layer is not installed in this site. Not an error: a
            # frontend that asks every site the same question deserves a
            # usable "there are no profiles here" rather than a 404 it has to
            # special-case.
            return body

        brains = catalog.unrestrictedSearchResults(userid=userid)
        if not brains:
            return body

        brain = brains[0]
        body["profile"] = brain.getURL()
        body["review_state"] = brain.review_state
        return body


__all__ = ["MyProfileGet"]
