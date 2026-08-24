"""``GET @identities`` -- what the caller has linked."""

from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.services.identities import IdentitiesBase
from plone.restapi.serializer.expansion import expandable_elements


class IdentitiesGet(IdentitiesBase):
    """List the caller's own external identities."""

    def reply(self) -> JSONDict:
        """List the caller's identities.

        :returns: The listing, or an error body.
        """
        userid = self._userid()
        if userid is None:
            return self._error(401, "Not authenticated", "Log in first.")

        plugin = self._plugin()
        base = f"{self.context.absolute_url()}/@identities"
        items = []
        for record in plugin.store.identities_for(userid):
            provider = get_provider(record.provider)
            items.append({
                "@id": f"{base}/{record.provider}/{record.subject}",
                "provider": record.provider,
                "subject": record.subject,
                "title": provider.title if provider is not None else record.provider,
                "created": record.created.isoformat(),
                "last_login": (
                    record.last_login.isoformat() if record.last_login else None
                ),
                # Surfaced so the UI can grey out the button rather than let
                # the user discover the refusal by pressing it.
                "can_unlink": plugin.can_unlink(
                    userid, record.provider, record.subject
                ),
            })
        # The page that reads this also offers what is *not* linked yet, so
        # `?expand=login-providers` answers the whole screen in one request.
        return {
            "@id": base,
            "items": items,
            **expandable_elements(self.context, self.request),
        }
