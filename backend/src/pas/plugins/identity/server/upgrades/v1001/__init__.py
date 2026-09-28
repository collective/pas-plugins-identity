"""Take a site to server profile version 1001.

A client registration gained ``allowed_groups``: the groups whose members may
authorize it. Every stored registration gets the key, empty, which admits
everybody, as every client did before.

The step edits the stored JSON rather than reading it through
:class:`~pas.plugins.identity.server.controlpanel.clients.ClientConfig`. The
model validates on assignment, and a registration stored before one of its
rules existed would stop the upgrade on a question this step is not asking.
A registration that already has the key keeps its value.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.server.controlpanel.clients import CLIENTS_RECORD
from plone import api
from Products.GenericSetup.tool import SetupTool

import json


def add_allowed_groups(context: SetupTool) -> None:
    """Write an empty ``allowed_groups`` into every stored client.

    :param context: The setup tool running the upgrade.
    """
    raw = api.portal.get_registry_record(CLIENTS_RECORD, default="") or ""
    if not raw:
        logger.info("No OAuth clients registered; nothing to upgrade")
        return
    entries = json.loads(raw)
    added = 0
    for entry in entries:
        if "allowed_groups" not in entry:
            entry["allowed_groups"] = []
            added += 1
    api.portal.set_registry_record(CLIENTS_RECORD, json.dumps(entries))
    logger.info("Added allowed_groups to %d of %d OAuth clients", added, len(entries))
