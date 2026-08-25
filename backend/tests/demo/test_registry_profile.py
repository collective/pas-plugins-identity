"""The demo profile's registry XML has to survive the real importer.

The demo ships provider records, and provider records belong to no interface:
each one carries its own field type, which is what
``tests/core/test_export.py`` pins on the *export* side. Nothing pinned the
import side, and the file spent a day in a shape GenericSetup rejects outright
-- ``<records prefix="...">`` with no ``interface`` attribute, which raises
``KeyError`` before a single record is applied, taking the interface-bound
sections above it down with it.

Reading the file rather than applying the profile is deliberate: applying it
would need ``identitydemo`` installed in the test site, which drags in a
published client secret and a demo user. The failure mode being guarded
against is entirely in the XML.
"""

from identitydemo import settings
from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.server.claims import SCOPE_CLAIMS
from pas.plugins.identity.server.clients import get_client
from pas.plugins.identity.server.clients import verify_secret
from plone.registry.interfaces import IRegistry
from zope.component import getUtility

import pytest


class TestDemoIdPRegistry:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, demo_registry):
        self.portal = portal
        self.registry = getUtility(IRegistry)
        demo_registry("idp")

    def test_provider_is_readable_through_the_api(self):
        """The point of the file: a provider the add-on can actually use."""
        provider = get_provider("github")
        assert provider is not None
        assert provider.driver_id == "github"
        assert provider.title == "GitHub"
        assert provider.enabled is True

    def test_typed_records_keep_their_types(self):
        """A record that imports untyped reads back as a string, and every
        boolean in the file would then be true."""
        assert self.registry["pas.plugins.identity.providers.github.enabled"] is True
        assert self.registry["pas.plugins.identity.providers.github.order"] == 1
        assert self.registry["pas.plugins.identity.providers.email.order"] == 0

    def test_the_magic_link_is_offered_first(self):
        """It is the one way into this demo that needs nothing configured
        anywhere else: no OAuth client, no secret, no third-party account.

        ``get_providers`` answers in stored order, which is the order of the
        buttons on the login page.
        """
        assert [p.provider_id for p in get_providers()] == ["email", "github"]

    def test_the_property_map_is_a_mapping(self):
        """Written as a Python ``repr`` it imports as one long string, and the
        login that applies it resolves nothing."""
        provider = get_provider("github")
        assert provider.propertymap["bio"] == "description"
        assert provider.propertymap["picture_url"] == "portrait"

    def test_the_interface_bound_sections_applied(self):
        """They sit above the provider records, so a provider block that
        raises takes them with it."""
        assert self.registry["pas.plugins.identity.sync_portraits"] is True

    def test_the_demo_client_is_registered(self):
        client = get_client(settings.DEMO_CLIENT_ID)

        assert client is not None
        assert client.title == settings.DEMO_CLIENT_TITLE

    def test_the_registered_secret_is_the_documented_one(self):
        """The relying party is installed in another container and can only
        be handed a literal, so the two halves agree by both reading
        ``settings``. This is the assertion that fails if one is edited
        alone."""
        client = get_client(settings.DEMO_CLIENT_ID)

        assert verify_secret(settings.DEMO_CLIENT_SECRET, client.secret_hash)

    def test_the_secret_is_not_stored_in_the_clear(self):
        """Stated because the secret being a known literal makes it easy to
        stop caring how it is stored."""
        client = get_client(settings.DEMO_CLIENT_ID)

        assert settings.DEMO_CLIENT_SECRET not in client.secret_hash

    def test_the_issuer_is_left_to_the_install_handler(self):
        """The two demo stacks disagree on it, and XML cannot read an
        environment variable."""
        assert not self.registry["pas.plugins.identity.server_issuer"]


class TestDemoRPRegistry:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, demo_registry):
        self.portal = portal
        self.registry = getUtility(IRegistry)
        demo_registry("rp")

    def test_provider_is_readable_through_the_api(self):
        provider = get_provider("demo-idp")
        assert provider is not None
        assert provider.driver_id == "plone-identity"
        assert provider.config["client_id"] == "demo-rp"

    def test_the_issuer_is_left_to_the_install_handler(self):
        """The two demo stacks disagree on it, and XML cannot read an
        environment variable."""
        assert "issuer" not in get_provider("demo-idp").config

    def test_every_mapped_claim_is_one_this_provider_publishes(self):
        """A map addressed by Plone field name instead of claim path resolves
        nothing, and does so silently."""
        published = set(SCOPE_CLAIMS["profile"]) | set(SCOPE_CLAIMS["email"])
        published |= {"address.formatted"}
        # ``fullname`` and ``picture_url`` are this package's own normalized
        # names for ``name`` and ``picture``, which the map may address
        # directly; everything else has to be a real claim.
        published |= {"fullname", "picture_url"}
        assert set(get_provider("demo-idp").propertymap) <= published
