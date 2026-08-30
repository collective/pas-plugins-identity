"""What the identity provider gets: content as data, the demo user as code.

Whatever the demo should show is a ``plone.exportimport`` payload in
:data:`IDP_CONTENT`, and nothing here has to change as that grows -- the
importer reads every file it recognises and reports "no data to import" for
each one it does not find. The way to change the *content* of this demo is to
configure a site, run ``plone-exporter``, and commit what comes out.

The demo **user** is the exception, and it is worth saying why, because they
used to be a ``principals.json`` in that same payload. The principals importer
creates users the way Plone always has, which on this site meant a
``source_users`` row holding the password -- in the site whose whole point is
that a user is a content object. Their password cannot come out of an export
either: it lives in an annotation on their Profile, and an annotation is
precisely what an export does not carry, which is the reason a credential is
kept there instead of in a field.

So this creates them through ``api.user.create``, the seat every other user on
every other site goes through, and lets the shipped adder do what it does on
any configured site: mint the Profile, and put the password on it. The demo
then demonstrates the feature rather than working around it.

Written *unguarded*. :func:`identitydemo.setuphandlers.guard` protects the
relying party profile, which is the one holding a published client secret; the
demo user is a fixed literal in a public repository either way and refusing to
create them protects nobody.
"""

from identitydemo import logger
from identitydemo import settings
from pas.plugins.identity.core.container import get_container
from pas.plugins.identity.server.controlpanel.clients import get_clients
from pas.plugins.identity.server.controlpanel.clients import set_clients
from pas.plugins.identity.server.consent.screen import CONSENT_URL_RECORD
from pas.plugins.identity.server.grants.tokens import ISSUER_RECORD
from pathlib import Path
from plone import api
from plone.exportimport import importers
from Products.GenericSetup.tool import SetupTool


#: The ``plone.exportimport`` payload applied to the identity provider.
IDP_CONTENT = Path(__file__).parent / "idpcontent"


def install_idp(context: SetupTool) -> None:
    """Create the demo user and import the identity provider's content.

    Idempotent, so re-running the profile against a warm volume is safe: the
    user is created only when they are not there, and the content importer
    matches on UID.

    The Profile container is created *first*, and that ordering is the whole
    reason that line exists. The container is created lazily, so without it
    the user adder runs at a moment when nothing resolves at the configured
    path, declines, and the demo user lands in ``source_users`` with no
    Profile. Everyone created afterwards gets one, which is what makes the
    failure so easy to miss: the mechanism looks fine the moment you test it
    by hand, and only the first user is wrong.

    :param context: The setup tool running the import.
    """
    _ensure_profile_container()
    _create_demo_user()

    importer = importers.get_importer(api.portal.get())
    for line in importer.import_site(IDP_CONTENT):
        logger.info(line)

    _apply_deployment_urls()


def _create_demo_user() -> None:
    """Create the demo user, through the seat every user goes through.

    ``api.user.create`` reaches PAS's adder chain, where this package's plugin
    sits first and creates the Profile; the password then goes to whatever
    the Profile adapts to, which on this site is the password behavior the
    profile's ``types/UserProfile.xml`` enables. Nothing here knows any of
    that, which is the point: the demo user is created the way a site's users
    are created, and the site's configuration decides where they land.
    """
    if api.user.get(userid=settings.DEMO_USER_ID) is not None:
        return

    api.user.create(
        username=settings.DEMO_USER_ID,
        email=settings.DEMO_USER_EMAIL,
        password=settings.DEMO_USER_PASSWORD,
        properties={"fullname": settings.DEMO_USER_FULLNAME},
    )
    logger.info("Created the demo user %s", settings.DEMO_USER_ID)


def _ensure_profile_container() -> None:
    """Create the Profile container, and say so plainly when it cannot be.

    Best effort rather than fatal. A site whose parent forbids every container
    type this package will try -- which is any site with no addable types, as
    a bare test fixture is -- must still get its demo user and its content;
    refusing the whole install over the container would trade a demo user
    without a Profile for no demo at all.

    But it is logged at warning, with the consequence spelled out, because the
    silent version of this is exactly the bug it was added to fix.
    """
    from pas.plugins.identity.core.container import ContainerNotFound

    try:
        get_container(create=True)
    except ContainerNotFound as exc:
        logger.warning(
            "No Profile container (%s). The demo user will be created in "
            "source_users with no Profile.",
            exc,
        )


def _apply_deployment_urls() -> None:
    """Write the values that depend on where this demo is deployed.

    Everything else about the authorization server is in the profile's
    registry XML, including the client and its hashed secret. These are not,
    and cannot be: there are two demo deployments, they do not agree on their
    URLs, and XML cannot read an environment variable.

    The first two are compared as strings and never parsed -- the issuer by
    the relying party against the one discovery publishes, the redirect URI
    byte for byte at the token endpoint -- so a value that is merely
    equivalent is a login that fails with nothing useful to say.

    The consent URL is different in kind: it is only ever a place to send a
    browser, and setting it is what makes this demo exercise the frontend
    consent screen rather than the server's standalone fallback. Written even
    when it is empty, because empty is a meaningful value there -- it is how
    the federation test stack, which runs no frontend, asks for the standalone
    page instead of a route nothing serves.
    """
    api.portal.set_registry_record(ISSUER_RECORD, settings.IDP_PUBLIC_URL)
    api.portal.set_registry_record(CONSENT_URL_RECORD, settings.IDP_CONSENT_URL)

    clients = list(get_clients())
    for client in clients:
        if client.client_id == settings.DEMO_CLIENT_ID:
            client.redirect_uris = [settings.DEMO_REDIRECT_URI]
    set_clients(clients)


__all__ = ["IDP_CONTENT", "install_idp"]
