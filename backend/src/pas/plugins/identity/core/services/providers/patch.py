"""``PATCH @identity-providers/<id>`` -- update in place."""

from pas.plugins.identity.core.controlpanel import check_signin_policy
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel import InvalidColor
from pas.plugins.identity.core.controlpanel import InvalidSignInPolicy
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.controlpanel import unmask
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.services.providers import ProvidersService
from pas.plugins.identity.core.utils.svg import InvalidSVG
from plone.restapi.deserializer import json_body


class ProvidersPatch(ProvidersService):
    """Apply a partial update to one provider."""

    def reply(self) -> JSONDict:
        """Apply a partial update.

        :returns: No content on success, or an error body.
        """
        refusal = self._refuse_unless_manager()
        if refusal is not None:
            return refusal
        self._disable_csrf()

        if len(self.segments) != 1:
            return self._error(400, "Bad request", "Expected @identity-providers/<id>")
        providers = get_providers()
        target = next((p for p in providers if p.provider_id == self.segments[0]), None)
        if target is None:
            return self._error(404, "Unknown provider", repr(self.segments[0]))

        data = json_body(self.request)
        refusal = self._apply(target, data)
        if refusal is not None:
            return refusal

        set_providers(providers)
        return self.reply_no_content()

    def _apply(self, target, data: JSONDict) -> JSONDict | None:
        """Write the supplied fields onto one provider.

        Absent keys are left alone: this is a PATCH, and a control panel that
        edits one tab must not clear the others.

        :param target: The provider being updated.
        :param data: The request body.
        :returns: An error body, or ``None`` when everything applied.
        """
        if "title" in data:
            target.title = data["title"]
        if "enabled" in data:
            target.enabled = bool(data["enabled"])
        if "show_in_login" in data:
            target.show_in_login = bool(data["show_in_login"])
        refusal = self._apply_style(target, data)
        if refusal is not None:
            return refusal
        if "propertymap" in data:
            target.propertymap = dict(data["propertymap"] or {})
        if "groupmap" in data:
            target.groupmap = dict(data["groupmap"] or {})
        if "config" in data:
            # A round trip echoes the mask back, and that must not overwrite
            # the stored secret with a row of bullets.
            merged = unmask(target.driver_id, data["config"], target.config)
            try:
                check_signin_policy(merged)
            except InvalidSignInPolicy as error:
                return self._error(400, "Nobody could sign in", str(error))
            target.config = merged
        return None

    def _apply_style(self, target, data: JSONDict) -> JSONDict | None:
        """Apply the presentation fields, refusing anything unstorable.

        Refused rather than quietly emptied: an operator who pasted something
        unusable should find out here, not by looking at a login page that
        has no icon on it.

        :param target: The provider being updated.
        :param data: The request body.
        :returns: An error body, or ``None`` when everything applied.
        """
        try:
            if "icon" in data:
                target.icon = data["icon"] or ""
            if "background_color" in data:
                target.background_color = data["background_color"] or ""
            if "foreground_color" in data:
                target.foreground_color = data["foreground_color"] or ""
        except (InvalidSVG, InvalidColor) as error:
            return self._error(400, "Invalid style", str(error))
        return None
