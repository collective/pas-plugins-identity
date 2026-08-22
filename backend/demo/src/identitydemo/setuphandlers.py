"""Install handlers for the two demo profiles.

Both start by calling :func:`guard`, which refuses to do anything unless the
opt-in environment variable is set. The profiles are visible in any site that
has this package on its path, so the guard is what stands between a curious
click in ``portal_setup`` and a site holding a published client secret.
"""

from identitydemo import logger
from identitydemo import settings
from pas.plugins.identity.core.controlpanel import CALLBACK_URL_RECORD
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.server.clients import ClientConfig
from pas.plugins.identity.server.clients import get_client
from pas.plugins.identity.server.clients import get_clients
from pas.plugins.identity.server.clients import hash_secret
from pas.plugins.identity.server.clients import set_clients
from pas.plugins.identity.server.tokens import ISSUER_RECORD
from plone import api
from Products.GenericSetup.tool import SetupTool

import os


class DemoRefused(RuntimeError):
    """Raised when a demo profile is applied to a site that did not opt in."""


def guard() -> None:
    """Refuse to install unless the site explicitly asked for the demo.

    :raises DemoRefused: When :data:`identitydemo.settings.OPT_IN_ENV` is
        unset or empty. Deliberately an exception rather than a silent
        no-op: a profile that appears to install and then does nothing is
        worse to debug than one that says why it stopped.
    """
    if not os.environ.get(settings.OPT_IN_ENV):
        raise DemoRefused(
            f"identitydemo ships fixed, publicly known credentials and will "
            f"not install unless {settings.OPT_IN_ENV} is set. If this is a "
            f"real site, that is the correct outcome."
        )


def install_idp(context: SetupTool) -> None:
    """Register the demo client and the demo user on the identity provider.

    Idempotent, so re-running the profile against a warm volume is safe.

    The client is built by hand rather than through
    :func:`pas.plugins.identity.server.clients.add_client`, which mints a
    secret and returns it exactly once. There is nobody here to hand it to:
    the relying party is a different container, installed from its own
    profile, so the credential has to be a literal both sides can read.

    :param context: The setup tool running the import.
    """
    guard()

    # Written here rather than in the profile's registry XML because the URLs
    # come from the environment: the hermetic stack and the manual stack do
    # not agree on them, and XML cannot read an environment variable. Stating
    # them in one place also removes the drift between a Python constant and
    # an XML literal that nothing would have caught.
    api.portal.set_registry_record(ISSUER_RECORD, settings.IDP_PUBLIC_URL)

    if get_client(settings.DEMO_CLIENT_ID) is None:
        client = ClientConfig(
            client_id=settings.DEMO_CLIENT_ID,
            title=settings.DEMO_CLIENT_TITLE,
            redirect_uris=[settings.DEMO_REDIRECT_URI],
            grant_types=["authorization_code", "refresh_token"],
            scope="openid email profile",
            auth_method="client_secret_post",
            secret_hash=hash_secret(settings.DEMO_CLIENT_SECRET),
        )
        set_clients([*get_clients(), client])
        logger.info("Registered demo client %s", settings.DEMO_CLIENT_ID)

    if api.user.get(userid=settings.DEMO_USER_ID) is None:
        api.user.create(
            email=settings.DEMO_USER_EMAIL,
            username=settings.DEMO_USER_ID,
            password=settings.DEMO_USER_PASSWORD,
            properties={"fullname": settings.DEMO_USER_FULLNAME},
        )
        logger.info("Created demo user %s", settings.DEMO_USER_ID)


def install_rp(context: SetupTool) -> None:
    """Point the relying party at the demo identity provider.

    The issuer is the *public* URL even though discovery is fetched server to
    server, because the issuer is also what the browser is redirected to and a
    provider will not answer under a URL other than the one it publishes.
    Reaching it from inside the compose network is a DNS problem, solved in
    the compose file, not a configuration problem to be solved by lying here.

    :param context: The setup tool running the import.
    """
    guard()

    # Without this the login endpoint answers 502 and says so, which is
    # correct and is the first thing a new deployment hits. It has to be the
    # byte-identical twin of the redirect URI registered with the provider.
    api.portal.set_registry_record(CALLBACK_URL_RECORD, settings.DEMO_REDIRECT_URI)

    if get_provider(settings.DEMO_PROVIDER_ID) is not None:
        return

    provider = ProviderConfig(
        provider_id=settings.DEMO_PROVIDER_ID,
        driver_id="oidc-generic",
        title="Sign in with the demo IdP",
        config={
            "issuer": settings.IDP_PUBLIC_URL,
            "client_id": settings.DEMO_CLIENT_ID,
            "client_secret": settings.DEMO_CLIENT_SECRET,
            "scope": "openid email profile",
        },
    )
    set_providers([*get_providers(), provider])
    logger.info("Registered demo provider %s", settings.DEMO_PROVIDER_ID)
