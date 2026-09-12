"""Take a site to profile version 1007.

Asking a person with several verified addresses which one stands for them
needs two things a site installed before it does not have.

``confirm_email_at_first_login`` is a setting on :class:`IProfileSettings`.
Its registry record is created by
:func:`~pas.plugins.identity.setuphandlers.register_settings`, which keeps the
value of every record already there and resets to its default only a value
that no longer validates against its field. Re-importing the registry step
would not keep them: the default profile states values of its own, and
importing it puts each back over whatever the site chose.

``email_confirmation_pending`` is a column in the identity catalog, created by
re-importing the ``identity-catalog`` step. Nothing is reindexed. A brain reads
a column no object has been indexed into as ``Missing.Value``, which is false,
and that is the right answer for every Profile: none can be waiting on a
confirmation from before the setting existed.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.controlpanel.interfaces import IProfileSettings
from pas.plugins.identity.setuphandlers import register_settings
from plone import api
from Products.GenericSetup.tool import SetupTool


#: The profile the step re-imports from.
PROFILE = "profile-pas.plugins.identity:default"


def add_email_confirmation(context: SetupTool) -> None:
    """Create the confirmation setting's record and its catalog column.

    :param context: The setup tool running the upgrade.
    """
    register_settings(IProfileSettings)
    setup = api.portal.get_tool("portal_setup")
    setup.runImportStepFromProfile(PROFILE, "identity-catalog")
    logger.info(
        "Added the confirm_email_at_first_login setting and the "
        "email_confirmation_pending column"
    )
