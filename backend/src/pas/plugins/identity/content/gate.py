"""Holding a user on their profile until it carries what the site requires.

A redirect at login is a suggestion: the user closes the tab, comes back
tomorrow and is asked again. This is the other thing, asked for deliberately
(Érico, 2026-08-27): while a profile is ``incomplete``, every page its owner
asks for is answered with a redirect to the profile's edit form.

**This can lock a site out, and the two things that stop it are here rather
than in the documentation.** A required field nobody can supply -- named in
the registry but not on the type, or simply impossible to satisfy -- would
otherwise leave every user in a loop with no way to reach the control panel
that would undo it. So:

* ``Manager`` and ``Site Administrator`` are never gated. Somebody has to be
  able to reach the settings, and it cannot be somebody who first has to get
  past the gate.
* ``pas.plugins.identity.enforce_required_profile_fields`` turns the whole
  thing off, from that same control panel.

What is *not* gated is as load-bearing as what is, and each exclusion below
is a way the gate would otherwise break the escape it depends on.

``IAPIRequest``
    Volto talks to this site over ``plone.restapi``. Redirecting those calls
    would break the edit form itself, which is the one page the user has to
    reach. The frontend does its own routing; see the Volto add-on.

Anything that is not a browser asking for a page
    A gate on every request is a gate on stylesheets and images too. Only
    ``GET`` for ``text/html`` is a navigation.

The profile itself
    Its edit form, its widgets, its save. Redirecting the target of the
    redirect is a loop that no amount of correct configuration escapes.

Signing out
    A user who would rather leave than fill the form in must be able to.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.content.catalog import query_catalog
from pas.plugins.identity.content.completeness import INCOMPLETE
from pas.plugins.identity.content.container import PREFIX
from plone import api
from plone.api.exc import InvalidParameterError
from plone.rest.interfaces import IAPIRequest
from zExceptions import Redirect


#: Registry record turning the gate off. On by default: "enforce" is what was
#: asked for, and a flow nobody is held to is the flow this package already
#: had.
ENFORCE_RECORD = f"{PREFIX}.enforce_required_profile_fields"

#: Roles that pass through. Not a convenience: an administrator locked out by
#: a required field they configured has no way to unconfigure it.
BYPASS_ROLES = frozenset({"Manager", "Site Administrator"})

#: Last path segments never gated, whatever else is true. Leaving has to stay
#: possible, and so does arriving.
ALLOWED = frozenset({
    "logout",
    "@@logout",
    "login",
    "@@login",
    "login_form",
    "logged_out",
    "require_login",
    "@@require_login",
})


def _enforcing() -> bool:
    """Return whether the gate is switched on in this site.

    :returns: The record's value, and ``False`` when the layer's settings are
        not registered here at all.
    """
    try:
        return bool(api.portal.get_registry_record(ENFORCE_RECORD, default=False))
    except InvalidParameterError:
        return False


def _is_navigation(request) -> bool:
    """Return whether this request is a browser asking for a page.

    A gate on every request is a gate on stylesheets, images and favicons.
    ``GET`` for ``text/html`` is what a person clicking a link sends, and it
    is the only thing worth redirecting.

    :param request: The current request.
    :returns: Whether to consider gating it.
    """
    if request.get("REQUEST_METHOD", "GET") != "GET":
        return False
    return "text/html" in (request.getHeader("Accept") or "")


def _traversed_paths(request) -> set[str]:
    """Return the physical paths of everything this request traversed.

    Read off ``PARENTS`` rather than from ``PATH_INFO`` because a site behind
    a virtual host rewrites the URL and does not rewrite the object tree, and
    the question here is which *object* was reached.

    :param request: The current request.
    :returns: Physical paths, as strings.
    """
    paths = set()
    for obj in request.get("PARENTS", None) or []:
        get_path = getattr(obj, "getPhysicalPath", None)
        if get_path is not None:
            paths.add("/".join(get_path()))
    return paths


def _incomplete_profile(userid: str):
    """Return the brain of this user's profile when it is incomplete.

    From the catalog, so the check every page load performs wakes nothing --
    the same discipline the enumeration plugin and ``@my-profile`` follow.

    :param userid: The current user's id.
    :returns: The brain, or ``None`` when there is nothing to hold them for.
    """
    catalog = query_catalog()
    if catalog is None:
        return None
    brains = catalog.unrestrictedSearchResults(userid=userid)
    if not brains:
        return None
    brain = brains[0]
    return brain if brain.review_state == INCOMPLETE else None


def redirect_target(request) -> str | None:
    """Return where this request should be sent, or ``None`` to let it pass.

    Every condition is a reason *not* to gate, checked cheapest first, so the
    ordinary request on an ordinary site answers on the first or second line.

    :param request: The current request.
    :returns: An absolute URL, or ``None``.
    """
    if IAPIRequest.providedBy(request):
        return None
    if not _is_navigation(request):
        return None
    if api.user.is_anonymous():
        return None
    if request.get("PATH_INFO", "").rstrip("/").rsplit("/", 1)[-1] in ALLOWED:
        return None

    user = api.user.get_current()
    if BYPASS_ROLES & set(user.getRoles()):
        return None
    if not _enforcing():
        return None

    brain = _incomplete_profile(user.getId())
    if brain is None:
        return None
    if brain.getPath() in _traversed_paths(request):
        # Already on the profile: its edit form, its widgets, its save.
        return None

    return f"{brain.getURL()}/edit"


def on_after_traversal(event) -> None:
    """Send a user with an incomplete profile to its edit form.

    Subscribed to ``IPubAfterTraversalEvent`` rather than wrapping a view,
    because the point is that there is no page they can reach instead.

    :param event: The publication event.
    :raises Redirect: When the request should be gated, which the publisher
        turns into a 302.
    """
    target = redirect_target(event.request)
    if target is None:
        return
    logger.debug("Profile incomplete; holding the request at %s", target)
    raise Redirect(target)


__all__ = ["BYPASS_ROLES", "ENFORCE_RECORD", "on_after_traversal", "redirect_target"]
