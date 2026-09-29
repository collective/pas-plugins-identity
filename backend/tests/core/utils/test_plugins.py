"""Finding a PAS plugin in the current site by its id."""

from pas.plugins.identity.core.pas import PLUGIN_ID as CORE_PLUGIN_ID
from pas.plugins.identity.core.utils.plugins import get

import pytest


class TestGet:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.acl_users = portal.acl_users

    @pytest.mark.parametrize("plugin_id", [CORE_PLUGIN_ID, "source_users"])
    def test_an_installed_plugin_is_found(self, plugin_id: str):
        """This package's own plugin, and one Plone ships."""
        assert get(plugin_id).getId() == plugin_id

    def test_an_unknown_plugin_is_none(self):
        """A lookup, so it answers ``None`` rather than raising."""
        assert get("no-such-plugin") is None

    def test_nothing_is_acquired_from_the_site(self):
        """``getattr(acl_users, ...)`` would find the site's catalog through
        acquisition and hand it back as if it were a plugin."""
        assert getattr(self.acl_users, "portal_catalog", None) is not None

        assert get("portal_catalog") is None
