"""``DELETE @identities/<provider>/<subject>`` -- unlink."""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.interfaces import LockoutRefused
from pas.plugins.identity.core.services.identities import IdentitiesBase


class IdentitiesDelete(IdentitiesBase):
    """Remove one of the caller's own external identities."""

    def reply(self) -> JSONDict:
        """Unlink one of the caller's identities.

        :returns: An empty body on success, or an error body.
        """
        self._disable_csrf()
        userid = self._userid()
        if userid is None:
            return self._error(401, "Not authenticated", "Log in first.")

        if len(self.segments) != 2:
            return self._error(
                400,
                "Missing parameters",
                "Expected @identities/<provider>/<subject>",
            )
        provider_id, subject = self.segments

        try:
            self._plugin().unlink(userid, provider_id, subject)
        except KeyError:
            # Unknown, and owned-by-someone-else, answer identically: whose
            # account an identity belongs to is not worth probing for.
            return self._error(404, "Unknown identity", f"{provider_id}:{subject}")
        except LockoutRefused as exc:
            # Refusing here is the whole point.
            return self._error(409, "Would lock you out", str(exc))

        return self.reply_no_content()
