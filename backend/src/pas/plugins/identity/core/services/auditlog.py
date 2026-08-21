"""``@audit-log`` -- read the authentication event log (§4.6, Gate 4).

``GET @audit-log``
    Your own entries.

``GET @audit-log?userid=<id>``
    Somebody else's. Managers only.

``GET @audit-log?scope=site``
    Everything, including the refusals that could not be attributed to
    anybody -- which is the view an operator investigating an attack wants.
    Managers only.

The default is deliberately the narrow one. A log that shows the whole site
to whoever asks is a list of who has accounts and when they signed in.
"""

from pas.plugins.identity.core.interfaces import IAuditSink
from pas.plugins.identity.core.services.base import IdentityService
from plone import api
from typing import Any
from zope.component import queryUtility


#: Permission a caller needs to read beyond their own entries.
MANAGE_PERMISSION = "Manage portal"

#: How many entries are returned when the caller does not say.
DEFAULT_LIMIT = 100

#: Ceiling on ``limit``. The log is bounded per user, but a site-wide read on
#: a busy site is still worth capping.
MAX_LIMIT = 500


class AuditLogGet(IdentityService):
    """Read authentication events."""

    def reply(self) -> dict[str, Any]:
        """Return the entries the caller is allowed to see.

        :returns: The listing, or an error body.
        """
        if api.user.is_anonymous():
            return self._error(401, "Not authenticated", "Log in first.")
        caller = api.user.get_current().getId()

        sink = queryUtility(IAuditSink, default=None)
        if sink is None:
            # A site that unregistered the sink has no log to read, which is
            # a configuration answer rather than an error.
            return {"@id": self._base(), "items": [], "scope": "none"}

        scope = self.request.form.get("scope", "")
        requested = self.request.form.get("userid", "")

        if scope == "site" or (requested and requested != caller):
            if not api.user.has_permission(MANAGE_PERMISSION):
                # Not 404: the caller knows perfectly well the log exists,
                # having just been told they may read their own.
                return self._error(
                    403,
                    "Not allowed",
                    "Reading another user's authentication log needs "
                    f"the {MANAGE_PERMISSION!r} permission.",
                )
            userid = None if scope == "site" else requested
        else:
            userid = caller

        entries = sink.entries(userid)
        return {
            "@id": self._base(),
            "scope": "site" if userid is None else userid,
            "items_total": len(entries),
            "items": [entry.serialize() for entry in entries[: self._limit()]],
        }

    def _base(self) -> str:
        """Return this service's canonical URL.

        :returns: The URL.
        """
        return f"{self.context.absolute_url()}/@audit-log"

    def _limit(self) -> int:
        """Return how many entries to render.

        :returns: The limit, clamped to :data:`MAX_LIMIT`.
        """
        try:
            limit = int(self.request.form.get("limit", DEFAULT_LIMIT))
        except (TypeError, ValueError):
            return DEFAULT_LIMIT
        if limit <= 0:
            return DEFAULT_LIMIT
        return min(limit, MAX_LIMIT)
