"""What ``@controlpanels/identity-clients`` serves and accepts.

The frontend builds the server settings form from this panel, so what the
panel serves is what the browser is sent. It used to serve the whole of
``IServerSettings``, which includes the client list and the signing key ring
-- the private keys -- and to write whatever a ``PATCH`` sent for either.
These tests hold it to the five settings an operator edits (issue #107).
"""

from .. import ISSUER
from .. import PROFILE_ID
from pas.plugins.identity.server.controlpanel.clients import CLIENTS_RECORD
from pas.plugins.identity.server.controlpanel.interfaces import is_issuer
from pas.plugins.identity.server.controlpanel.panel import CONFIGLET_ID
from pas.plugins.identity.server.controlpanel.panel import IdentityServerConfigletPanel
from pas.plugins.identity.server.grants.tokens import ISSUER_RECORD
from pas.plugins.identity.server.utils.keys import KEYS_RECORD
from plone import api
from plone.restapi.deserializer.controlpanels import ControlpanelDeserializeFromJson
from plone.restapi.serializer.controlpanels import ControlpanelSerializeToJson
from zExceptions import BadRequest
from zope.interface import Invalid

import json
import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])

#: The settings on the form, in the order the form shows them: the order they
#: are declared in on ``IServerSettings``, which a copied field keeps.
EDITABLE = [
    "server_issuer",
    "server_consent_url",
    "server_refresh_token_ttl",
    "server_access_token_ttl",
    "server_unreleased_groups",
]


def strings(value):
    """Yield every string anywhere in a JSON-shaped value.

    :param value: A payload, or part of one.
    :returns: A generator of strings.
    """
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from strings(item)


class TestWhatIsServed:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, http_request) -> None:
        self.portal = portal
        self.request = http_request

    def payload(self) -> dict:
        """Return what ``GET @controlpanels/identity-clients`` answers.

        :returns: The serialized panel.
        """
        panel = IdentityServerConfigletPanel(self.portal, self.request)
        # Set by the publisher while traversing, and by nothing here.
        panel.__name__ = CONFIGLET_ID
        return ControlpanelSerializeToJson(panel)()

    def test_the_form_is_the_editable_settings(self):
        assert list(self.payload()["schema"]["properties"]) == EDITABLE

    def test_the_data_is_the_editable_settings(self):
        assert sorted(self.payload()["data"]) == sorted(EDITABLE)

    def test_no_private_key_is_served(self):
        """The reason for all of it. The ring is generated when the profile
        is applied, so there is a private key in the registry to leak, and
        ``d`` is the private exponent every RSA JWK in it carries."""
        ring = api.portal.get_registry_record(KEYS_RECORD)
        assert '"d"' in ring

        served = list(strings(self.payload()))

        # Every string, not the serialized body: dumped, the ring's quotes are
        # escaped, and a search for them there finds nothing either way.
        assert [value for value in served if '"d"' in value] == []
        assert ring not in served


class TestWhatIsAccepted:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, http_request) -> None:
        self.portal = portal
        self.request = http_request

    def save(self, data: dict) -> None:
        """Save through the panel, as ``PATCH @controlpanels`` does.

        :param data: The request body.
        """
        panel = IdentityServerConfigletPanel(self.portal, self.request)
        panel.__name__ = CONFIGLET_ID
        self.request["BODY"] = json.dumps(data)
        ControlpanelDeserializeFromJson(panel)()

    def test_the_issuer_is_saved(self):
        self.save({"server_issuer": ISSUER})

        assert api.portal.get_registry_record(ISSUER_RECORD) == ISSUER

    def test_the_other_settings_are_saved(self):
        self.save({
            "server_consent_url": "https://id.example.org/consent",
            "server_access_token_ttl": 300,
            "server_refresh_token_ttl": 3600,
        })

        prefix = "pas.plugins.identity"
        assert (
            api.portal.get_registry_record(f"{prefix}.server_consent_url")
            == "https://id.example.org/consent"
        )
        assert (
            api.portal.get_registry_record(f"{prefix}.server_access_token_ttl") == 300
        )
        assert (
            api.portal.get_registry_record(f"{prefix}.server_refresh_token_ttl") == 3600
        )

    def test_the_key_ring_cannot_be_written(self):
        ring = api.portal.get_registry_record(KEYS_RECORD)

        self.save({"server_signing_keys": "[]"})

        assert api.portal.get_registry_record(KEYS_RECORD) == ring

    def test_the_client_list_cannot_be_written(self):
        """It has its own endpoint, which validates every registration; a
        panel save would have replaced it wholesale with no check at all."""
        clients = api.portal.get_registry_record(CLIENTS_RECORD)

        self.save({"server_clients": '[{"client_id": "forged"}]'})

        assert api.portal.get_registry_record(CLIENTS_RECORD) == clients

    def test_an_issuer_with_a_trailing_slash_is_refused(self):
        with pytest.raises(BadRequest):
            self.save({"server_issuer": f"{ISSUER}/"})

        assert api.portal.get_registry_record(ISSUER_RECORD) == ""


class TestTheIssuerRule:
    @pytest.mark.parametrize(
        "value",
        [
            "",
            "https://id.example.org",
            "https://id.example.org/sub/path",
            "http://id.localhost:8080",
        ],
    )
    def test_accepted(self, value: str):
        """Empty included: that is a server nobody has configured yet."""
        assert is_issuer(value) is True

    @pytest.mark.parametrize(
        "value",
        [
            pytest.param("https://id.example.org/", id="trailing-slash"),
            pytest.param("https://id.example.org/sub/", id="trailing-slash-path"),
            pytest.param(" https://id.example.org", id="leading-space"),
            pytest.param("id.example.org", id="no-scheme"),
            pytest.param("https://", id="no-host"),
            pytest.param("https://id.example.org?tenant=a", id="query"),
            pytest.param("https://id.example.org#top", id="fragment"),
        ],
    )
    def test_refused(self, value: str):
        with pytest.raises(Invalid):
            is_issuer(value)
