"""``GET @identity-drivers`` -- what the control-panel widget renders."""

from pas.plugins.identity.core.drivers import all_drivers
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.services.providers import ControlPanelService


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
                    "schema": driver.config_schema(),
                    "default_propertymap": dict(driver.default_propertymap),
                }
                for _name, driver in sorted(all_drivers().items())
            ],
        }
