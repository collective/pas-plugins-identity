"""Take a site to profile version 1009.

``image_scales`` is Plone's own metadata column: the image fields an object
holds, with their scales. The identity catalog now carries it too. ``@users``
serializes every user it lists, and it used to wake each one's Profile to learn
two things: its URL and whether it had a picture. A brain answers the first,
and this column answers the second, so a listing no longer loads every Profile
it returns. The indexer is the one ``Products.CMFPlone`` registers for all
Dexterity content, so declaring the column is all it takes to fill it.

The column is created by re-importing the ``identity-catalog`` step, then
filled by reindexing every Profile, as
:mod:`~pas.plugins.identity.upgrades.v1008` did. Filling it is not optional:
read as ``Missing.Value`` the column says "no picture", and every Profile
picture would disappear from ``@users`` and from the ``picture`` claim until
that Profile's next write.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.setuphandlers import rebuild_catalog
from plone import api
from Products.GenericSetup.tool import SetupTool


#: The profile the step re-imports from.
PROFILE = "profile-pas.plugins.identity:default"


def add_image_scales_column(context: SetupTool) -> None:
    """Create the ``image_scales`` column and fill it for every Profile.

    :param context: The setup tool running the upgrade.
    """
    setup = api.portal.get_tool("portal_setup")
    setup.runImportStepFromProfile(PROFILE, "identity-catalog")
    rebuild_catalog(context)
    logger.info("Added the image_scales column and reindexed every Profile")
