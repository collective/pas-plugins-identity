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

from pas.plugins.identity.core.drivers import all_drivers
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.services.providers import ControlPanelService
from pas.plugins.identity.core.services.schema import jsonschema_for


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
                    "schema": jsonschema_for(
                        driver.settings_schema, self.context, self.request
                    ),
                    "supports_manual_link": driver.supports_manual_link,
                    "default_propertymap": dict(driver.default_propertymap),
                    "default_groupmap": dict(driver.default_groupmap),
                }
                for _name, driver in sorted(all_drivers().items())
            ],
        }


__all__ = ["DriversGet"]
