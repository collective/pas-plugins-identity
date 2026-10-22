"""Take a site to profile version 1011.

The login and the group membership of a Profile are guarded by a permission of
their own, ``View Account Details``, apart from ``View Profile``. A permission
is three writes rather than one: the rolemap is the site-wide floor, the
workflow decides who holds it on a Profile in each state, and **every Profile
that already exists** carries a permission map written when it was last
transitioned.

Re-importing the workflow updates the definition and nothing else.
``updateRoleMappings`` is what carries the new permission map onto Profiles
that already exist. Without it the permission is unmanaged on every one of
them, so it acquires from the container, and the login and the groups a user
is in would be readable by whoever the container happens to allow, not by the
roles the workflow names.
"""

from pas.plugins.identity import logger
from plone import api
from Products.GenericSetup.tool import SetupTool


#: The profile these steps re-import from.
PROFILE = "profile-pas.plugins.identity:default"


def guard_account_details(context: SetupTool) -> None:
    """Map ``View Account Details`` onto every Profile already in the site.

    :param context: The setup tool running the upgrade.
    """
    setup = api.portal.get_tool("portal_setup")
    for step in ("rolemap", "workflow"):
        setup.runImportStepFromProfile(PROFILE, step)

    # The workflow's new permission map reaches existing Profiles only here.
    count = api.portal.get_tool("portal_workflow").updateRoleMappings()

    logger.info(
        "Guarded login and group membership: updated %s object(s)",
        count,
    )
