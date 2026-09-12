from AccessControl.SecurityManagement import newSecurityManager
from pas.plugins.identity.interfaces import IBrowserLayer
from Products.CMFPlone.factory import _DEFAULT_PROFILE
from Products.CMFPlone.factory import addPloneSite
from Products.GenericSetup.tool import SetupTool
from Testing.makerequest import makerequest
from zope.interface import directlyProvidedBy
from zope.interface import directlyProvides

import os
import transaction


truthy = frozenset(("t", "true", "y", "yes", "on", "1"))


def asbool(s):
    """Return the boolean value ``True`` if the case-lowered value of string
    input ``s`` is a :term:`truthy string`. If ``s`` is already one of the
    boolean values ``True`` or ``False``, return it."""
    if s is None:
        return False
    if isinstance(s, bool):
        return s
    s = str(s).strip()
    return s.lower() in truthy


DELETE_EXISTING = asbool(os.getenv("DELETE_EXISTING"))
EXAMPLE_CONTENT = asbool(os.getenv("EXAMPLE_CONTENT", "1"))

#: Profile applied when example content is asked for: a front page, and GitHub
#: and Google sign-in for a developer's ``localhost`` checkout.
EXAMPLE_CONTENT_PROFILE = "pas.plugins.identity:initial"


app = makerequest(globals()["app"])

request = app.REQUEST

ifaces = [IBrowserLayer]
for iface in directlyProvidedBy(request):
    ifaces.append(iface)

directlyProvides(request, *ifaces)

admin = app.acl_users.getUserById("admin")
admin = admin.__of__(app.acl_users)
newSecurityManager(None, admin)

site_id = "Plone"
payload = {
    "title": "pas.plugins.identity",
    "profile_id": _DEFAULT_PROFILE,
    "distribution_name": "volto",
    "setup_content": False,
    "default_language": "en",
    "portal_timezone": "UTC",
}

if site_id in app.objectIds() and DELETE_EXISTING:
    app.manage_delObjects([site_id])
    transaction.commit()
    app._p_jar.sync()

if site_id not in app.objectIds():
    site = addPloneSite(app, site_id, **payload)
    transaction.commit()

    portal_setup: SetupTool = site.portal_setup
    portal_setup.runAllImportStepsFromProfile("profile-pas.plugins.identity:default")
    transaction.commit()

    # The profile's providers carry client secrets whose applications accept
    # only a ``localhost`` callback. A site created for anything else sets
    # EXAMPLE_CONTENT=0 and configures its own.
    if EXAMPLE_CONTENT:
        portal_setup.runAllImportStepsFromProfile(f"profile-{EXAMPLE_CONTENT_PROFILE}")
        transaction.commit()
    app._p_jar.sync()
