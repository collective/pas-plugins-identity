"""Fixtures for the ``[server]`` extra.

The layer stores its clients in a registry record and nothing else, so there
is no content to create and no elevation needed: the tests here do not carry
the ``_manager`` workaround that ``tests/core/conftest.py`` documents.

What is here is what more than one module needs. A fixture used by a single
module stays in that module -- the point of this file is to stop the same
four lines being written eight times, not to collect every fixture in the
package.
"""

from . import ISSUER
from pas.plugins.identity.server.controlpanel import clients as clients_module
from pas.plugins.identity.server.grants.tokens import ISSUER_RECORD
from pas.plugins.identity.server.pas import PLUGIN_ID
from plone import api

import pytest


@pytest.fixture
def add_client(portal):
    """Return a factory registering a client.

    :param portal: The Plone site, so the registry is reachable.
    :returns: Callable with :func:`~pas.plugins.identity.server.controlpanel.clients.
        add_client`'s signature, returning ``(client, secret)``.
    """

    def factory(client_id: str = "test-client", **kwargs):
        return clients_module.add_client(client_id, **kwargs)

    return factory


@pytest.fixture
def issuer(portal) -> str:
    """Configure the issuer, without which nothing can be signed.

    :param portal: The Plone site, so the registry is reachable.
    :returns: The configured issuer.
    """
    api.portal.set_registry_record(ISSUER_RECORD, ISSUER)
    return ISSUER


@pytest.fixture
def plugin(acl_users):
    """Return the server PAS plugin, which holds every store this layer keeps.

    :param acl_users: The site's PAS instance.
    :returns: The plugin.
    """
    return acl_users[PLUGIN_ID]


@pytest.fixture
def userid() -> str:
    """Return the authenticated user's id.

    :returns: The current user's id.
    """
    return api.user.get_current().getId()
