"""What the relying party gets, as data where data can say it.

The provider itself is declared in the profile's registry XML, and the site's
content and principals are a ``plone.exportimport`` payload in
:data:`RP_CONTENT`. What is left here is the pair of URLs that neither can
state, because they come from the environment: there are two demo deployments
and they do not agree on them.

Nothing on this side is an authorization server. The issuer written here is
the *provider's* -- where this site sends a browser to sign in -- not one this
site publishes, and there are no clients to register: a relying party holds a
credential, it does not issue them.
"""

from identitydemo import logger
from identitydemo import settings
from identitydemo.setuphandlers import guard
from pas.plugins.identity.core.controlpanel import CALLBACK_URL_RECORD
from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pathlib import Path
from plone import api
from plone.exportimport import importers
from Products.GenericSetup.tool import SetupTool


#: The ``plone.exportimport`` payload applied to the relying party.
RP_CONTENT = Path(__file__).parent / "rpcontent"


def install_rp(context: SetupTool) -> None:
    """Import the relying party's content and point it at the demo IdP.

    Guarded, unlike the identity provider's handler: this profile is the one
    that puts a published client secret into a site.

    Idempotent, so re-running the profile against a warm volume is safe: the
    principals importer skips a user that already exists, the content importer
    matches on UID, and the provider is edited in place when it is there.

    :param context: The setup tool running the import.
    """
    guard()

    importer = importers.get_importer(api.portal.get())
    for line in importer.import_site(RP_CONTENT):
        logger.info(line)

    _apply_deployment_urls()


def _apply_deployment_urls() -> None:
    """Write the two values that depend on where this demo is deployed.

    The callback URL, the redirect URI registered with the provider and
    ``settings.DEMO_REDIRECT_URI`` are compared byte for byte at the token
    endpoint. Without the record the login endpoint answers 502 and says so,
    which is correct and is the first thing a new deployment hits.

    The issuer is the provider's *public* URL even though discovery is fetched
    server to server, because the issuer is also what the browser is
    redirected to and a provider will not answer under a URL other than the
    one it publishes. Reaching it from inside the compose network is a DNS
    problem, solved in the compose file, not a configuration problem to be
    solved by lying here.

    It is written on every install, even when the profile's registry XML has
    already declared the provider. Returning early because the provider exists
    would leave the hermetic stack pointed at the manual stack's hostname.
    """
    api.portal.set_registry_record(CALLBACK_URL_RECORD, settings.DEMO_REDIRECT_URI)

    # ``set_providers`` renumbers ``order`` from list position, so the existing
    # list is edited in place rather than rebuilt: appending a provider that is
    # already there would silently move it down the login screen.
    providers = list(get_providers())
    if get_provider(settings.DEMO_PROVIDER_ID) is None:
        providers.append(
            ProviderConfig(
                provider_id=settings.DEMO_PROVIDER_ID,
                driver_id="plone-identity",
                title="id.localhost",
                config={
                    "client_id": settings.DEMO_CLIENT_ID,
                    "client_secret": settings.DEMO_CLIENT_SECRET,
                    "scope": ("openid", "email", "profile", "address"),
                    # Two containers on a laptop, with no certificate between
                    # them. See core/portraits.py for why this is never a
                    # default.
                    "picture_over_http": True,
                },
            )
        )
        logger.info("Registered demo provider %s", settings.DEMO_PROVIDER_ID)

    for provider in providers:
        if provider.provider_id == settings.DEMO_PROVIDER_ID:
            provider.config["issuer"] = settings.IDP_PUBLIC_URL
    set_providers(providers)


__all__ = ["RP_CONTENT", "install_rp"]
