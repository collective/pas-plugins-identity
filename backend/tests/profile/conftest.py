"""Fixtures for the ``[profile]`` extra.

The profile is applied per test module through ``@pytest.mark.portal`` on the
ordinary integration layer, rather than from a second ``PloneSandboxLayer``.
That is not the obvious choice, so it is worth writing down why:
``pytest_plone``'s ``fixtures_factory`` keeps every layer it is given set up
for the whole session, and two sandbox layers kept up at once end up sharing
one site, with whichever was set up last deciding what is installed in it. The
visible symptom was the *magic-link* tests failing on a missing MockMailHost
-- a suite that has nothing to do with profiles, on a layer that never
mentions them.

Applying the profile inside the test keeps the core layer honestly core: every
test outside this package still runs against a site where the extra was never
installed, which is what makes the "core installs alone" invariant something
the suite proves rather than something it assumes. Integration testing rolls
the transaction back afterwards, so the site is clean again for the next test.

The marker rather than a fixture that shadows ``portal``: a shadowing fixture
applies to everything under this directory whether a module wants it or not,
which is how ``test_not_installed`` ended up needing a second fixture to opt
back out. With the marker the default is a plain site, and a module that needs
the extra says so at the top.
"""

from pas.plugins.identity.profile.catalog import CATALOG_ID
from pas.plugins.identity.profile.catalog import GROUP_PORTAL_TYPE
from pas.plugins.identity.profile.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.profile.catalog import query_catalog
from pas.plugins.identity.profile.container import get_container
from pas.plugins.identity.profile.pas import PLUGIN_ID
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID

import pytest


@pytest.fixture(autouse=True)
def _manager(integration):
    """Run these tests as a site manager.

    Applying a GenericSetup profile is a manager's action -- this one creates
    the Profile container -- and ``@pytest.mark.portal`` applies profiles as
    whoever is logged in. Granting the role here rather than through the
    marker's own ``roles`` argument is deliberate: the marker grants roles
    *after* it applies profiles, which is too late to help the import step.

    .. warning::

       This fixture is now the *only* thing electing these tests, and the whole
       package leans on it: the 27 explicit ``api.env.adopt_roles(["Manager"])``
       blocks that used to double it up have been removed as redundant. It was
       introduced as a workaround for `plone/pytest-plone#63
       <https://github.com/plone/pytest-plone/issues/63>`_ and is marked for
       deletion once that lands -- but deleting it wholesale would now strip
       every test here of its role, not merely undo a workaround. When #63
       ships, replace this with the marker's own ``roles`` argument; do not
       simply drop it.

    :param integration: The integration layer.
    """
    setRoles(integration["portal"], TEST_USER_ID, ["Manager"])


@pytest.fixture(autouse=True)
def _profile_container(request, portal, _manager):
    """Create the Profile container for the tests that expect one.

    Installing the ``[profile]`` profile no longer creates it: where Profiles
    live is a registry setting, and a profile layered on top sets it after the
    install handler has run, so creating it eagerly created it under the wrong
    id. First login creates it instead.

    Almost every test here starts from "a site with somewhere to put a
    Profile", so the harness does what a first login would, rather than each
    module opening with the same two lines. A module that is testing the
    creation itself opts out with ``@pytest.mark.no_profile_container``.

    :param request: The test request, read for the opt-out marker.
    :param portal: The Plone site.
    :param _manager: Ensures the role is granted first.
    """
    if request.node.get_closest_marker("no_profile_container"):
        return
    if query_catalog() is None:
        # The layer is not installed in this site; there is no Profile type
        # to make a container for. ``test_not_installed`` lives here.
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
def plugin(acl_users):
    """Return the profile PAS plugin.

    :param acl_users: The site's PAS instance.
    :returns: The plugin.
    """
    return acl_users[PLUGIN_ID]


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
