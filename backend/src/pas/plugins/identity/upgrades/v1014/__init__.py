"""Take a site to profile version 1014.

``default`` became two profiles, ``core`` and ``contenttypes``, and is now no
more than its dependencies on both. A site installed before that has every
part of both already: the plugins, the types, the catalog, the settings. What
it lacks is the record of having them -- GenericSetup has never heard of
either profile there -- and the marker that says users are content here.

So this step writes both, and imports nothing. Re-importing what the site
already holds would put each shipped value back over whatever the site chose.

Each profile is recorded at the version its own ``metadata.xml`` states, and
only where the site has no version for it yet: running the step twice, or on
a site that somehow already knows one of them, changes nothing.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.interfaces import IUsersAsContent
from pas.plugins.identity.setuphandlers import LAYER_PROFILES
from plone import api
from Products.GenericSetup.tool import SetupTool
from Products.GenericSetup.tool import UNKNOWN
from zope.interface import alsoProvides


def record_layer_profiles(context: SetupTool) -> None:
    """Record ``core`` and ``contenttypes`` as installed, and mark the site.

    :param context: The setup tool running the upgrade.
    """
    setup = api.portal.get_tool("portal_setup")
    for profile_id in LAYER_PROFILES:
        if setup.getLastVersionForProfile(profile_id) != UNKNOWN:
            continue
        version = setup.getVersionForProfile(profile_id)
        setup.setLastVersionForProfile(profile_id, version)
        logger.info("Recorded %s as installed at version %s", profile_id, version)
    alsoProvides(api.portal.get(), IUsersAsContent)
    logger.info("Marked the site as keeping its users as content")
