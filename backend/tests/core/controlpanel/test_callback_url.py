"""How the login callback URL is resolved."""

from pas.plugins.identity.core.controlpanel import CALLBACK_URL_RECORD
from pas.plugins.identity.core.controlpanel import DEFAULT_CALLBACK_PATH
from pas.plugins.identity.core.controlpanel import get_callback_url
from pas.plugins.identity.core.interfaces import FlowError
from plone import api
from plone.registry.interfaces import IRegistry
from zope.component import getUtility

import pytest


class TestCallbackURL:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def configure(self, value) -> None:
        """Store a callback URL.

        :param value: What to store.
        """
        api.portal.set_registry_record(CALLBACK_URL_RECORD, value)

    def test_defaults_to_the_frontend_route(self):
        """A site that configured nothing still resolves, because the
        default is the route this package's own add-on registers."""
        assert get_callback_url() == (
            f"{self.portal.absolute_url()}{DEFAULT_CALLBACK_PATH}"
        )

    def test_a_path_is_resolved_against_the_site(self):
        self.configure("/somewhere-else")

        assert get_callback_url() == f"{self.portal.absolute_url()}/somewhere-else"

    def test_an_absolute_url_is_taken_verbatim(self):
        """The frontend need not share an origin with the backend, and no
        portal URL can describe one Plone is never reached on."""
        self.configure("https://frontend.example/login-identity")

        assert get_callback_url() == "https://frontend.example/login-identity"

    def test_an_empty_record_falls_back_to_the_default(self):
        # An empty <value> in a GenericSetup profile imports as None, and
        # plone.api refuses to store that -- so this is one of the few
        # places the registry has to be written to directly.
        getUtility(IRegistry).records[CALLBACK_URL_RECORD].value = None

        assert get_callback_url().endswith(DEFAULT_CALLBACK_PATH)

    def test_whitespace_is_not_a_configuration(self):
        self.configure("   ")

        assert get_callback_url().endswith(DEFAULT_CALLBACK_PATH)

    def test_neither_a_path_nor_a_url_is_refused(self):
        """A provider would answer an opaque rejection instead."""
        self.configure("login-identity")

        with pytest.raises(FlowError):
            get_callback_url()
