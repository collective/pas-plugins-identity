"""``PATCH @identity-providers`` -- reorder them all, or update one in place."""

from pas.plugins.identity.core.controlpanel import check_address_preference
from pas.plugins.identity.core.controlpanel import check_propertymap
from pas.plugins.identity.core.controlpanel import check_signin_policy
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel import InvalidAddressPreference
from pas.plugins.identity.core.controlpanel import InvalidColor
from pas.plugins.identity.core.controlpanel import InvalidPropertyMap
from pas.plugins.identity.core.controlpanel import InvalidSignInPolicy
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.controlpanel import unmask
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.services.providers import ProvidersService
from pas.plugins.identity.core.utils.svg import InvalidSVG
from plone.restapi.deserializer import json_body


def _order_problems(order: list[str], configured: list[str]) -> list[str]:
    """Say what stops a list of ids being an order for the configured providers.

    :param order: The provider ids, in the order asked for.
    :param configured: The id of every configured provider.
    :returns: One sentence per kind of problem, naming the ids involved; empty
        when the list names each configured provider exactly once.
    """
    named = set(order)
    found = (
        ("Missing", [pid for pid in configured if pid not in named]),
        ("Not configured", sorted(named - set(configured))),
        ("Named more than once", sorted(p for p in named if order.count(p) > 1)),
    )
    return [f"{label}: {', '.join(map(repr, ids))}" for label, ids in found if ids]


class ProvidersPatch(ProvidersService):
    """Reorder the providers, or apply a partial update to one of them."""

    def reply(self) -> JSONDict:
        """Reorder the providers, or apply a partial update to one.

        :returns: No content on success, or an error body.
        """
        refusal = self._refuse_unless_manager()
        if refusal is not None:
            return refusal
        self._disable_csrf()

        if not self.segments:
            return self._reorder(json_body(self.request))
        if len(self.segments) != 1:
            return self._error(
                400,
                "Bad request",
                "Expected @identity-providers or @identity-providers/<id>",
            )
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

    def _reorder(self, data: JSONDict) -> JSONDict:
        """Store every provider in the order given.

        One request for the whole list, rather than an ``order`` written to
        each provider in turn, so a reorder cannot be left half applied. The
        list must name each configured provider exactly once: a provider it
        leaves out has no position to take, and one it names twice has two.

        :param data: The request body, ``{"order": [<provider id>, ...]}``.
        :returns: No content on success, or an error body.
        """
        # ``json_body`` has already refused a body that is not an object.
        order = data.get("order")
        if not isinstance(order, list) or not all(isinstance(p, str) for p in order):
            return self._error(
                400, "Bad request", 'Expected {"order": [<provider id>, ...]}'
            )
        providers = {provider.provider_id: provider for provider in get_providers()}
        problems = _order_problems(order, list(providers))
        if problems:
            return self._error(400, "Invalid order", "; ".join(problems))
        set_providers([providers[provider_id] for provider_id in order])
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
            # Checked here rather than left to the registry, which refuses the
            # same map without naming the row or the alternatives.
            try:
                check_propertymap(data["propertymap"] or {})
            except InvalidPropertyMap as error:
                return self._error(400, "Invalid property map", str(error))
            target.propertymap = dict(data["propertymap"] or {})
        if "groupmap" in data:
            target.groupmap = dict(data["groupmap"] or {})
        if "config" in data:
            return self._apply_config(target, data["config"])
        return None

    def _apply_config(self, target, config: JSONDict) -> JSONDict | None:
        """Apply the driver settings, refusing a configuration that cannot work.

        :param target: The provider being updated.
        :param config: The driver settings as supplied.
        :returns: An error body, or ``None`` when the settings applied.
        """
        # A round trip echoes the mask back, and that must not overwrite the
        # stored secret with a row of bullets.
        merged = unmask(target.driver_id, config, target.config)
        try:
            check_signin_policy(merged)
            check_address_preference(merged)
        except InvalidSignInPolicy as error:
            return self._error(400, "Nobody could sign in", str(error))
        except InvalidAddressPreference as error:
            return self._error(400, "Invalid address preference", str(error))
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
