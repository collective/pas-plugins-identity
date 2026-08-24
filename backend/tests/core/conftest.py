"""Fixtures shared across the core layer's tests."""

from .services import CALLBACK_URL
from .services import DEX_METADATA
from .services import DEX_PROVIDER
from .services import DISABLED_PROVIDER
from .services import USERINFO
from pas.plugins.identity.core.audit import AuditLog
from pas.plugins.identity.core.controlpanel import CALLBACK_URL_RECORD
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.flows.session import COOKIE_NAME
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.pas import PLUGIN_ID
from plone import api
from plone.app.testing import login
from zope.component import adapter
from zope.component import getGlobalSiteManager
from zope.interface import Interface

import pytest


@pytest.fixture
def plugin(portal):
    """Return the installed identity plugin.

    :param portal: The Plone site, so this binds to whichever one the
        requesting module provides.
    :returns: The plugin.
    """
    return api.portal.get_tool("acl_users")[PLUGIN_ID]


@pytest.fixture
def log(portal) -> AuditLog:
    """Return the installed plugin's audit log, emptied.

    Resolves whichever ``portal`` the requesting module provides, so a module
    that shadows it with a class-scoped one still gets a log bound to that.

    :param portal: The Plone site.
    :returns: The identity plugin's audit log.
    """
    plugin = api.portal.get_tool("acl_users")[PLUGIN_ID]
    plugin.audit._by_userid.clear()
    return plugin.audit


@pytest.fixture
def request_(portal):
    """Return the current request, carrying no flow cookie."""
    portal.REQUEST.cookies.pop(COOKIE_NAME, None)
    portal.REQUEST.form.clear()
    return portal.REQUEST


@pytest.fixture
def stub_metadata(monkeypatch):
    """Replace metadata resolution so no test reaches the network.

    :returns: Callable taking the metadata to answer with, or an exception to
        raise instead.
    """

    def install(metadata: JSONDict | Exception | None = None):
        """Install the stub in both service modules.

        :param metadata: Metadata to return, or an exception to raise.
            Defaults to the Dex fixture.
        """
        from pas.plugins.identity.core.flows import metadata as metadata_module
        from pas.plugins.identity.core.services.callback import post as callback_module
        from pas.plugins.identity.core.services.identities import (
            post as identities_module,
        )
        from pas.plugins.identity.core.services.login import get as login_module

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
        monkeypatch.setattr(identities_module, "metadata_for", fake)
        # providers.py reaches through the module rather than importing the
        # name, so patching the importers is not enough for it.
        monkeypatch.setattr(metadata_module, "metadata_for", fake)

    return install


@pytest.fixture
def stub_provider(monkeypatch):
    """Replace the provider's token and userinfo endpoints.

    :returns: Callable taking the userinfo payload to answer with.
    """

    class StubResponse:
        """The part of ``requests.Response`` the userinfo call touches."""

        def __init__(self, payload: dict) -> None:
            """Hold a canned payload.

            :param payload: What :meth:`json` returns.
            """
            self.payload = payload

        def raise_for_status(self) -> None:
            """Succeed: this stub stands in for a healthy provider."""

        def json(self) -> dict:
            """Return the canned payload.

            :returns: The payload.
            """
            return dict(self.payload)

    def install(userinfo: dict | None = None):
        """Install the stub.

        :param userinfo: What the userinfo endpoint answers; the recorded
            Dex payload when omitted.
        """
        payload = USERINFO if userinfo is None else userinfo
        from authlib.integrations.requests_client import OAuth2Session
        from pas.plugins.identity.core import flows

        class StubSession(OAuth2Session):
            """authlib's client with the network calls short-circuited."""

            def fetch_token(self, url: str, **kwargs) -> dict:
                """Answer the token request.

                :param url: Ignored.
                :param kwargs: Ignored.
                :returns: A token with no ``id_token``.
                """
                return {"access_token": "at", "token_type": "Bearer"}

            def get(self, url: str, **kwargs) -> StubResponse:
                """Answer the userinfo request.

                :param url: Ignored.
                :param kwargs: Ignored.
                :returns: The canned response.
                """
                return StubResponse(payload)

        monkeypatch.setattr(flows, "OAuth2Session", StubSession)

    return install


@pytest.fixture
def configured(portal):
    """Configure one enabled provider, one disabled, and the callback URL.

    :param portal: The Plone site.
    """
    set_providers([
        ProviderConfig.deserialize(DEX_PROVIDER),
        ProviderConfig.deserialize(DISABLED_PROVIDER),
    ])
    api.portal.set_registry_record(CALLBACK_URL_RECORD, CALLBACK_URL)


@pytest.fixture
def recorded_events():
    """Record every event fired during a test.

    :returns: The list the recorder appends to.
    """
    events = []

    @adapter(Interface)
    def recorder(event):
        events.append(event)

    gsm = getGlobalSiteManager()
    gsm.registerHandler(recorder)
    yield events
    gsm.unregisterHandler(recorder)


@pytest.fixture
def member(portal) -> str:
    """Create and log in an ordinary member.

    :param portal: The Plone site.
    :returns: The member's userid.
    """
    with api.env.adopt_roles(["Manager"]):
        user = api.user.create(
            email="member@plone.org",
            username="member",
            password="s3cr3t-member",
        )
    login(portal, "member")
    return user.getId()
