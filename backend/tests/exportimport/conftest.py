"""Fixtures for the export/import tests.

A site with principals in it, built through the same API an operator would
use, so a test never asserts against a document this package also invented.
"""

from . import ADDRESS
from . import LOGIN
from . import USERID
from pas.plugins.identity.core.catalog import GROUP_PORTAL_TYPE
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.container import get_container
from pas.plugins.identity.core.container import GROUP
from pas.plugins.identity.core.pas import PLUGIN_ID as CORE_PLUGIN_ID
from plone import api

import pytest


@pytest.fixture
def plugin(portal):
    """Return the identity plugin.

    :param portal: The portal.
    :returns: The plugin.
    """
    return portal.acl_users[CORE_PLUGIN_ID]


@pytest.fixture
def make_group(portal):
    """Return a factory for a group.

    :param portal: The portal.
    :returns: The factory.
    """

    def factory(group_id: str, title: str = "", **kwargs):
        """Create one group.

        :param group_id: Its id.
        :param title: Its title.
        :param kwargs: Any other field.
        :returns: The object.
        """
        with api.env.adopt_roles(["Manager"]):
            return api.content.create(
                container=get_container(create=True, kind=GROUP),
                type=GROUP_PORTAL_TYPE,
                id=group_id,
                group_id=group_id,
                title=title or group_id,
                **kwargs,
            )

    return factory


@pytest.fixture
def make_user(portal):
    """Return a factory for a Profile.

    :param portal: The portal.
    :returns: The factory.
    """

    def factory(userid: str = USERID, login: str = LOGIN, **kwargs):
        """Create one Profile.

        :param userid: Its userid, which is also its object id.
        :param login: Its login name.
        :param kwargs: Any other field.
        :returns: The object.
        """
        fields = {"emails": (ADDRESS,), "fullname": "Érico Andrei", **kwargs}
        with api.env.adopt_roles(["Manager"]):
            return api.content.create(
                container=get_container(create=True),
                type=PROFILE_PORTAL_TYPE,
                id=userid,
                userid=userid,
                login=login,
                **fields,
            )

    return factory
