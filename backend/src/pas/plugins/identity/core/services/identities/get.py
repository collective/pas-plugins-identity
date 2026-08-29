"""``GET @identities`` -- what the caller has linked, and what they could."""

from pas.plugins.identity.core.controlpanel import enabled_providers
from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.services.identities import IdentitiesBase
from pas.plugins.identity.core.services.login import render_provider
from plone.restapi.serializer.expansion import expandable_elements


class IdentitiesGet(IdentitiesBase):
    """List the caller's own external identities."""

    def reply(self) -> JSONDict:
        """List the caller's identities, and the providers still on offer.

        ``available`` is the *enabled* providers rather than the ones the
        login screen shows. That is the difference the two settings exist
        for: a provider an operator has taken off the login page is still one
        a user may attach to an account they already have.

        Providers whose driver takes no link form are absent from it -- magic
        link, whose addresses come from the profile rather than from a box on
        this page. Identities already linked through them are still listed in
        ``items``, because seeing what is attached to your account is a
        different question from being offered another one.

        :returns: The listing, or an error body.
        """
        userid = self._userid()
        if userid is None:
            return self._error(401, "Not authenticated", "Log in first.")

        plugin = self._plugin()
        base = f"{self.context.absolute_url()}/@identities"
        items = []
        linked = set()
        for record in plugin.store.identities_for(userid):
            provider = get_provider(record.provider)
            linked.add(record.provider)
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
            "available": self._available(linked),
            **expandable_elements(self.context, self.request),
        }

    def _available(self, linked: set[str]) -> list[JSONDict]:
        """Return the providers this caller could still start a link against.

        A provider already linked is kept out of the list. One external
        account per provider per user is the model the store enforces -- the
        forward map is keyed on ``(provider, subject)`` and a second subject
        from the same provider would be a second way in that nothing here
        distinguishes -- so offering it again is offering something that
        cannot succeed.

        :param linked: Provider ids the caller already has an identity for.
        :returns: One entry per offerable provider, in stored order.
        """
        base = f"{self.context.absolute_url()}/@login-providers"
        return [
            render_provider(base, provider)
            for provider in enabled_providers()
            if provider.provider_id not in linked
            and provider.driver.supports_manual_link
        ]
