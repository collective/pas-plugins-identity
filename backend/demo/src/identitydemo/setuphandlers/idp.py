"""What the identity provider gets, as data rather than as code.

Everything the demo IdP needs beyond its registry settings is a
``plone.exportimport`` payload in :data:`IDP_CONTENT`: the demo user today,
and whatever content the demo should show as soon as somebody drops a
``content/`` folder in beside it. Nothing here has to change for that -- the
importer reads every file it recognises and reports "no data to import" for
each one it does not find, so the payload grows without the handler growing.

Which is the point. ``api.user.create`` with four keyword arguments describes
one user and nothing else; the same user as JSON is the *shape* the exporter
writes, so the way to change the demo is to configure a site, run
``plone-exporter``, and commit what comes out -- not to write more Python.

The payload is written *unguarded*. :func:`identitydemo.setuphandlers.guard`
protects the relying party profile, which is the one holding a published
client secret; the demo user is a fixed literal in a public repository either
way and refusing to create it protects nobody.
"""

from identitydemo import logger
from identitydemo import settings
from pas.plugins.identity.server.clients import get_clients
from pas.plugins.identity.server.clients import set_clients
from pas.plugins.identity.server.tokens import ISSUER_RECORD
from pathlib import Path
from plone import api
from plone.exportimport import importers
from Products.GenericSetup.tool import SetupTool


#: The ``plone.exportimport`` payload applied to the identity provider.
IDP_CONTENT = Path(__file__).parent / "idpcontent"


def install_idp(context: SetupTool) -> None:
    """Import the identity provider's principals and content.

    Idempotent, so re-running the profile against a warm volume is safe: the
    principals importer skips a user that already exists, and the content
    importer matches on UID.

    :param context: The setup tool running the import.
    """
    importer = importers.get_importer(api.portal.get())
    for line in importer.import_site(IDP_CONTENT):
        logger.info(line)

    _apply_deployment_urls()


def _apply_deployment_urls() -> None:
    """Write the two values that depend on where this demo is deployed.

    Everything else about the authorization server is in the profile's
    registry XML, including the client and its hashed secret. These two are
    not, and cannot be: there are two demo deployments, they do not agree on
    their URLs, and XML cannot read an environment variable.

    Both are compared as strings and never parsed -- the issuer by the relying
    party against the one discovery publishes, the redirect URI byte for byte
    at the token endpoint -- so a value that is merely equivalent is a login
    that fails with nothing useful to say.
    """
    api.portal.set_registry_record(ISSUER_RECORD, settings.IDP_PUBLIC_URL)

    clients = list(get_clients())
    for client in clients:
        if client.client_id == settings.DEMO_CLIENT_ID:
            client.redirect_uris = [settings.DEMO_REDIRECT_URI]
    set_clients(clients)


__all__ = ["IDP_CONTENT", "install_idp"]
