"""Where Profiles are stored, and who decides.

The add-on does not get to dictate the site's structure, so the container's
parent, id, title and type are all registry records rather than constants. A
project that keeps member data under ``/intranet/people`` sets four values; a
project that is happy with ``/identity-profiles`` sets none.

The catalog is deliberately *not* scoped to this container (Érico,
2026-08-21). It indexes a Profile wherever it is in the site, which is what
makes the move and rename steps of the churn test (§8.3) meaningful rather
than forbidden: moving a Profile out of the configured container must keep it
working, because an operator reorganising content has not deauthenticated
anybody.

What the container *is* for is answering "where does a new Profile go" --
asked at install and at first login (Gate 6c) and nowhere else.
"""

from pas.plugins.identity import logger
from plone import api
from plone.app.dexterity.behaviors.exclfromnav import IExcludeFromNavigation
from plone.base.interfaces import IPloneSiteRoot
from typing import Any


#: Registry record prefix for the four container settings.
PREFIX = "pas.plugins.identity"

#: Path of the container's parent, relative to the portal root. Empty means
#: the portal root itself.
PARENT_RECORD = f"{PREFIX}.profile_container_parent"

#: Id of the container within its parent.
ID_RECORD = f"{PREFIX}.profile_container_id"

#: Title given to the container when this package creates it. Ignored when the
#: container already exists -- renaming somebody's folder is not our business.
TITLE_RECORD = f"{PREFIX}.profile_container_title"

#: ``portal_type`` used when this package creates the container.
TYPE_RECORD = f"{PREFIX}.profile_container_type"


class ContainerNotFound(LookupError):
    """The configured parent path does not resolve to a folder in this site."""


def settings() -> dict[str, str]:
    """Read the four container settings from the registry.

    :returns: Mapping with ``parent``, ``id``, ``title`` and ``type``.
    """
    return {
        "parent": (api.portal.get_registry_record(PARENT_RECORD) or "").strip("/"),
        "id": api.portal.get_registry_record(ID_RECORD),
        "title": api.portal.get_registry_record(TITLE_RECORD),
        "type": api.portal.get_registry_record(TYPE_RECORD),
    }


def get_parent() -> Any:
    """Return the object the container lives in.

    :returns: The portal root, or the folder named by the parent record.
    :raises ContainerNotFound: If the configured path does not resolve.
    """
    portal = api.portal.get()
    path = settings()["parent"]
    if not path:
        return portal
    parent = portal.unrestrictedTraverse(path, None)
    if parent is None:
        raise ContainerNotFound(
            f"{PARENT_RECORD} points at {path!r}, which does not exist in this site."
        )
    return parent


def get_container(create: bool = False) -> Any | None:
    """Return the configured Profile container.

    :param create: Create the container when it is missing. Off by default so
        that read paths -- the consistency check, the control panel -- can ask
        without a side effect.
    :returns: The container, or ``None`` when it does not exist and ``create``
        is false.
    :raises ContainerNotFound: If the configured parent path does not resolve.
    """
    parent = get_parent()
    config = settings()
    container = parent.get(config["id"])
    if container is not None or not create:
        return container

    container = api.content.create(
        container=parent,
        type=config["type"],
        id=config["id"],
        title=config["title"],
    )
    # A container of Profiles is not site content: keeping it out of navigation
    # spares every site the "why is there an empty folder in my menu" ticket.
    # Exclusion is a behavior, and the container type is the project's choice,
    # so it is applied only when that type actually carries it. Asked with
    # ``hasattr`` this would always answer yes: Dexterity's ``__getattr__``
    # serves schema defaults, and acquisition covers the rest.
    if IExcludeFromNavigation.providedBy(container):
        container.exclude_from_nav = True
        container.reindexObject(idxs=["exclude_from_nav"])
    logger.info(
        "Created profile container at %s", "/".join(container.getPhysicalPath())
    )
    return container


def is_site_root(obj: Any) -> bool:
    """Return whether an object is the Plone site root.

    Used by the uninstall handler, which removes the container it created but
    must never try to remove the portal.

    :param obj: Any object.
    :returns: ``True`` for the site root.
    """
    return IPloneSiteRoot.providedBy(obj)
