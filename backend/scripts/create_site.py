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

#: Profile applied when example content is asked for. Not registered by this
#: package yet; see the call site.
EXAMPLE_CONTENT_PROFILE = "pas.plugins.identity:initial"


def _registered_profiles() -> set:
    """Return the ids of every registered GenericSetup profile.

    :returns: Profile ids, without the ``profile-`` prefix.
    """
    from Products.GenericSetup.registry import _profile_registry

    return set(_profile_registry.listProfiles())


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

    # This package ships no ``initial`` profile today, and applying one that
    # is not registered raises KeyError *after* the site has been created --
    # so the container dies with a traceback about GenericSetup rather than
    # about example content, and dies on every start with EXAMPLE_CONTENT at
    # its default of on. Asking first keeps the hook for whenever the profile
    # does arrive, without making its absence fatal.
    if EXAMPLE_CONTENT and EXAMPLE_CONTENT_PROFILE in _registered_profiles():
        portal_setup.runAllImportStepsFromProfile(f"profile-{EXAMPLE_CONTENT_PROFILE}")
        transaction.commit()
    app._p_jar.sync()
