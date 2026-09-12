"""``GET @identity-drivers`` -- what a provider form is built from.

Each driver's ``settings_schema`` is serialized here with ``plone.restapi``'s
own schema machinery -- the same three calls that answer ``@controlpanels`` --
so what a client receives is an ordinary JSON schema: ``properties``,
``required``, ``fieldsets``, widgets, vocabularies, and titles already
translated into the request's language.

This used to hand over ``driver.config_schema()``, a dict this package built
by hand, and the Volto add-on turned that into a form schema in 529 lines of
its own. Nothing about a provider form is special enough to deserve a second
schema language; see :mod:`pas.plugins.identity.core.drivers.settings`.
"""

from pas.plugins.identity.core.controlpanel import driver_defaults
from pas.plugins.identity.core.drivers import all_drivers
from pas.plugins.identity.core.drivers.base import BaseDriver
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.services.providers import ControlPanelService
from pas.plugins.identity.core.services.schema import jsonschema_for


def _schema_with_defaults(driver: BaseDriver, context, request) -> JSONDict:
    """Serialize a driver's settings schema, showing what it will actually store.

    The schema's own ``default`` is what the *field* declares, and for the
    settings a driver has an opinion about that is the wrong number: ``scope``
    declares an empty tuple because no single default suits every OAuth2
    provider, and Google's own ``("openid", "email", "profile")`` lives on the
    driver class. Volto seeds an add form from ``properties[*].default``, so
    without this overlay the operator reads an empty scope box and an unticked
    ``trust_email_verification``, then saves a provider that has both.

    Laid over the serialized schema rather than pushed down into the fields,
    because the fields are shared: ``IOAuth2Settings.scope`` is the same field
    object for every driver that inherits it, and giving it Google's default
    would give it to GitHub too.

    :func:`~pas.plugins.identity.core.controlpanel.driver_defaults` is the
    source, which is the point: the form and the record are then filled from
    one function and cannot drift apart.

    :param driver: The driver whose settings schema to render.
    :param context: Context to build the form against.
    :param request: The current request, deciding the language.
    :returns: The JSON schema, with the driver's own defaults in place.
    """
    schema = jsonschema_for(driver.settings_schema, context, request)
    properties = schema.get("properties", {})

    for name, value in driver_defaults(driver).items():
        if name not in properties:
            # A default for a setting this driver's schema does not declare.
            # `driver_defaults` already gates the two optional ones, so this is
            # a driver whose class and schema disagree rather than a normal
            # case -- and inventing the property here would put a field on the
            # form that nothing can store.
            continue
        properties[name]["default"] = value

    # Every collection default, not only the ones overlaid above: a `Tuple`
    # field's default is a Python tuple, and `plone.restapi` passes it through
    # as one. It reaches the client as an array regardless, because the JSON
    # encoder coerces it -- so the only symptom is on this side, where anything
    # comparing the served default against a list finds them unequal. Said once
    # here rather than at each call: what leaves this endpoint is JSON, and
    # JSON has one sequence type.
    for property_ in properties.values():
        if isinstance(property_.get("default"), tuple):
            property_["default"] = list(property_["default"])

    return schema


class DriversGet(ControlPanelService):
    """Describe every registered driver."""

    def reply(self) -> JSONDict:
        """Describe every registered driver.

        :returns: The listing, or an error body.
        """
        refusal = self._refuse_unless_manager()
        if refusal is not None:
            return refusal

        return {
            "@id": f"{self.context.absolute_url()}/@identity-drivers",
            "items": [
                {
                    "id": driver.driver_id,
                    "title": driver.title,
                    # What a provider of this driver is drawn with until
                    # it has an icon of its own, so the form can show it.
                    "default_icon": driver.default_icon,
                    "schema": _schema_with_defaults(driver, self.context, self.request),
                    "supports_manual_link": driver.supports_manual_link,
                    "default_propertymap": dict(driver.default_propertymap),
                    "default_groupmap": dict(driver.default_groupmap),
                }
                for _name, driver in sorted(all_drivers().items())
            ],
        }


__all__ = ["DriversGet"]
