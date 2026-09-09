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
from pas.plugins.identity.server.interfaces import IScopeSerializer
from pas.plugins.identity.server.pas import PLUGIN_ID
from pas.plugins.identity.server.serializers import SERIALIZER_FOR
from pas.plugins.identity.server.serializers.base import ScopeSerializer
from plone import api
from zope.component import getGlobalSiteManager

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


@pytest.fixture
def register_scope(portal):
    """Return a factory registering a scope serializer, as an add-on would.

    The registration goes on the global site manager, which is where a
    downstream package's ``<adapter />`` lands.

    **It restores what it displaced.** Registering under a name already in use
    replaces that registration rather than shadowing it, so unregistering
    afterwards would leave the scope with no serializer at all -- and the
    shipped three are registered exactly that way, by this package's own ZCML.
    A test that overrode ``profile`` and tidied up after itself would silently
    switch that scope off for every test that ran later in the session, and
    the failure would land on one of those instead.

    :param portal: The Plone site, so there is something to adapt.
    :returns: Callable taking the scope name and either the claims and values
        to release or a ``factory`` class of the test's own, and returning the
        registered class.
    """
    required = SERIALIZER_FOR
    gsm = getGlobalSiteManager()
    undo = []

    def factory(
        name: str,
        claims: tuple = (),
        values: dict | None = None,
        factory: type | None = None,
    ):
        registered = factory
        if registered is None:
            released = dict(values or {})

            class registered(ScopeSerializer):
                """A scope registered by a test."""

            registered.claims = claims
            registered.__call__ = lambda self, user: dict(released)

        displaced = gsm.adapters.registered(required, IScopeSerializer, name)
        gsm.registerAdapter(registered, required, IScopeSerializer, name=name)
        undo.append((registered, name, displaced))
        return registered

    yield factory

    for registered, name, displaced in reversed(undo):
        gsm.unregisterAdapter(registered, required, IScopeSerializer, name=name)
        if displaced is not None:
            gsm.registerAdapter(displaced, required, IScopeSerializer, name=name)
