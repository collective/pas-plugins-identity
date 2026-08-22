"""Create the demo site and apply whichever half of the federation it is.

Replaces ``/app/scripts/create_site.py`` in the demo image. The repository's
own script hardcodes ``pas.plugins.identity:default`` and takes no notice of
``APPLY_PROFILES``, which is right for the production image and useless here:
the whole point of the demo is that one image becomes two different sites
depending on the profile it is told to apply.

Driven by ``DEMO_PROFILE``, which is ``identitydemo:idp`` or
``identitydemo:rp``. Nothing defaults: a container started without it should
say so rather than quietly come up as half a demo.
"""

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


DEMO_PROFILE = os.getenv("DEMO_PROFILE", "")
if not DEMO_PROFILE:
    raise SystemExit(
        "DEMO_PROFILE is unset. Set it to identitydemo:idp or identitydemo:rp; "
        "there is no sensible default, because the two halves of the demo are "
        "the same image."
    )

SITE_ID = os.getenv("SITE", "Plone")

app = makerequest(globals()["app"])

request = app.REQUEST
ifaces = [IBrowserLayer]
for iface in directlyProvidedBy(request):
    ifaces.append(iface)
directlyProvides(request, *ifaces)

admin = app.acl_users.getUserById("admin")
admin = admin.__of__(app.acl_users)
newSecurityManager(None, admin)

if SITE_ID not in app.objectIds():
    site = addPloneSite(
        app,
        SITE_ID,
        title=f"Identity demo ({DEMO_PROFILE})",
        profile_id=_DEFAULT_PROFILE,
        distribution_name="volto",
        setup_content=False,
        default_language="en",
        portal_timezone="UTC",
    )
    transaction.commit()

    portal_setup: SetupTool = site.portal_setup
    portal_setup.runAllImportStepsFromProfile("profile-pas.plugins.identity:default")
    transaction.commit()

    # The demo profile's metadata declares the rest of what it needs, so the
    # dependency chain applies it. Naming those profiles here as well would
    # mean two places to keep in step.
    portal_setup.runAllImportStepsFromProfile(f"profile-{DEMO_PROFILE}")
    transaction.commit()
    app._p_jar.sync()
