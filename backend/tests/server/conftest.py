"""Fixtures for the ``[server]`` extra.

The layer stores its clients in a registry record and nothing else, so there
is no content to create and no elevation needed: the tests here do not carry
the ``_manager`` workaround that ``tests/core/conftest.py`` documents.
"""

from pas.plugins.identity.server import clients as clients_module

import pytest


@pytest.fixture
def add_client(portal):
    """Return a factory registering a client.

    :param portal: The Plone site, so the registry is reachable.
    :returns: Callable with :func:`~pas.plugins.identity.server.clients.
        add_client`'s signature, returning ``(client, secret)``.
    """

    def factory(client_id: str = "test-client", **kwargs):
        return clients_module.add_client(client_id, **kwargs)

    return factory
