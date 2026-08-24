"""``@login-providers`` -- what the user can log in with, and how to start."""

from pas.plugins.identity.core.controlpanel import enabled_providers
from pas.plugins.identity.core.interfaces import JSONDict


def provider_listing(context) -> JSONDict:
    """Return the providers a user may log in with.

    A function rather than a method because two things answer with it now --
    the service and the expander -- and a login button rendered from the
    expander must not be able to differ from one rendered from the endpoint.

    No secrets and no configuration leave here: a login button needs an id, a
    label and somewhere to click.

    :param context: The site the providers are configured on.
    :returns: The listing, with its own ``@id``.
    """
    base = f"{context.absolute_url()}/@login-providers"
    return {
        "@id": base,
        "items": [
            {
                "@id": f"{base}/{provider.provider_id}",
                "id": provider.provider_id,
                "title": provider.title,
                "driver": provider.driver_id,
            }
            for provider in enabled_providers()
        ],
    }
