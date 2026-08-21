"""``@identities`` -- see, link and unlink your own external identities (Gate 2).

Three shapes:

``GET @identities``
    List the identities the authenticated user owns.

``POST @identities`` with ``{"provider": "<id>"}``
    Start a linking flow and answer with the authorize URL. The attempt
    remembers whose account it is linking to, and the callback refuses to
    complete it as anybody else (S1).

``DELETE @identities/<provider>/<subject>``
    Unlink, unless it is the user's last way in (S4).

Every one of them is about *your own* account. There is no shape here that
takes a userid: an administrator repairing someone else's identities is a
different feature with a different permission, and conflating the two is how
an ordinary user ends up able to attach their provider account to somebody
else's login.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.controlpanel import get_callback_url
from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.flows import FlowManager
from pas.plugins.identity.core.flows.metadata import metadata_for
from pas.plugins.identity.core.flows.session import FlowSession
from pas.plugins.identity.core.interfaces import FlowError
from pas.plugins.identity.core.interfaces import LockoutRefused
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.core.services.base import IdentityService
from plone import api
from plone.restapi.deserializer import json_body
from typing import Any
from zope.interface import implementer
from zope.publisher.interfaces import IPublishTraverse

import plone.protect.interfaces


@implementer(IPublishTraverse)
class IdentitiesBase(IdentityService):
    """Shared plumbing for the three ``@identities`` shapes.

    plone.rest registers one factory per HTTP method, so the verbs are three
    classes rather than three branches.
    """

    def __init__(self, context: Any, request: Any) -> None:
        """Bind the service and prepare to consume path segments.

        :param context: The context the service was traversed on.
        :param request: The current request.
        """
        super().__init__(context, request)
        self.segments: list[str] = []

    def publishTraverse(self, request: Any, name: str) -> "IdentitiesBase":
        """Collect ``<provider>`` and ``<subject>`` from the URL.

        :param request: The current request.
        :param name: The next path segment.
        :returns: This service.
        """
        self.segments.append(name)
        return self

    # ------------------------------------------------------------------
    # Shared
    # ------------------------------------------------------------------

    def _userid(self) -> str | None:
        """Return the authenticated userid.

        :returns: The userid, or ``None`` when nobody is logged in.
        """
        user = api.user.get_current()
        return None if api.user.is_anonymous() else user.getId()

    def _plugin(self) -> Any:
        """Return the identity plugin.

        :returns: The plugin installed in this site.
        """
        return api.portal.get_tool("acl_users")[PLUGIN_ID]

    def _disable_csrf(self) -> None:
        """Exempt a write from plone.protect's form authenticator.

        Volto sends a token, not a Plone form token. The request is
        authenticated and the action only ever touches the caller's own
        account, which is what makes this safe to do here.
        """
        from zope.interface import alsoProvides

        alsoProvides(self.request, plone.protect.interfaces.IDisableCSRFProtection)


class IdentitiesGet(IdentitiesBase):
    """``GET @identities`` -- what the caller has linked."""

    def reply(self) -> dict[str, Any]:
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
                # S4, surfaced so the UI can grey out the button rather than
                # let the user discover the refusal by pressing it.
                "can_unlink": plugin.can_unlink(
                    userid, record.provider, record.subject
                ),
            })
        return {"@id": base, "items": items}


class IdentitiesPost(IdentitiesBase):
    """``POST @identities`` -- start a linking flow."""

    def reply(self) -> dict[str, Any]:
        """Start a flow that will link a provider to the caller's account.

        :returns: The authorize URL, or an error body.
        """
        self._disable_csrf()
        userid = self._userid()
        if userid is None:
            # S1 -- a linking flow may not even be *started* anonymously.
            return self._error(401, "Not authenticated", "Log in first.")

        data = json_body(self.request)
        provider_id = data.get("provider")
        if not provider_id:
            return self._error(400, "Missing parameters", "Required: provider")

        provider = get_provider(provider_id)
        if provider is None or not provider.enabled or provider.driver is None:
            return self._error(404, "Unknown provider", repr(provider_id))

        try:
            manager = FlowManager(
                FlowSession(self.request), api.portal.get().absolute_url()
            )
            authorize_url = manager.start(
                provider,
                get_callback_url(),
                metadata_for(provider),
                came_from=data.get("came_from", ""),
                link_for=userid,
            )
        except FlowError as exc:
            logger.info("Refusing to start a link for %r: %s", provider_id, exc)
            return self._error(502, "Provider unavailable", str(exc))

        return {"provider": provider_id, "authorize_url": authorize_url}


class IdentitiesDelete(IdentitiesBase):
    """``DELETE @identities/<provider>/<subject>`` -- unlink."""

    def reply(self) -> dict[str, Any]:
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
            # S4 -- refusing here is the whole point.
            return self._error(409, "Would lock you out", str(exc))

        return self.reply_no_content()
