"""The authorization server's own configuration.

Its settings, its control panel entry, and the schema an OAuth client is
registered against. Grouped here for the reason the core layer's own
``controlpanel`` package exists: what an operator configures is one subject,
and it was spread across three files at the top level of ``server``.
"""

from pas.plugins.identity.server.controlpanel.panel import CONFIGLET_CATEGORY_ID
from pas.plugins.identity.server.controlpanel.panel import CONFIGLET_ID


__all__ = ["CONFIGLET_CATEGORY_ID", "CONFIGLET_ID"]
