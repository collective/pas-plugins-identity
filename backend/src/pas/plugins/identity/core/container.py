"""Where Profiles and Groups are stored, and who decides.

The add-on does not get to dictate the site's structure, so the container's
parent, id, title and type are all registry records rather than constants. A
project that keeps member data under ``/intranet/people`` sets four values; a
project that is happy with ``/identity-profiles`` sets none.

The catalog is deliberately *not* scoped to this container (Érico,
2026-08-21). It indexes a Profile wherever it is in the site, which is what
makes the move and rename steps of the churn test meaningful rather
than forbidden: moving a Profile out of the configured container must keep it
working, because an operator reorganising content has not deauthenticated
anybody.

What the container *is* for is answering "where does a new Profile go" --
asked at install and at first login and nowhere else. It is also *how* that
question is answered exclusively: both add permissions are granted to no role
in ``rolemap.xml`` and granted to administrators on the container itself, so
a ``UserProfile`` may be created in the folder configured for it and nowhere
else in the site. Filing them somewhere else is a grant an operator makes
deliberately, on a folder they chose.

Groups get their own four records, and they default to the Profile
container's. A site that wants principals filed together sets nothing and
gets exactly what it had; a site that wants ``/groups`` beside ``/profiles``
sets ``group_container_id`` and core follows. The defaulting is what keeps
this from being a migration: an existing site has no group records set, and
the group container it resolves to is the one its groups are already in.
"""

from pas.plugins.identity import logger
from plone import api
from plone.app.dexterity.behaviors.exclfromnav import IExcludeFromNavigation
from plone.base.interfaces import IPloneSiteRoot
from plone.dexterity.content import Container
from plone.dexterity.utils import resolveDottedName
from Products.CMFCore.interfaces import IFolderish
from Products.CMFPlone.Portal import PloneSite


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

#: The two kinds of principal container this layer knows about. A kind names
#: the record set to read; everything else about them is identical.
PROFILE = "profile"
GROUP = "group"

#: Where a group container's parent lives. Empty falls back to the Profile
#: container's parent, as do the three below -- see the module docstring.
GROUP_PARENT_RECORD = f"{PREFIX}.group_container_parent"

#: Id of the group container within its parent. This is the record that
#: decides whether groups have a container of their own at all: empty means
#: they share the Profile container.
GROUP_ID_RECORD = f"{PREFIX}.group_container_id"

#: Title given to the group container when this package creates it.
GROUP_TITLE_RECORD = f"{PREFIX}.group_container_title"

#: ``portal_type`` used when this package creates the group container.
GROUP_TYPE_RECORD = f"{PREFIX}.group_container_type"

#: Record names per kind, in the order :func:`settings` reads them.
RECORDS = {
    PROFILE: (PARENT_RECORD, ID_RECORD, TITLE_RECORD, TYPE_RECORD),
    GROUP: (
        GROUP_PARENT_RECORD,
        GROUP_ID_RECORD,
        GROUP_TITLE_RECORD,
        GROUP_TYPE_RECORD,
    ),
}

#: Types tried, in order, when the configured one may not be added where the
#: container goes. ``Document`` is first because it is the folderish type a
#: Volto site has, and Volto is the distribution that makes the default
#: unusable.
CONTAINER_TYPE_FALLBACKS = ("Document", "Folder")

#: Add permission per kind, by **title** rather than by ZCML id: that is what
#: ``manage_permission`` and ``rolemap.xml`` both name a permission by.
ADD_PERMISSIONS = {
    PROFILE: "pas.plugins.identity: Add User Profile",
    GROUP: "pas.plugins.identity: Add User Group",
}

#: Roles that may add a principal *inside a container*. Granted there and
#: nowhere else -- ``rolemap.xml`` gives these permissions to no role at all,
#: so this local grant is the only thing that makes either type addable
#: anywhere in the site.
#:
#: ``Manager`` is on the list because every machine path that mints a
#: principal -- first login, ``api.user.create``, ``api.group.create`` --
#: elevates to it. Take it off and the layer stops working rather than
#: becoming stricter.
ADD_ROLES = ("Manager", "Site Administrator")


class ContainerNotFound(LookupError):
    """The configured parent path does not resolve to a folder in this site."""


