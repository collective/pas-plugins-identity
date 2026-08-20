"""Fixtures reaching for what the portal marker created."""

from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.core.pas.plugin import IdentityPlugin

import pytest


@pytest.fixture()
def acl_users(portal):
    """Return the site's PAS instance."""
    return portal.acl_users


@pytest.fixture()
def plugin(acl_users) -> IdentityPlugin:
    """Return the installed identity plugin."""
    return acl_users[PLUGIN_ID]
