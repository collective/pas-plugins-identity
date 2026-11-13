from OFS.Application import AppInitializer
from pas.plugins.identity.core.controlpanel import CALLBACK_URL_RECORD
from pas.plugins.identity.core.controlpanel import DEFAULT_CALLBACK_PATH
from pas.plugins.identity.server.consent.screen import CONSENT_URL_RECORD
from pas.plugins.identity.server.grants.tokens import ISSUER_RECORD
from plone import api
from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import quickInstallProduct
from plone.base.interfaces import IMailSchema
from plone.registry.interfaces import IRegistry
from plone.testing.zope import WSGI_SERVER_FIXTURE
from zope.component import getUtility

import os


class Layer(PloneSandboxLayer):
    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load any other ZCML that is required for your tests.
        # The z3c.autoinclude feature is disabled in the Plone fixture base
        # layer.
        import collective.MockMailHost
        import pas.plugins.authomatic
        import pas.plugins.oidc
        import plone.restapi

        self.loadZCML(package=plone.restapi)
        # The two packages this one migrates from. Loaded here so the
        # migration tests can install them for real rather than synthesizing
        # their storage -- a fixture that encoded our reading of their BTrees
        # would pass while the migration was wrong about them. Loading the
        # ZCML registers their profiles; nothing applies one unless a test
        # asks, so every other test still runs in a site that has never heard
        # of either.
        self.loadZCML(package=pas.plugins.authomatic)
        self.loadZCML(package=pas.plugins.oidc)
        # Captures outgoing mail in the MailHost tool instead of sending it,
        # which is what makes the magic-link round trip testable in process
        # without a mail server anywhere.
        self.loadZCML(package=collective.MockMailHost)
        self.loadZCML(package=pas.plugins.identity)

    def setUpPloneSite(self, portal):
        applyProfile(portal, "pas.plugins.identity:default")
        quickInstallProduct(portal, "collective.MockMailHost")
        applyProfile(portal, "collective.MockMailHost:default")
        # plone.api.portal.send_email refuses to run while the overview
        # control panel would show a "MailHost is not configured" warning,
        # and that check reads the *registry*, not the portal attributes.
        # Nothing is actually sent: MockMailHost captures it.
        registry = getUtility(IRegistry)
        mail = registry.forInterface(IMailSchema, prefix="plone", check=False)
        mail.smtp_host = "localhost"
        mail.email_from_address = "noreply@plone.org"
        mail.email_from_name = "Plone Site"


FIXTURE = Layer()

INTEGRATION_TESTING = IntegrationTesting(
    bases=(FIXTURE,),
    name="Pas.Plugins.IdentityLayer:IntegrationTesting",
)


FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(FIXTURE, WSGI_SERVER_FIXTURE),
    name="Pas.Plugins.IdentityLayer:FunctionalTesting",
)


class AcceptanceLayer(PloneSandboxLayer):
    """What a browser-driven test needs beyond :data:`FIXTURE`.

    Volto's own robot layer used to provide part of this, configured through
    the ``CONFIGURE_PACKAGES`` and ``APPLY_PROFILES`` variables. This layer
    reads neither, so it states what it needs itself.

    The frontend reaches the backend the way a production site does: the
    browser calls the frontend's own origin, and Volto's server proxies to
    this one through ``VirtualHostBase`` URLs. That needs the virtual host
    monster, which a real Zope root has and the test one does not. It is
    also what makes a federated sign-in work at all: its state is a cookie
    the backend sets, and a browser keeps no cookie from a cross-origin
    request that Volto makes without credentials.

    A request made to the backend directly, as the tests' own set-up does,
    sees the backend's address as the portal URL. A login callback given as a
    path would resolve against it, and a magic link asked for that way would
    open Classic UI. The callback is the frontend's absolute URL instead, read
    from ``ACCEPTANCE_FRONTEND_URL``.

    Kept apart from :data:`FIXTURE` so the integration and functional tests
    run in a site without Volto, as they always have.
    """

    defaultBases = (FIXTURE,)

    def setUpZope(self, app, configurationContext):
        AppInitializer(app).install_virtual_hosting()

    def setUpPloneSite(self, portal):
        applyProfile(portal, "plone.volto:default")
        frontend = os.environ.get("ACCEPTANCE_FRONTEND_URL", "http://localhost:3000")
        api.portal.set_registry_record(
            CALLBACK_URL_RECORD, f"{frontend.rstrip('/')}{DEFAULT_CALLBACK_PATH}"
        )
        # The authorization server's screens -- client registration, consent,
        # the applications page -- are part of what the browser tests cover.
        # Nothing can be signed without an issuer, and the acceptance server
        # is reached on a fixed address, so it is stated here.
        applyProfile(portal, "pas.plugins.identity.server:default")
        backend = os.environ.get(
            "ACCEPTANCE_BACKEND_URL", "http://localhost:55001/plone"
        )
        api.portal.set_registry_record(ISSUER_RECORD, backend.rstrip("/"))
        # Without a frontend route the server asks for consent on a page of
        # its own; a Volto site sends the question to the add-on's screen.
        api.portal.set_registry_record(
            CONSENT_URL_RECORD, f"{frontend.rstrip('/')}/oauth-consent"
        )


ACCEPTANCE_FIXTURE = AcceptanceLayer()

ACCEPTANCE_TESTING = FunctionalTesting(
    bases=(
        ACCEPTANCE_FIXTURE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        WSGI_SERVER_FIXTURE,
    ),
    name="Pas.Plugins.IdentityLayer:AcceptanceTesting",
)
