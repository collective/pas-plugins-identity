"""``@my-profile`` -- where the current user's Profile is, and how far along.

``GET @my-profile``
    ``{"profile": <url or null>, "review_state": <state or null>,
    "userid": …, "missing": [<field names>],
    "emails": [{"address": …, "verified": …, "preferred": …}]}``

Exists for one job: Volto's first-login routing. A user whose Profile is still
``incomplete`` should land on it and be asked to fill it in; a user whose
Profile is ``complete`` should go wherever they were heading. The frontend
cannot work that out from ``@userschema`` or ``@users/<id>``, because neither
knows anything about the workflow state of a piece of content.

``missing`` names the required fields the profile has no value for, and is why
``review_state`` is ``incomplete``. The frontend gate asks on every page load
and has to be able to say what it wants: a user redirected to a form with no
reason given cannot tell a requirement from a broken site.

``emails`` is the addresses the profile carries, each with whether this site
has verified it and which one ``email`` therefore resolves to. It is what the
account page renders the verify buttons from, and what a page offering the
person a preferred address chooses between.

There used to be a second list beside it, ``email_choices``: the addresses a
provider had offered and nobody had picked between. There is nothing to pick
between any more -- every address a provider reports goes onto the profile,
and arranging them is the choice. See
:func:`~pas.plugins.identity.core.subscribers.sync_addresses`.

Answered from the catalog, so the routing check every login performs costs no
object load -- the same discipline as the PAS plugin, for the same reason, and
the reason ``missing`` and the addresses alike are read off the brain rather
than off the profile.
"""

from pas.plugins.identity.core.catalog import query_catalog
from pas.plugins.identity.core.completeness import missing_from_brain
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.services.base import IdentityService
from plone import api


class MyProfileGet(IdentityService):
    """Report the caller's own Profile."""

    def reply(self) -> JSONDict:
        """Return the caller's Profile URL and workflow state.

        :returns: The body, or an error body.
        """
        if api.user.is_anonymous():
            return self._error(401, "Not authenticated", "Log in first.")

        userid = api.user.get_current().getId()
        body: JSONDict = {
            "@id": f"{self.context.absolute_url()}/@my-profile",
            "userid": userid,
            "profile": None,
            "review_state": None,
            "missing": [],
            "emails": [],
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
        # Read off the same brain, so saying *what* is missing costs nothing
        # more than saying *that* something is. The frontend needs it to
        # explain itself: a user redirected to a form with no reason given
        # does not know whether the site is broken.
        body["missing"] = list(missing_from_brain(brain))
        body["emails"] = self._addresses(brain)
        return body

    @staticmethod
    def _addresses(brain) -> list[JSONDict]:
        """Render the profile's own addresses and their verification state.

        Off the brain, like everything else here: both lists are catalog
        metadata, and the one that changes without the profile being written
        -- ``verified_emails``, which a magic link updates through the
        identity store -- is reindexed by a subscriber for exactly that
        reason. See :mod:`pas.plugins.identity.core.emails`.

        :param brain: The Profile brain.
        :returns: One entry per address, in the person's own order.
        """
        verified = set(getattr(brain, "verified_emails", None) or ())
        preferred = getattr(brain, "email", "") or ""
        return [
            {
                "address": address,
                "verified": address in verified,
                # Which one ``email`` resolves to, so a page can mark it
                # rather than reimplement the rule that picks it.
                "preferred": address == preferred,
            }
            for address in getattr(brain, "emails", None) or ()
        ]


__all__ = ["MyProfileGet"]
