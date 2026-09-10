"""Fixtures for the façade's own tests.

``tests/core/conftest.py`` grants the Manager role and creates the Profile
container for everything beneath it, and a sibling package does not inherit
either. Rather than reach across, this package states the two things it needs
for itself -- which also keeps these tests honest about what the façade
requires of a site.
"""

from pas.plugins.identity.core.catalog import query_catalog
from pas.plugins.identity.core.container import get_container
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID

import pytest


@pytest.fixture(autouse=True)
def _manager(portal):
    """Run these tests as a site manager.

    :param portal: The Plone site.
    """
    setRoles(portal, TEST_USER_ID, ["Manager"])


@pytest.fixture(autouse=True)
def _profile_container(portal, _manager):
    """Give the site somewhere to file a Profile.

    Installing the add-on does not create the container -- where Profiles live
    is a registry setting, and first login creates it. These tests start from
    a site that has one.

    :param portal: The Plone site.
    :param _manager: Ensures the role is granted first.
    """
    if query_catalog() is None:  # pragma: no cover - a site without the add-on
        return
    get_container(create=True)


@pytest.fixture
def configured_provider(portal) -> str:
    """Register one provider and return its id.

    Built here rather than borrowed from the core suite's ``configured``
    fixture, because these tests care about one provider being findable
    through the façade rather than about the fixture's enabled/disabled pair.

    :param portal: The Plone site.
    :returns: The provider id.
    """
    from pas.plugins.identity.core.controlpanel import ProviderConfig
    from pas.plugins.identity.core.controlpanel import set_providers

    set_providers([ProviderConfig(provider_id="dex", driver_id="oidc", title="Dex")])
    return "dex"


@pytest.fixture
def make_member(portal):
    """Return a factory for real Plone users.

    A Profile is content and carries a userid; it is not a member. A test that
    logs somebody in needs both, and conflating them is how a test ends up
    asserting about an account PAS cannot resolve.

    :param portal: The Plone site.
    :returns: Callable taking a username, returning the userid.
    """

    def factory(username: str) -> str:
        user = api.user.create(
            email=f"{username}@plone.org",
            username=username,
            password=f"s3cr3t-{username}",
        )
        return user.getId()

    return factory
