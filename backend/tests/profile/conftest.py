"""Fixtures for the ``[profile]`` extra (Gate 6).

The profile is applied per test on the ordinary integration layer rather than
from a second ``PloneSandboxLayer``. That is not the obvious choice, so it is
worth writing down why: ``pytest_plone``'s ``fixtures_factory`` keeps every
layer it is given set up for the whole session, and two sandbox layers kept up
at once end up sharing one site, with whichever was set up last deciding what
is installed in it. The visible symptom was the *magic-link* tests failing on
a missing MockMailHost -- a suite that has nothing to do with profiles, on a
layer that never mentions them.

Applying the profile inside the test keeps the core layer honestly core: every
test outside this package still runs against a site where the extra was never
installed, which is what makes the "core installs alone" invariant (I5)
something the suite proves rather than something it assumes. Integration
testing rolls the transaction back afterwards, so the site is clean again for
the next test.
"""

from pas.plugins.identity import PACKAGE_NAME
from pas.plugins.identity.profile.catalog import CATALOG_ID
from plone import api
from plone.app.testing import applyProfile

import pytest


@pytest.fixture
def portal(integration):
    """A site with the ``[profile]`` extra installed.

    Shadows the core ``portal`` fixture for everything under this package, so
    no test here can accidentally assert against a site that never applied the
    profile.

    :param integration: The integration layer.
    :returns: The Plone site.
    """
    site = integration["portal"]
    applyProfile(site, f"{PACKAGE_NAME}:profile")
    return site


@pytest.fixture
def catalog(portal):
    """The Profile catalog.

    :param portal: The Plone site.
    :returns: The catalog tool.
    """
    return api.portal.get_tool(CATALOG_ID)
