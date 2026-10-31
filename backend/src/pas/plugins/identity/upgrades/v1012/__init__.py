"""Take a site to profile version 1012.

``client_ip_headers`` is a setting on :class:`IIdentitySettings`. Its registry
record is created by
:func:`~pas.plugins.identity.setuphandlers.register_settings`, which keeps the
value of every record already there. Re-importing the registry step would not:
the default profile states values of its own, and importing it puts each back
over whatever the site chose.

The record starts empty on an upgraded site too. Which headers can be believed
depends on the proxies in front of it, and only its operator knows those.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.controlpanel.interfaces import IIdentitySettings
from pas.plugins.identity.setuphandlers import register_settings
from Products.GenericSetup.tool import SetupTool


def add_client_ip_headers(context: SetupTool) -> None:
    """Create the record naming the client address headers.

    :param context: The setup tool running the upgrade.
    """
    register_settings(IIdentitySettings)
    logger.info("Added the client_ip_headers setting")
