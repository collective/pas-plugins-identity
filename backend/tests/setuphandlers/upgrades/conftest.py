"""Fixtures shared by the upgrade step tests."""

from . import PROFILE
from collections.abc import Callable
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from plone import api
from Products.GenericSetup.tool import SetupTool

import pytest


@pytest.fixture
def setup_tool(portal) -> SetupTool:
    """Return the setup tool.

    :param portal: The Plone site.
    :returns: ``portal_setup``.
    """
    return api.portal.get_tool("portal_setup")


@pytest.fixture
def upgrade_from(setup_tool) -> Callable[[str], None]:
    """Return a function that runs the upgrades as a site at a version would.

    :param setup_tool: ``portal_setup``.
    :returns: A callable taking the profile version the site pretends to be at.
    """

    def upgrade(version: str) -> None:
        setup_tool.setLastVersionForProfile(PROFILE, version)
        setup_tool.upgradeProfile(PROFILE)

    return upgrade


@pytest.fixture
def make_profile(container) -> Callable[..., object]:
    """Return a factory for Profiles in the configured container.

    Not the ``make_profile`` fixture in ``tests/core/conftest.py``, which is
    not visible here. Widening its scope to reach this package would change
    every test under ``tests/core`` to make these shorter. The container comes
    from this suite's own fixture, which creates it the way a first login does.

    :param container: The Profile container.
    :returns: A callable taking a userid and a full name.
    """

    def make(userid: str, fullname: str) -> object:
        # Elevated: adding a Profile is held to a permission of its own, and
        # this suite starts from a site that has only been installed.
        with api.env.adopt_roles(["Manager"]):
            return api.content.create(
                container=container,
                type=PROFILE_PORTAL_TYPE,
                id=userid,
                userid=userid,
                login=f"{userid}@example.com",
                fullname=fullname,
            )

    return make
