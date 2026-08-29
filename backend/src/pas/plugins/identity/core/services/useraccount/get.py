"""``GET @user-account/<userid>`` -- one person's identities and last login."""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.services.base import IdentityService
from pas.plugins.identity.core.services.useraccount import audit_entries
from pas.plugins.identity.core.services.useraccount import DEFAULT_EVENTS
from pas.plugins.identity.core.services.useraccount import identity_plugin
from pas.plugins.identity.core.services.useraccount import last_authenticated
from pas.plugins.identity.core.services.useraccount import MANAGE_PERMISSION
from pas.plugins.identity.core.services.useraccount import MAX_EVENTS
from pas.plugins.identity.core.services.useraccount import render_identity
from pas.plugins.identity.core.subscribers import profile_url
from plone import api
from Products.CMFPlone.Portal import PloneSite
from zope.interface import implementer
from zope.publisher.interfaces import IPublishTraverse
from ZPublisher.HTTPRequest import HTTPRequest


@implementer(IPublishTraverse)
class UserAccountGet(IdentityService):
    """Report how one user gets in, and when they last did."""

    def __init__(self, context: PloneSite, request: HTTPRequest) -> None:
        """Bind the service and prepare to consume a path segment.

        :param context: The context the service was traversed on.
        :param request: The current request.
        """
        super().__init__(context, request)
        self.segments: list[str] = []

    def publishTraverse(self, request: HTTPRequest, name: str) -> "UserAccountGet":
        """Collect ``<userid>`` from the URL.

        :param request: The current request.
        :param name: The next path segment.
        :returns: This service.
        """
        self.segments.append(name)
        return self

    def reply(self) -> JSONDict:
        """Report one user's identities, addresses and authentication history.

        :returns: The body, or an error body.
        """
        if api.user.is_anonymous():
            return self._error(401, "Not authenticated", "Log in first.")
        if len(self.segments) != 1:
            return self._error(400, "Bad request", "Expected @user-account/<userid>")
        userid = self.segments[0]

        refusal = self._refuse_unless_allowed(userid)
        if refusal is not None:
            return refusal

        user = api.user.get(userid=userid)
        if user is None:
            return self._error(404, "Unknown user", repr(userid))

        entries = audit_entries(userid)
        plugin = identity_plugin()
        records = plugin.store.identities_for(userid) if plugin is not None else ()
        return {
            "@id": f"{self.context.absolute_url()}/@user-account/{userid}",
            "userid": userid,
            "fullname": user.getProperty("fullname", "") or "",
            "profile_url": profile_url(userid),
            "identities": [render_identity(record) for record in records],
            "emails": self._addresses(userid),
            "last_authenticated": last_authenticated(entries),
            "events_total": len(entries),
            "events": [entry.serialize() for entry in entries[: self._limit()]],
        }

    def _limit(self) -> int:
        """Return how many recent events to include.

        :returns: The count, clamped to :data:`MAX_EVENTS`.
        """
        try:
            requested = int(self.request.form.get("events", DEFAULT_EVENTS))
        except (TypeError, ValueError):
            # A query string is whatever somebody typed; a bad one gets the
            # default rather than a 400 about a field nobody meant to send.
            return DEFAULT_EVENTS
        return max(0, min(requested, MAX_EVENTS))

    def _addresses(self, userid: str) -> list[JSONDict]:
        """Return the user's addresses and which of them are verified.

        Which addresses an account can be reached and matched on is part of
        the same question as which providers it uses -- a verified address is
        what ``auto_link_by_email`` attaches a new provider account to, so an
        administrator looking at one is looking at the other.

        :param userid: Canonical Plone userid.
        :returns: One entry per address, in the person's own order.
        """
        from pas.plugins.identity.core.catalog import query_catalog

        catalog = query_catalog()
        if catalog is None:
            return []
        brains = catalog.unrestrictedSearchResults(userid=userid)
        if not brains:
            return []
        brain = brains[0]
        verified = set(getattr(brain, "verified_emails", None) or ())
        preferred = getattr(brain, "email", "") or ""
        return [
            {
                "address": address,
                "verified": address in verified,
                "preferred": address == preferred,
            }
            for address in getattr(brain, "emails", None) or ()
        ]

    def _refuse_unless_allowed(self, userid: str) -> JSONDict | None:
        """Return an error body unless the caller may read this account.

        :param userid: The account being read.
        :returns: The error body, or ``None`` when the caller is allowed.
        """
        if api.user.has_permission(MANAGE_PERMISSION):
            return None
        if api.user.get_current().getId() == userid:
            # The same facts are already theirs through @identities and
            # @audit-log; refusing here would only mean the frontend needing
            # two code paths to draw one panel.
            return None
        return self._error(
            403,
            "Not allowed",
            f"Reading another user's account needs the {MANAGE_PERMISSION!r} "
            "permission.",
        )
