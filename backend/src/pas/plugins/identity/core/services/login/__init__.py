"""``@login-providers`` -- what the user can log in with, and how to start."""

from pas.plugins.identity.core.controlpanel import login_providers
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.interfaces import JSONDict


def render_provider(base: str, provider: ProviderConfig) -> JSONDict:
    """Render one provider as a login button.

    :param base: URL of the listing this entry belongs to.
    :param provider: The provider.
    :returns: JSON-ready mapping. No secrets and no configuration: a button
        needs an id, a label, somewhere to click and how to look.
    """
    driver = provider.driver
    return {
        "@id": f"{base}/{provider.provider_id}",
        "id": provider.provider_id,
        "title": provider.title or (driver.title if driver is not None else ""),
        "driver": provider.driver_id,
        # Whether a client may offer this provider as something to link from
        # a form of its own. False for magic link, whose addresses come from
        # the user's own profile rather than from a box on the page.
        "supports_manual_link": (
            driver.supports_manual_link if driver is not None else False
        ),
        **provider.style(),
    }


def provider_listing(context) -> JSONDict:
    """Return the providers the login screen should offer.

    A function rather than a method because two things answer with it now --
    the service and the expander -- and a login button rendered from the
    expander must not be able to differ from one rendered from the endpoint.

    Hidden providers are absent here and present in ``@identities``: this is
    the login screen's question, and ``show_in_login`` is the setting that
    answers it.

    :param context: The site the providers are configured on.
    :returns: The listing, with its own ``@id``.
    """
    base = f"{context.absolute_url()}/@login-providers"
    return {
        "@id": base,
        "items": [render_provider(base, provider) for provider in login_providers()],
    }
