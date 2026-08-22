"""Fixtures for the migration tests."""

from pas.plugins.identity.core.pas import PLUGIN_ID

import pytest


@pytest.fixture
def store(acl_users):
    """Return this package's identity store.

    :param acl_users: The site's PAS instance.
    :returns: The store.
    """
    return acl_users[PLUGIN_ID].store