def settings(kind: str = PROFILE) -> dict[str, str]:
    """Read a container's four settings from the registry.

    A group container with no id of its own *is* the Profile container, and
    the fallback is whole rather than per-record: a site that names a group
    container but no parent for it means "beside the Profiles", not "at the
    portal root". Mixing the two record sets would make the group container's
    location depend on which of its four records happened to be set.

    :param kind: :data:`PROFILE` or :data:`GROUP`.
    :returns: Mapping with ``parent``, ``id``, ``title`` and ``type``.
    """
    parent_record, id_record, title_record, type_record = RECORDS[kind]
    if (
        kind == GROUP
        and not (api.portal.get_registry_record(id_record, default="") or "").strip()
    ):
        return settings(PROFILE)
    return {
        "parent": (
            api.portal.get_registry_record(parent_record, default="") or ""
        ).strip("/"),
        "id": api.portal.get_registry_record(id_record),
        "title": api.portal.get_registry_record(title_record),
        "type": api.portal.get_registry_record(type_record),
    }


def get_parent(kind: str = PROFILE) -> PloneSite | Container:
    """Return the object a container lives in.

    :param kind: :data:`PROFILE` or :data:`GROUP`.
    :returns: The portal root, or the folder named by the parent record.
    :raises ContainerNotFound: If the configured path does not resolve.
    """
    portal = api.portal.get()
    path = settings(kind)["parent"]
    if not path:
        return portal
    parent = portal.unrestrictedTraverse(path, None)
    if parent is None:
        raise ContainerNotFound(
            f"{RECORDS[kind][0]} points at {path!r}, which does not exist in this site."
        )
    return parent


def _creatable_type(parent, configured: str, type_record: str) -> str:
    """Return a container type that may actually be added to ``parent``.

    The configured type is used whenever the parent allows it, which is the
    ordinary case and the only one on a site whose structure someone has
    thought about.

    It is not the case on a site built from the ``volto`` distribution, which
    does not allow ``Folder`` at the portal root at all -- and ``Folder`` is
    what this package ships as the default. Installing the layer there failed
    with a bare "Disallowed subobject type", naming neither the record to
    change nor the fact that a record exists. Since Volto is the frontend this
    package ships, that is not an edge case to document.

    Folderish types only, and that filter is not paranoia. ``Document`` is
    the first fallback because ``plone.volto`` makes it folderish, and it is
    the type a Volto site has where ``Folder`` is refused -- but the same id
    names an ordinary *item* on a site without that add-on. Creating one as a
    principal container produced a Document at the configured path that could
    hold nothing and could not even be granted the add permission, which
    surfaced as ``The permission ... is invalid`` from a line about
    permissions rather than about types.

    :param parent: The object the container will be created in.
    :param configured: The type named by the container's type record.
    :param type_record: That record's name, so the message names the record
        an operator would actually change.
    :returns: The configured type, or the first allowed fallback.
    :raises ContainerNotFound: When nothing addable here can hold Profiles.
    """
    allowed = [
        fti.getId() for fti in parent.allowedContentTypes() if _holds_content(fti)
    ]
    if configured in allowed:
        return configured

    for fallback in CONTAINER_TYPE_FALLBACKS:
        if fallback in allowed:
            logger.info(
                "%s is %r, which %s does not allow; creating the "
                "container as %r instead. Set the record to silence this.",
                type_record,
                configured,
                "/".join(parent.getPhysicalPath()),
                fallback,
            )
            return fallback

    raise ContainerNotFound(
        f"{type_record} is {configured!r}, which cannot be added to "
        f"{'/'.join(parent.getPhysicalPath())} as a folder, and none of "
        f"{CONTAINER_TYPE_FALLBACKS} can either. Folderish types allowed "
        f"here: {allowed}."
    )


def _holds_content(fti) -> bool:
    """Report whether objects of a type can contain other objects.

    Asked of the class the FTI names rather than of an instance, because the
    answer is needed before anything is created. A type whose class will not
    import is not one to file principals in, and a broken FTI must not break
    adding a user.

    Every failure is the same answer, and there are three of them: a type
    information object with no ``klass`` at all, a dotted name that does not
    resolve, and a name that resolves to something that is not a class --
    ``implementedBy`` refuses a module with a ``TypeError`` rather than
    answering false.

    :param fti: A type information object.
    :returns: Whether its objects are folderish.
    """
    try:
        klass = resolveDottedName(getattr(fti, "klass", "") or "")
        return IFolderish.implementedBy(klass)
    except (AttributeError, ImportError, TypeError, ValueError):
        return False


