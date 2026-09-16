"""Take a site to profile version 1008.

``missing_fields`` is a column in the identity catalog carrying what a Profile
is still waiting for, as the *object* counted it -- the only answer that knows
which of those fields their owner is allowed to write. ``@my-profile`` and the
Classic UI gate read it to explain a hold, and before it existed they explained
one by scanning columns for emptiness: a list that named fields the form does
not show the person being held, and named any required field that is not a
column at all however full it was.

Two things are needed and the second is the reason this is not
:mod:`~pas.plugins.identity.upgrades.v1007` again.

The column is created by re-importing the ``identity-catalog`` step, which is
additive and leaves every other index and column alone.

Then every Profile is reindexed, and here ``Missing.Value`` is *not* the right
answer for an existing one. A new column reads that way until something indexes
into it, and :func:`~pas.plugins.identity.core.completeness.missing_from_brain`
treats it as "not asked yet" and falls back to the old scan -- correct, and
still the behaviour being fixed. So the upgrade populates it rather than
waiting for each Profile's next write, which for a site whose users are all
complete would be never.

The rebuild is the ``rebuild-catalog`` profile's, reused rather than repeated:
it is the same operation an operator runs after any drift, and this is drift
with a version number on it.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.setuphandlers import rebuild_catalog
from plone import api
from Products.GenericSetup.tool import SetupTool


#: The profile the step re-imports from.
PROFILE = "profile-pas.plugins.identity:default"


def add_missing_fields_column(context: SetupTool) -> None:
    """Create the ``missing_fields`` column and fill it for every Profile.

    :param context: The setup tool running the upgrade.
    """
    setup = api.portal.get_tool("portal_setup")
    setup.runImportStepFromProfile(PROFILE, "identity-catalog")
    rebuild_catalog(context)
    logger.info("Added the missing_fields column and reindexed every Profile")
