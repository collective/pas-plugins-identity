"""Fixtures shared by the service tests that send mail."""

from . import EMAIL_PROVIDER_RECORD
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from plone import api

import email
import pytest


@pytest.fixture
def email_configured(portal, configured):
    """Add the email provider alongside the Dex fixture."""
    set_providers([
        *get_providers(),
        ProviderConfig.deserialize(EMAIL_PROVIDER_RECORD),
    ])


@pytest.fixture
def mailbox(portal):
    """Return a reader over the captured mail, emptied first.

    Mail is captured in process by ``collective.MockMailHost``, so the whole
    round trip -- ask for a link, read it out of the message, redeem it --
    runs without a mail server anywhere.

    :returns: A callable answering the parsed messages, oldest first.
    """
    mailhost = api.portal.get_tool("MailHost")
    mailhost.reset()

    def read() -> list:
        """Return the captured messages, parsed.

        :returns: Parsed messages, oldest first.
        """
        return [
            email.message_from_bytes(raw, policy=email.policy.default)
            for raw in mailhost.messages
        ]

    return read
