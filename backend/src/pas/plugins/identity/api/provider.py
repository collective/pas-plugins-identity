"""The providers this site can sign somebody in against.

What the control panel edits, read-only. Registering or editing a provider
goes through the control panel or a GenericSetup profile, so that every route
in is held to the same validation; this module is for code that needs to know
what is configured.
"""

from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel import ProviderConfig


def get(provider_id: str) -> ProviderConfig | None:
    """Return one configured provider.

    :param provider_id: The provider id, as stored in the control panel.
    :returns: The provider, or ``None`` when this site has no such provider.
    """
    return get_provider(provider_id)


def get_all() -> list[ProviderConfig]:
    """Return every configured provider, enabled or not.

    :returns: The providers, in the order the site stores them -- which is the
        order they are offered in on the sign-in page.
    """
    return get_providers()


def plugin():
    """Return this package's PAS plugin for the current site.

    :returns: The plugin, or ``None`` when the add-on is not installed here.
        ``None`` rather than an exception because "is this installed" is a
        question worth asking, and every caller of it already branches.
    """
    from pas.plugins.identity.core.services.useraccount import identity_plugin

    return identity_plugin()


__all__ = [
    "get",
    "get_all",
    "plugin",
]
