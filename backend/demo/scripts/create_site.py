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

#: Id of the Profile container, matching the ``profile_container_id`` record
#: that ``pas.plugins.identity:profile`` ships.
PROFILE_CONTAINER_ID = "identity-profiles"

#: What that record has to say on a site built from the Volto distribution,
#: which does not allow ``Folder`` at the portal root at all. See
#: :func:`prepare_profile_layer`.
VOLTO_CONTAINER_TYPE = "Document"


def prepare_profile_layer(site) -> None:
    """Create the Profile container as a type a Volto site allows.

    The demo sites are built from the ``volto`` distribution, which does not
    allow ``Folder`` at the portal root, and that is what
    ``pas.plugins.identity:profile`` creates by default.

    Overriding the ``profile_container_type`` record cannot work from a
    profile: that layer's own registry step rewrites the record every time it
    is applied, and its post handler creates the container immediately
    afterwards, so any value set beforehand is gone by the time it is read and
    any value set afterwards arrives too late. ``get_container`` returns an
    existing container untouched, though, so creating it first settles the
    question before the profile ever asks it.

    The demo's own ``registry.xml`` then sets the record to match, which
    matters for nothing today and would matter if the container were ever
    removed and recreated.

    :param site: The Plone site.
    """
    if PROFILE_CONTAINER_ID in site.objectIds():
        return
    site.invokeFactory(
        VOLTO_CONTAINER_TYPE, PROFILE_CONTAINER_ID, title="Identity Profiles"
    )
    transaction.commit()


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

    if DEMO_PROFILE.endswith(":idp"):
        prepare_profile_layer(site)

    # The demo profile's metadata declares the rest of what it needs, so the
    # dependency chain applies it. Naming those profiles here as well would
    # mean two places to keep in step.
    portal_setup.runAllImportStepsFromProfile(f"profile-{DEMO_PROFILE}")
    transaction.commit()
    app._p_jar.sync()
