"""Take a site to profile version 1002.

Two changes land together, and only one of them a re-import can carry.

The Profile's fields moved onto behaviors, which is the FTI's ``behaviors``
property and so exactly what re-importing ``typeinfo`` applies. That half is
declared in ``configure.zcml`` and needs no code.

The other half is a new field permission, and a permission is three writes
rather than one: the rolemap is the site-wide floor, the workflow decides who
holds it in each state, and **every Profile that already exists** carries a
permission map written when it was last transitioned. Importing a workflow
does not touch those --
:func:`Products.CMFCore.exportimport.workflow.importWorkflowTool` never calls
``updateRoleMappings`` -- so without this handler an upgraded site would leave
the new permission unmanaged on every existing Profile, and an unmanaged
permission is not one nobody holds: it is acquired from the container, which
is the one place this package grants it to Site Administrator as well.

The upgrade would then read as applied and change nothing.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.container import grant_add_permissions
from plone import api
from Products.GenericSetup.tool import SetupTool


#: The profile these steps re-import from.
PROFILE = "profile-pas.plugins.identity:default"


def restrict_login(context: SetupTool) -> None:
    """Hold a Profile's ``login`` to ``Manager`` once the account exists.

    Re-imports the two steps that declare the permission, then applies it to
    content that already exists and to the containers principals are filed in.

    ``updateRoleMappings`` walks every object under every workflow and is the
    expensive part of this upgrade. It is also the whole point of it: the
    permission maps on existing Profiles are what decides who may write a
    login on the accounts a site already has, which is every account it has.

    :param context: The setup tool running the upgrade.
    """
    setup = api.portal.get_tool("portal_setup")
    for step in ("rolemap", "workflow"):
        setup.runImportStepFromProfile(PROFILE, step)

    # The workflow's new permission map reaches existing content only here.
    count = api.portal.get_tool("portal_workflow").updateRoleMappings()

    # And the container is what keeps the field on the add form; see
    # ``core.container.LOGIN_ROLES``.
    containers = grant_add_permissions()

    logger.info(
        "Restricted Profile logins to Manager: updated %s object(s) and "
        "granted the permission on %s",
        count,
        ", ".join(containers) or "no container",
    )
