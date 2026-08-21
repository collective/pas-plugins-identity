"""Fixtures shared by the login-flow service tests."""

from . import CALLBACK_URL
from . import DEX_METADATA
from . import DEX_PROVIDER
from . import DISABLED_PROVIDER
from pas.plugins.identity.core.controlpanel import CALLBACK_URL_RECORD
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.flows.session import COOKIE_NAME
from plone import api
from typing import Any

import json
import pytest


@pytest.fixture()
def configured(portal):
    """Configure one enabled provider, one disabled, and the callback URL."""
    set_providers([
        ProviderConfig.deserialize(DEX_PROVIDER),
        ProviderConfig.deserialize(DISABLED_PROVIDER),
    ])
    api.portal.set_registry_record(CALLBACK_URL_RECORD, CALLBACK_URL)


@pytest.fixture()
def request_(portal):
    """Return the current request, carrying no flow cookie."""
    portal.REQUEST.cookies.pop(COOKIE_NAME, None)
    portal.REQUEST.form.clear()
    return portal.REQUEST


@pytest.fixture()
def stub_metadata(monkeypatch):
    """Replace metadata resolution so no test reaches the network.

    :returns: Callable taking the metadata to answer with, or an exception to
        raise instead.
    """

    def install(metadata: Any = None):
        """Install the stub in both service modules.

        :param metadata: Metadata to return, or an exception to raise.
            Defaults to the Dex fixture.
        """
        from pas.plugins.identity.core.services import callback as callback_module
        from pas.plugins.identity.core.services import login as login_module

        answer = DEX_METADATA if metadata is None else metadata

        def fake(provider):
            """Answer with the canned metadata.

            :param provider: Ignored.
            :returns: The metadata.
            :raises Exception: When the fixture was given one.
            """
            if isinstance(answer, Exception):
                raise answer
            return dict(answer)

        monkeypatch.setattr(login_module, "metadata_for", fake)
        monkeypatch.setattr(callback_module, "metadata_for", fake)

    return install


def body(request: Any, data: dict) -> None:
    """Put a JSON body on a request.

    :param request: The request to write to.
    :param data: The body payload.
    """
    request.set("BODY", json.dumps(data))
