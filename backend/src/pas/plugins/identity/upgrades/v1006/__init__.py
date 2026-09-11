"""Take a site to profile version 1006.

Exporting providers became a permission of its own, because an export carries
every client secret in the clear. A permission declared in ZCML exists as soon
as the code does, registered with ``Manager`` and acquired from above the site.
The rolemap is what pins it to ``Manager`` with ``acquire="False"``, so the
answer does not depend on what the application root happens to grant, and
only re-importing the rolemap writes that onto a site installed before the
permission existed.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.services.providers import EXPORT_PERMISSION
from plone import api
from Products.GenericSetup.tool import SetupTool


#: The profile the step re-imports from.
PROFILE = "profile-pas.plugins.identity:default"


def restrict_provider_export(context: SetupTool) -> None:
    """Hold exporting providers to ``Manager``, without acquisition.

    :param context: The setup tool running the upgrade.
    """
    setup = api.portal.get_tool("portal_setup")
    setup.runImportStepFromProfile(PROFILE, "rolemap")
    logger.info("Held %r to Manager", EXPORT_PERMISSION)
