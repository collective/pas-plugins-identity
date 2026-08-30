"""Fixtures shared across the core layer's tests."""

from .services import CALLBACK_URL
from .services import DEX_METADATA
from .services import DEX_PROVIDER
from .services import DISABLED_PROVIDER
from .services import USERINFO
from pas.plugins.identity.core.audit import AuditLog
from pas.plugins.identity.core.catalog import CATALOG_ID
from pas.plugins.identity.core.catalog import GROUP_PORTAL_TYPE
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.catalog import query_catalog
from pas.plugins.identity.core.container import get_container
from pas.plugins.identity.core.container import grant_add_permission
from pas.plugins.identity.core.container import GROUP
from pas.plugins.identity.core.container import PROFILE
from pas.plugins.identity.core.controlpanel import CALLBACK_URL_RECORD
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.flows.session import COOKIE_NAME
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.core.pas.profile import PLUGIN_ID as PROFILE_PLUGIN_ID
from plone import api
from plone.app.testing import login
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
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


#: Portal fixtures these autouse fixtures will bind to, in preference order.
#: Asked through ``request.fixturenames`` rather than declared as parameters,
#: because declaring one would *set up* that layer for every module here --
#: including the ones that run functionally, where a second layer coming up
#: beside theirs turns their first ``transaction.commit`` into
#: ``TestIsolationBroken``.
PORTAL_FIXTURES = ("portal", "portal_class")


def _portal_of(request):
    """Return the Plone site this test already asked for, if it asked.

    :param request: The test request.
    :returns: The portal, or ``None`` for a test that uses no portal fixture
        -- a functional module, or a unit test of a pure function.
    """
    for name in PORTAL_FIXTURES:
        if name in request.fixturenames:
            return request.getfixturevalue(name)
    return None


@pytest.fixture(autouse=True)
def _manager(request):
    """Run these tests as a site manager.

    Applying a GenericSetup profile is a manager's action -- this one creates
    the Profile container -- and ``@pytest.mark.portal`` applies profiles as
    whoever is logged in. Granting the role here rather than through the
    marker's own ``roles`` argument is deliberate: the marker grants roles
    *after* it applies profiles, which is too late to help the import step.

    .. warning::

       This fixture is now the *only* thing electing these tests, and the whole
       package leans on it: **75 explicit ``api.env.adopt_roles(["Manager"])``
       blocks** that used to double it up have been removed as redundant -- 27
       in one pass and 48 in another, the second measured by deleting all of
       them and watching 1582 tests still pass. It was introduced as a
       workaround for `plone/pytest-plone#63
       <https://github.com/plone/pytest-plone/issues/63>`_ and is marked for
       deletion once that lands -- but deleting it wholesale would now strip
       every test here of its role, not merely undo a workaround. When #63
       ships, replace this with the marker's own ``roles`` argument; do not
       simply drop it.

       Two elevations under ``tests/core`` survive on purpose, and neither is
       redundant with this: ``test_completeness.py`` adopts ``Anonymous``,
       which is the opposite of a grant, and ``test_email_linking.py`` runs as
       the ``member`` fixture rather than as ``TEST_USER_ID`` -- so the role
       granted here is not the role that request carries.

    .. warning::

       It reaches everything under ``tests/core``, which since the merge is
       most of the suite. A test asking whether an ordinary member is refused
       must therefore make a member of its own -- the ``member`` fixture --
       rather than logging in as the test user, which is a ``Manager`` here
       and would answer 200 to a question written to expect 403.

    :param request: The test request, read for whichever portal fixture the
        module already uses -- naming one here would tear a class-scoped
        layer down mid-class, or raise a functional module's layer beside the
        integration one.
    """
    portal = _portal_of(request)
    if portal is None:
        return
    setRoles(portal, TEST_USER_ID, ["Manager"])


@pytest.fixture(autouse=True)
def _profile_container(request, _manager):
    """Create the Profile container for the tests that expect one.

    Installing the add-on does not create it: where Profiles
    live is a registry setting, and a profile layered on top sets it after the
    install handler has run, so creating it eagerly created it under the wrong
    id. First login creates it instead.

    Almost every test here starts from "a site with somewhere to put a
    Profile", so the harness does what a first login would, rather than each
    module opening with the same two lines. A module that is testing the
    creation itself opts out with ``@pytest.mark.no_profile_container``.

    :param request: The test request, read for the opt-out marker and for
        whichever portal fixture the module already uses.
    :param _manager: Ensures the role is granted first.
    """
    if request.node.get_closest_marker("no_profile_container"):
        return
    if _portal_of(request) is None:
        return
    if query_catalog() is None:  # pragma: no cover - a site without the add-on
        return
    get_container(create=True)


@pytest.fixture
def catalog(portal):
    """The Profile catalog.

    :param portal: The Plone site.
    :returns: The catalog tool.
    """
    return api.portal.get_tool(CATALOG_ID)


@pytest.fixture
def profile_plugin(acl_users):
    """Return the profile PAS plugin.

    Named apart from ``plugin``, which is the identity plugin: two PAS
    plugins, two fixtures, and a test that asks for the wrong one fails
    loudly rather than asserting about the other.

    :param acl_users: The site's PAS instance.
    :returns: The plugin.
    """
    return acl_users[PROFILE_PLUGIN_ID]


@pytest.fixture
def allow_principals():
    """Return a callable making a folder accept Profiles and Groups.

    Both add permissions are granted to no role site-wide, so a folder that is
    not one of the configured containers refuses every ``UserProfile`` and
    ``UserGroup``. That is the lock, and this is the escape hatch it was
    designed to leave open: an operator who wants principals filed somewhere
    else grants the permission on the folder they chose.

    The tests that use this are about the catalog, the doctor or the indexing
    subscribers, none of which is about permissions. They need a second folder
    that principals may live in, which is what an operator would have made.

    :returns: Callable taking a folder and returning it, now permitted.
    """

    def grant(folder):
        for kind in (PROFILE, GROUP):
            grant_add_permission(folder, kind)
        return folder

    return grant


@pytest.fixture
def make_profile(portal):
    """Return a factory for Profiles in the configured container.

    :param portal: The Plone site.
    :returns: Callable taking a userid and extra field values.
    """

    def factory(userid: str, **kwargs) -> object:
        return api.content.create(
            container=kwargs.pop("container", portal["identity-profiles"]),
            type=PROFILE_PORTAL_TYPE,
            id=kwargs.pop("id", userid),
            userid=userid,
            login=kwargs.pop("login", f"{userid}@example.com"),
            **kwargs,
        )

    return factory


@pytest.fixture
def make_group(portal):
    """Return a factory for Group content.

    :param portal: The Plone site.
    :returns: Callable taking a group id and optional title.
    """

    def factory(group_id: str, title: str | None = None, **kwargs) -> object:
        return api.content.create(
            container=kwargs.pop("container", portal["identity-profiles"]),
            type=GROUP_PORTAL_TYPE,
            id=kwargs.pop("id", group_id),
            group_id=group_id,
            title=title or kwargs.pop("title", group_id.title()),
            **kwargs,
        )

    return factory
