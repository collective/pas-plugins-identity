"""Server profile version 1001: every client gets ``allowed_groups``.

Registration is asserted here as well as the effect. This is the server
profile's first upgrade step, and ``server/upgrades`` is included from the
server's ``profiles.zcml``; left out, the step would not appear in the add-ons
control panel, would not run, and nothing would report it.
"""

from .. import PROFILE_ID
from pas.plugins.identity.server.controlpanel.clients import CLIENTS_RECORD
from pas.plugins.identity.server.controlpanel.clients import get_client
from plone import api

import json
import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


#: The version a site ends at once every step has run.
LATEST = "1001"

#: Registrations as a site at 1000 stored them: no ``allowed_groups`` key.
#: The second one carries a redirect URI the model refuses today (a
#: fragment), which the step has to leave alone rather than stop on.
LEGACY = [
    {
        "client_id": "intranet",
        "title": "Intranet",
        "redirect_uris": ["https://intranet.example.org/cb"],
        "grant_types": ["authorization_code"],
        "scope": ["openid"],
        "auth_method": "client_secret_post",
        "secret_hash": "not-a-real-hash",
        "enabled": True,
        "service_user": "",
    },
    {
        "client_id": "legacy",
        "title": "Legacy",
        "redirect_uris": ["https://legacy.example.org/cb#fragment"],
        "grant_types": ["authorization_code"],
        "scope": "openid email",
        "auth_method": "none",
        "secret_hash": "",
        "enabled": False,
        "service_user": "",
    },
]


def stored() -> list[dict]:
    """Return the client registrations exactly as the registry holds them.

    :returns: The decoded JSON list.
    """
    return json.loads(api.portal.get_registry_record(CLIENTS_RECORD) or "[]")


class TestRegistration:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.setup_tool = api.portal.get_tool("portal_setup")

    def test_a_site_at_1000_is_offered_the_step(self):
        self.setup_tool.setLastVersionForProfile(PROFILE_ID, "1000")

        upgrades = self.setup_tool.listUpgrades(PROFILE_ID)

        dests = {
            step.get("dest")
            for group in upgrades
            for step in (group if isinstance(group, list) else [group])
        }
        assert (LATEST,) in dests

    def test_a_site_at_the_latest_version_is_offered_nothing(self):
        assert self.setup_tool.listUpgrades(PROFILE_ID) == []

    def test_the_upgrade_ends_at_the_latest_version(self):
        self.setup_tool.setLastVersionForProfile(PROFILE_ID, "1000")

        self.setup_tool.upgradeProfile(PROFILE_ID)

        assert self.setup_tool.getLastVersionForProfile(PROFILE_ID) == (LATEST,)


class TestAllowedGroupsAdded:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.setup_tool = api.portal.get_tool("portal_setup")

    def upgrade(self, entries: list[dict] | None) -> None:
        """Store registrations as a site at 1000 held them, then upgrade.

        :param entries: The stored registrations; ``None`` for none at all.
        """
        value = "" if entries is None else json.dumps(entries)
        api.portal.set_registry_record(CLIENTS_RECORD, value)
        self.setup_tool.setLastVersionForProfile(PROFILE_ID, "1000")
        self.setup_tool.upgradeProfile(PROFILE_ID)

    def test_every_registration_gets_an_empty_list(self):
        self.upgrade(LEGACY)

        assert [entry["allowed_groups"] for entry in stored()] == [[], []]

    def test_nothing_else_in_a_registration_changes(self):
        """Edited as JSON, not re-serialized through the model, which would
        normalise the string scope and refuse the fragment."""
        self.upgrade(LEGACY)

        after = stored()
        for before, entry in zip(LEGACY, after, strict=True):
            assert {k: v for k, v in entry.items() if k != "allowed_groups"} == before

    def test_a_registration_that_has_the_key_keeps_its_value(self):
        restricted = {**LEGACY[0], "allowed_groups": ["Reviewers"]}

        self.upgrade([restricted])

        assert stored()[0]["allowed_groups"] == ["Reviewers"]

    def test_an_upgraded_client_still_admits_everybody(self):
        self.upgrade(LEGACY[:1])

        client = get_client("intranet")

        assert client.allowed_groups == []
        assert client.admits([])

    @pytest.mark.parametrize("entries", [None, []])
    def test_a_site_with_no_clients_upgrades(self, entries):
        self.upgrade(entries)

        assert self.setup_tool.getLastVersionForProfile(PROFILE_ID) == (LATEST,)
