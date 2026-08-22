"""Fixtures for the flow-layer tests.

No provider and no portal: the flow manager takes a plain dict as its session
and provider metadata as an argument, which is what lets the whole security
surface be tested without Dex running.
"""

from . import DEX_PROVIDER
from . import PORTAL_URL
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.flows import FlowManager

import pytest


@pytest.fixture
def session() -> dict:
    """Return an empty session mapping.

    :returns: The session.
    """
    return {}


@pytest.fixture
def manager(session: dict) -> FlowManager:
    """Return a flow manager bound to an empty session.

    :param session: The session mapping.
    :returns: The manager.
    """
    return FlowManager(session, PORTAL_URL)


@pytest.fixture
def provider() -> ProviderConfig:
    """Return the Dex provider configuration.

    :returns: The provider.
    """
    return ProviderConfig.deserialize(DEX_PROVIDER)
