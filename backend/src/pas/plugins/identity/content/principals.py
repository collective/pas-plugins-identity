"""Telling core that this layer's content types are the site's users and groups.

Core can create a user or a group as content without knowing what type that
is: it reads four registry records naming the portal type and the container,
and it checks the type provides ``IUserContent`` or ``IGroupContent``. This
module is what points those records at ``Profile`` and ``IdentityGroup``.

**Why a subscriber and not a value in ``registry.xml``.** Where Profiles live
is itself configurable, and
:func:`~pas.plugins.identity.content.setuphandlers.post_install` explains why
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
from pas.plugins.identity.content.catalog import GROUP_PORTAL_TYPE
from pas.plugins.identity.content.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.content.container import GROUP
from pas.plugins.identity.content.container import GROUP_ID_RECORD
from pas.plugins.identity.content.container import GROUP_PARENT_RECORD
from pas.plugins.identity.content.container import ID_RECORD
from pas.plugins.identity.content.container import PARENT_RECORD
from pas.plugins.identity.content.container import PROFILE
from pas.plugins.identity.content.container import settings
from pas.plugins.identity.core.pas.plugin import GROUP_CONTAINER_PATH_RECORD
from pas.plugins.identity.core.pas.plugin import GROUP_CONTENT_TYPE_RECORD
from pas.plugins.identity.core.pas.plugin import USER_CONTAINER_PATH_RECORD
from pas.plugins.identity.core.pas.plugin import USER_CONTENT_TYPE_RECORD
from plone import api


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
    """Point core's four principal records at this layer.

    Users and groups are pointed separately now that they may be filed apart.
    On a site that has not asked for that they resolve to the same path, which
    is what the group settings falling back to the Profile ones buys: nothing
    to migrate, and one place to look when they differ.

    Idempotent, and safe to call before either container exists.
    """
    profile_path = container_path(PROFILE)
    group_path = container_path(GROUP)
    for record, value in (
        (USER_CONTENT_TYPE_RECORD, PROFILE_PORTAL_TYPE),
        (USER_CONTAINER_PATH_RECORD, profile_path),
        (GROUP_CONTENT_TYPE_RECORD, GROUP_PORTAL_TYPE),
        (GROUP_CONTAINER_PATH_RECORD, group_path),
    ):
        api.portal.set_registry_record(record, value)
    logger.info(
        "Core principal records now point at %r for users and %r for groups",
        profile_path,
        group_path,
    )


def clear_core_records() -> None:
    """Hand adding users and groups back to the stock plugins.

    Called on uninstall. Leaving the records set would name a content type
    the site no longer has -- core would decline on the type check and fall
    back anyway, so this is tidiness rather than a fix, but a registry record
    describing something that does not exist is a question somebody will
    eventually have to answer.
    """
    for record in (
        USER_CONTENT_TYPE_RECORD,
        USER_CONTAINER_PATH_RECORD,
        GROUP_CONTENT_TYPE_RECORD,
        GROUP_CONTAINER_PATH_RECORD,
    ):
        api.portal.set_registry_record(record, "")


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


__all__ = [
    "WATCHED_RECORDS",
    "clear_core_records",
    "container_path",
    "on_container_setting_changed",
    "sync_core_records",
]
