"""``@magic-link`` and ``@magic-link-confirm``.

``POST @magic-link`` with ``{"email": "..."}``
    Sends a login link, and answers the same way whether or not the address
    is known. Anything else turns the endpoint into a way to ask Plone which
    addresses have accounts.

``POST @magic-link-confirm`` with ``{"token": "..."}``
    Validates the token, burns it, and answers with a ``jwt_auth`` token.

The identity this proves is ``("email", <address>)``, and it is verified by
construction: the only way to hold the token is to have received the mail.
That is what lets it satisfy the unlink guard, and it is *not* the same thing
as a provider claiming ``email_verified`` about the same address.
"""

from pas.plugins.identity.core.controlpanel import enabled_providers
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.store import EMAIL_PROVIDER


def get_provider_config() -> ProviderConfig | None:
    """Return the configured email provider, if there is one.

    :returns: The provider, or ``None`` when magic-link login is not enabled.
    """
    for provider in enabled_providers():
        if provider.driver_id == EMAIL_PROVIDER:
            return provider
    return None
