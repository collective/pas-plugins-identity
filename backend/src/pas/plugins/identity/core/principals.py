"""Telling core that this layer's content types are the site's users and groups.

Core can create a user or a group as content without knowing what type that
is: it reads four registry records naming the portal type and the container,
and it checks the type provides ``IUserContent`` or ``IGroupContent``. This
module is what points those records at ``UserProfile`` and ``UserGroup``.

**Why a subscriber and not a value in ``registry.xml``.** Where Profiles live
is itself configurable, and
:func:`~pas.plugins.identity.setuphandlers.post_install` explains why
this package must not decide it at install time: a profile layered on top of
this one -- a policy package, a demo, anything with its own ``registry.xml``
-- sets the container's parent and id *after* this layer's handler has run.
A path written during install therefore names the container the layered
profile is about to move, and a static value in XML is that mistake in a
different file.

So the path is derived, and re-derived whenever the settings it depends on
change. An operator who moves the container in the control panel gets core
following them, with no reinstall and nothing to remember.

**What this does not do is create the container.** That stays lazy, for the
reason it always was. The consequence is worth stating plainly rather than
discovering: until the container exists, core has nowhere to put a user,
declines, and ``source_users`` adds them as before -- so on a site where
nobody has signed in yet, ``api.user.create`` still mints no Profile. That is
strictly better than the old behaviour, where it never did, and it is not the
whole fix.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.catalog import GROUP_PORTAL_TYPE
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.container import grant_add_permission
from pas.plugins.identity.core.container import grant_add_permissions
from pas.plugins.identity.core.container import GROUP
from pas.plugins.identity.core.container import GROUP_ID_RECORD
from pas.plugins.identity.core.container import GROUP_PARENT_RECORD
from pas.plugins.identity.core.container import ID_RECORD
from pas.plugins.identity.core.container import PARENT_RECORD
from pas.plugins.identity.core.container import PROFILE
from pas.plugins.identity.core.container import settings
from pas.plugins.identity.core.pas.plugin import GROUP_CONTAINER_PATH_RECORD
from pas.plugins.identity.core.pas.plugin import GROUP_CONTENT_TYPE_RECORD
from pas.plugins.identity.core.pas.plugin import USER_CONTAINER_PATH_RECORD
from pas.plugins.identity.core.pas.plugin import USER_CONTENT_TYPE_RECORD
from plone import api
from plone.api.exc import CannotGetPortalError
from plone.api.exc import InvalidParameterError
from zope.interface.interfaces import ComponentLookupError


#: The records whose value the container path is derived from. A change to
#: either one has to be followed.
WATCHED_RECORDS = frozenset({
    PARENT_RECORD,
    ID_RECORD,
    GROUP_PARENT_RECORD,
    GROUP_ID_RECORD,
})


def container_path(kind: str = PROFILE) -> str:
    """Return a principal container's path, relative to the site root.

    Derived rather than stored, so it cannot drift from the settings it comes
    from. Names where the container *will* be when it does not exist yet,
    which is what lets core decline cleanly instead of guessing.

    :param kind: :data:`PROFILE` or :data:`GROUP`.
    :returns: The path, without a leading slash.
    """
    config = settings(kind)
    parent = (config["parent"] or "").strip("/")
    container_id = (config["id"] or "").strip("/")
    if not container_id:
        return ""
    return f"{parent}/{container_id}" if parent else container_id


def sync_core_records() -> None:
    """Point the four principal records at this package's own types.

    Users and groups are pointed separately now that they may be filed apart.
    On a site that has not asked for that they resolve to the same path, which
    is what the group settings falling back to the Profile ones buys: nothing
    to migrate, and one place to look when they differ.

    Idempotent, and safe to call before either container exists.

    **Also safe to call before the records themselves exist**, which is not a
    hypothetical. This runs from a subscriber to every registry write, and one
    of the writes that reaches it is the profile's own ``registry.xml``
    creating the container settings -- during the very import step that
    creates the records being written here. The two settings files used to
    belong to two profiles, so the core half was always already in place;
    merging them inverted the order, and the demo stack refused to start with
    ``Cannot find a record with name
    'pas.plugins.identity.user_content_type'``.

    Declining is correct rather than merely quiet: ``post_install`` runs this
    again once every record exists, so the site ends up with the same values
    either way.
    """
    try:
        profile_path = container_path(PROFILE)
        group_path = container_path(GROUP)
        for record, value in (
            (USER_CONTENT_TYPE_RECORD, PROFILE_PORTAL_TYPE),
            (USER_CONTAINER_PATH_RECORD, profile_path),
            (GROUP_CONTENT_TYPE_RECORD, GROUP_PORTAL_TYPE),
            (GROUP_CONTAINER_PATH_RECORD, group_path),
        ):
            api.portal.set_registry_record(record, value)
    except InvalidParameterError as error:
        # Either half can be the missing one: the settings read above, in a
        # site that has uninstalled, or the records written below, in a site
        # that is mid-install.
        logger.debug("Not syncing the principal records yet: %s", error)
        return
    logger.info(
        "Core principal records now point at %r for users and %r for groups",
        profile_path,
        group_path,
    )


def on_container_setting_changed(event) -> None:
    """Re-derive the container path when its settings change.

    Guarded on the record name for two reasons: every registry write in the
    site fires this event, and the writes :func:`sync_core_records` makes
    would otherwise call it again.

    :param event: A ``plone.registry`` record-modified event.
    """
    if getattr(event.record, "__name__", None) not in WATCHED_RECORDS:
        return
    sync_core_records()
    # The folder the records now name is where principals go, so it is the
    # folder that has to allow them. The old one keeps its grant: it may still
    # hold Profiles, and revoking it would strand whoever is filing them.
    grant_add_permissions()


def on_folder_added(obj, event) -> None:
    """Grant the add permissions when a configured container appears.

    The container is not always created by this package. A policy profile
    layered on top may ship it as content, an operator may make the folder by
    hand, and the federation demo does both -- and none of those paths goes
    through :func:`~pas.plugins.identity.core.container.get_container`,
    which is where the grant otherwise happens.

    Neither of the two other grant points helps there. The install handler
    only sees a container that already exists, and the settings subscriber
    only fires when a *record* changes; a folder created afterwards, at the
    path the records already name, is the case both of them miss. The symptom
    is a container that looks correct and refuses every user filed into it.

    Fires for every folderish object added anywhere in the site, and answers
    with two registry reads and a string compare for all but the one that
    matters.

    :param obj: The object just added.
    :param event: The object-added event, unused.
    """
    try:
        wanted = {kind: container_path(kind) for kind in (PROFILE, GROUP)}
        portal_path = api.portal.get().getPhysicalPath()
    except (InvalidParameterError, ComponentLookupError, CannotGetPortalError):
        # Two different "not here" answers, and both are ordinary.
        #
        # ``InvalidParameterError`` is a site that does not have this add-on
        # installed -- another Plone site in the same instance, or this one
        # after an uninstall. The records do not exist, so there is no
        # configured container and nothing to grant.
        #
        # ``ComponentLookupError`` is a site that does not exist *yet*. A Plone
        # site is itself folderish, so this fires while it is being added to
        # the application root -- before ``plone.app.registry`` has been
        # applied and therefore before there is a registry to read. Missing
        # that case made every site creation fail with a traceback and a 500,
        # and no test caught it: ``plone.app.testing`` builds its site in
        # ``PLONE_FIXTURE``, before this package's ZCML is loaded, so the
        # subscriber that breaks site creation is not registered when the test
        # suite creates one.
        #
        # This subscriber is not bound to a browser layer -- it cannot be, the
        # objects it fires for carry no request -- so declining here is the
        # only thing keeping it inert where it has no business acting.
        return
    path = "/".join(obj.getPhysicalPath()[len(portal_path) :])
    for kind, configured in wanted.items():
        if configured and configured == path:
            grant_add_permission(obj, kind)


__all__ = [
    "WATCHED_RECORDS",
    "container_path",
    "on_container_setting_changed",
    "on_folder_added",
    "sync_core_records",
]
