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
        # The two packages this one migrates from (Gate 7). Loaded here so the
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
        # (Gate 3) without a mail server anywhere.
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


ACCEPTANCE_TESTING = FunctionalTesting(
    bases=(
        FIXTURE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        WSGI_SERVER_FIXTURE,
    ),
    name="Pas.Plugins.IdentityLayer:AcceptanceTesting",
)
