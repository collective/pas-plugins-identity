"""Take a site to profile version 1005.

A group's global roles became a field, and a field that grants roles carries a
permission of its own. A permission is three writes rather than one: the
rolemap is the site-wide floor, the workflow decides who holds it in each
state, and **every group that already exists** carries a permission map
written when it was last transitioned.

Re-importing the workflow updates the definition and nothing else.
``updateRoleMappings`` is what carries the new permission map onto content
that already exists, and without it every group in the site keeps a map that
never mentions ``Edit Group Global Roles`` -- so the permission acquires from
the container, and the field's guard is whatever the folder happens to allow.

The ``typeinfo`` step is here for the other half: the behavior is listed on the
UserGroup FTI, and a site upgraded without re-importing it would have the
permission and no field to apply it to.
"""

from pas.plugins.identity import logger
from plone import api
from Products.GenericSetup.tool import SetupTool


#: The profile these steps re-import from.
PROFILE = "profile-pas.plugins.identity:default"


def restrict_group_roles(context: SetupTool) -> None:
    """Hold a group's global roles to ``Manager`` on groups that already exist.

    ``updateRoleMappings`` walks every object under every workflow and is the
    expensive part of this upgrade. It is also the whole point of it: the
    permission maps on existing groups are what decides who may grant a role
    on the groups a site already has.

    :param context: The setup tool running the upgrade.
    """
    setup = api.portal.get_tool("portal_setup")
    for step in ("rolemap", "workflow", "typeinfo"):
        setup.runImportStepFromProfile(PROFILE, step)

    # The workflow's new permission map reaches existing content only here.
    count = api.portal.get_tool("portal_workflow").updateRoleMappings()

    logger.info(
        "Restricted group global roles to Manager: updated %s object(s)",
        count,
    )