def grant_add_permission(container: Container, kind: str = PROFILE) -> bool:
    """Let the configured roles add this kind of principal in ``container``.

    The site-wide answer is "nobody": ``rolemap.xml`` declares both add
    permissions with no role and no acquisition, so a ``UserProfile`` is
    addable in exactly the folders that say so, and a folder says so only
    because this ran on it. Filing users somewhere else is then a deliberate
    grant on a deliberate folder rather than a side effect of being an
    administrator.

    Idempotent, and it checks before it writes: this is called from the
    install handler and from the settings-changed subscriber as well as at
    creation, and a permission map rewritten on every registry change is a
    ZODB write per keystroke in the control panel.

    :param container: The folder principals of this kind are filed in.
    :param kind: :data:`PROFILE` or :data:`GROUP`.
    :returns: Whether anything was written.
    """
    permission = ADD_PERMISSIONS[kind]
    granted = {
        entry["name"]
        for entry in container.rolesOfPermission(permission)
        if entry["selected"]
    }
    acquired = bool(container.acquiredRolesAreUsedBy(permission))
    if granted == set(ADD_ROLES) and not acquired:
        return False
    container.manage_permission(permission, roles=ADD_ROLES, acquire=0)
    logger.info(
        "Granted %r to %s on %s",
        permission,
        ", ".join(ADD_ROLES),
        "/".join(container.getPhysicalPath()),
    )
    return True


def grant_add_permissions() -> list[str]:
    """Grant each kind's add permission on the container that holds it.

    Called where the answer may have changed without anything creating a
    container: after an install, and after somebody points the settings at a
    different folder. A container that does not exist yet is skipped rather
    than created -- see
    :func:`~pas.plugins.identity.setuphandlers.post_install` for why
    creating one eagerly is the mistake this package already made once.

    The two kinds resolve to the same folder on a site that has not separated
    them, which grants both permissions there and is exactly right.

    :returns: Paths of the containers that were written to.
    """
    written = []
    for kind in (PROFILE, GROUP):
        try:
            container = get_container(kind=kind)
        except ContainerNotFound:
            continue
        if container is None:
            continue
        if grant_add_permission(container, kind):
            written.append("/".join(container.getPhysicalPath()))
    return written


def get_container(create: bool = False, kind: str = PROFILE) -> Container | None:
    """Return a configured principal container.

    :param create: Create the container when it is missing. Off by default so
        that read paths -- the consistency check, the control panel -- can ask
        without a side effect.
    :param kind: :data:`PROFILE` or :data:`GROUP`. Defaulted, and left as the
        second argument, so every existing caller keeps working unchanged.
    :returns: The container, or ``None`` when it does not exist and ``create``
        is false.
    :raises ContainerNotFound: If the configured parent path does not resolve.
    """
    parent = get_parent(kind)
    config = settings(kind)
    container = parent.get(config["id"])
    if container is not None or not create:
        return container

    container = api.content.create(
        container=parent,
        type=_creatable_type(parent, config["type"], RECORDS[kind][3]),
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
    # Nothing may be added here until this runs, including by the machinery
    # that is about to file the first Profile: the add permissions are granted
    # to no role site-wide, so the container is the whole lock.
    #
    # Both kinds, not just the one asked for. On a site that has not separated
    # them the two resolve to this same folder, and granting only the kind
    # that happened to be created first leaves the other unaddable in the one
    # place it is supposed to go.
    grant_add_permissions()
    logger.info(
        "Created %s container at %s",
        kind,
        "/".join(container.getPhysicalPath()),
    )
    return container


def is_site_root(obj: object) -> bool:
    """Return whether an object is the Plone site root.

    Used by the uninstall handler, which removes the container it created but
    must never try to remove the portal.

    :param obj: The object to test.
    :returns: ``True`` for the site root.
    """
    return IPloneSiteRoot.providedBy(obj)
