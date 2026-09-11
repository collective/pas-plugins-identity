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

The type is ``PrincipalsContainer`` unless a record names another, and a
parent that will not take the type named is an error that says so. This
module used to fall back to ``Document`` and then ``Folder`` instead, which
filed principals in whatever the parent happened to allow and reported the
choice in a log line.
"""

from pas.plugins.identity import logger
from plone import api
from plone.app.dexterity.behaviors.exclfromnav import IExcludeFromNavigation
from plone.base.interfaces import IPloneSiteRoot
from plone.dexterity.content import Container
from plone.dexterity.utils import resolveDottedName
from plone.restapi.behaviors import IBlocks
from Products.CMFCore.interfaces import IFolderish
from Products.CMFPlone.Portal import PloneSite
from uuid import uuid4


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

#: The type this package ships for a container, and what both type records
#: name by default. See :mod:`pas.plugins.identity.core.contents.principals`.
CONTAINER_PORTAL_TYPE = "PrincipalsContainer"

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

#: The permission to write a Profile's ``login``, by **title**, for the same
#: reason as :data:`ADD_PERMISSIONS`.
LOGIN_PERMISSION = "pas.plugins.identity: Edit Profile Login"

#: Roles that may write a ``login`` *inside a container*, which in practice
#: means on the add form: an add form checks a field's write permission
#: against the folder, an edit form against the object.
#:
#: That split is the whole mechanism behind "a Manager may change a login
#: after the account exists". ``rolemap.xml`` grants the permission to
#: ``Manager`` alone and ``user_profile_workflow`` manages it in every state,
#: so once a Profile exists nobody else holds it. Here the same roles that may
#: file a principal may name it, or a Site Administrator would meet an add
#: form with no login on it and a required field they cannot fill.
LOGIN_ROLES = ADD_ROLES


class ContainerNotFound(LookupError):
    """A configured container cannot be found, or cannot be created.

    Either the parent path does not resolve to a folder in this site, or the
    folder it resolves to will not take the configured container type.
    """


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


def _check_addable(parent, type_name: str, type_record: str) -> None:
    """Refuse a container type that ``parent`` will not take.

    There is no fallback, and there used to be. When the configured type was
    refused, this tried ``Document`` and then ``Folder``, because the
    ``volto`` distribution does not allow ``Folder`` at the portal root and
    ``Folder`` was the shipped default. ``PrincipalsContainer`` is globally
    allowed, so the site root takes it on every distribution, and a parent
    that still refuses it is a folder somebody restricted on purpose.
    Guessing past that decision filed principals in a type nobody chose.

    Folderish types only. A ``Document`` is an ordinary item on a site
    without ``plone.volto``, and a container that can hold nothing cannot be
    granted the add permission either -- which surfaced as ``The permission
    ... is invalid``, from a line about permissions rather than about types.

    :param parent: The object the container will be created in.
    :param type_name: The type named by the container's type record.
    :param type_record: That record's name, so the message names the record
        an operator would actually change.
    :raises ContainerNotFound: When ``parent`` will not take ``type_name`` as
        a folder. The message names the record, the type and the parent.
    """
    allowed = sorted(
        fti.getId() for fti in parent.allowedContentTypes() if _holds_content(fti)
    )
    if type_name in allowed:
        return
    raise ContainerNotFound(
        f"{type_record} is {type_name!r}, which cannot be added to "
        f"{'/'.join(parent.getPhysicalPath())} as a folder. Folderish types "
        f"addable there: {allowed}."
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
    written = _grant(container, ADD_PERMISSIONS[kind], ADD_ROLES)
    if kind == PROFILE:
        # Only a Profile has a login. Granted here rather than in the rolemap
        # so that the answer differs between the container and the object;
        # see :data:`LOGIN_ROLES`.
        written = _grant(container, LOGIN_PERMISSION, LOGIN_ROLES) or written
    return written


def _grant(container: Container, permission: str, roles: tuple[str, ...]) -> bool:
    """Give ``roles`` a permission on ``container``, unless they already have it.

    :param container: The folder to write the permission map on.
    :param permission: The permission, by title.
    :param roles: The roles to grant it to, and the only ones.
    :returns: Whether anything was written.
    """
    granted = {
        entry["name"]
        for entry in container.rolesOfPermission(permission)
        if entry["selected"]
    }
    acquired = bool(container.acquiredRolesAreUsedBy(permission))
    if granted == set(roles) and not acquired:
        return False
    container.manage_permission(permission, roles=list(roles), acquire=0)
    logger.info(
        "Granted %r to %s on %s",
        permission,
        ", ".join(roles),
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
    :raises ContainerNotFound: If the configured parent path does not resolve,
        or ``create`` is true and that parent will not take the configured
        type.
    """
    parent = get_parent(kind)
    config = settings(kind)
    container = parent.get(config["id"])
    if container is not None or not create:
        return container

    _check_addable(parent, config["type"], RECORDS[kind][3])
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
    # Volto draws a page that has a ``blocks`` field from its blocks and
    # nothing else, so a container created here with none would be a blank
    # page, without even its title. Same condition as above: only when the
    # type carries the behavior.
    if IBlocks.providedBy(container):
        block_id = str(uuid4())
        container.blocks = {block_id: {"@type": "title"}}
        container.blocks_layout = {"items": [block_id]}
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
