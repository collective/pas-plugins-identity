"""The PAS plugin.

Implements extraction, authentication, credentials reset and -- off by default
-- challenge. It deliberately does **not** implement properties, enumeration,
groups, roles or user adding: on first login it *decorates* the stock
``source_users`` and ``mutable_properties`` plugins instead, which is what lets
core install and work with no extras.

Extraction and authentication only ever run at callback time. An ordinary
request rides the ``plone.session`` ticket or the ``jwt_auth`` token that this
plugin handed out, and never reaches the network.
"""

from AccessControl.class_init import InitializeClass
from pas.plugins.identity import logger
from pas.plugins.identity.core.audit import AuditLog
from pas.plugins.identity.core.events import ExternalIdentityAuthenticated
from pas.plugins.identity.core.events import IdentityLinked
from pas.plugins.identity.core.events import IdentityUnlinked
from pas.plugins.identity.core.flows.magiclink import MagicLinkStore
from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.interfaces import ICredentialStorage
from pas.plugins.identity.core.interfaces import IGroupContent
from pas.plugins.identity.core.interfaces import IIdentityPlugin
from pas.plugins.identity.core.interfaces import IOwnsUserProperties
from pas.plugins.identity.core.interfaces import IUserContent
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.interfaces import LockoutRefused
from pas.plugins.identity.core.logout import LogoutJTIStore
from pas.plugins.identity.core.pas import CREDENTIALS_KEY
from pas.plugins.identity.core.pas import EXTRACTOR
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.core.pas import PLUGIN_TITLE
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from pas.plugins.identity.core.store import IdentityRecord
from pas.plugins.identity.core.store import IdentityStore
from Products.PlonePAS.interfaces.group import IGroupManagement
from Products.PluggableAuthService.interfaces.plugins import IAuthenticationPlugin
from Products.PluggableAuthService.interfaces.plugins import IChallengePlugin
from Products.PluggableAuthService.interfaces.plugins import ICredentialsResetPlugin
from Products.PluggableAuthService.interfaces.plugins import IExtractionPlugin
from Products.PluggableAuthService.interfaces.plugins import IPropertiesPlugin
from Products.PluggableAuthService.interfaces.plugins import IUserAdderPlugin
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.plugins.ZODBUserManager import ZODBUserManager
from Products.PluggableAuthService.utils import classImplements
from Products.PluggableAuthService.utils import url_local
from urllib.parse import quote
from uuid import uuid4
from zope.event import notify
from zope.interface import implementer
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse


#: Where the provider picker lives, for the optional challenge plugin.
#: ``/login`` rather than a view of this package's own: the Volto add-on
#: overrides that route with the provider picker, and a Classic site serves
#: Plone's login form there. A name only this package knew would be served by
#: neither.
LOGIN_VIEW = "login"


#: What a provider may mint its userids from. ``uuid`` is the default and
#: the only one that is not a claim.
USERID_SOURCES = ("uuid", "username", "email", "subject")


def _userid_candidate(source: str, claims: Claims, subject: str) -> str:
    """Return the raw value a userid should be built from.

    :param source: One of :data:`USERID_SOURCES`.
    :param claims: Normalized claims.
    :param subject: The provider-side subject.
    :returns: The raw value, which may be empty.
    """
    if source == "username":
        return str(claims.get("username") or "")
    if source == "email":
        return str(claims.get("email") or "")
    if source == "subject":
        return subject or ""
    return ""


def _available(userid: str) -> bool:
    """Report whether a userid is free to hand out.

    Checked against *every* PAS source, not just this plugin's. That is the
    whole guard: a provider account called ``admin`` must not be handed the
    site's ``admin`` userid and inherit its roles, and the only way to know
    is to ask Plone rather than this plugin's own records.

    :param userid: The candidate.
    :returns: Whether no user already has it.
    """
    from plone import api

    return api.user.get(userid=userid) is None


def mint_userid(
    source: str = "uuid", claims: Claims | None = None, subject: str = ""
) -> str:
    """Mint a canonical userid.

    A random UUID by default: never derived from provider claims, so it
    leaks nothing about where the account came from and cannot change when a
    claim does.

    A provider may instead ask for a readable userid, which is what makes a
    person recognisable in Plone rather than being 32 hex characters. Three
    things follow from that, and all three are handled here: the value is a
    claim, so it is normalized into something usable as an id; it may be
    empty, in which case this falls back to a UUID rather than minting
    something unusable; and it may already belong to somebody, in which case
    a numeric suffix is added until it does not.

    :param source: One of :data:`USERID_SOURCES`.
    :param claims: Normalized claims, when the source needs them.
    :param subject: The provider-side subject, when the source needs it.
    :returns: A userid nobody else holds.
    """
    if source not in USERID_SOURCES or source == "uuid":
        return uuid4().hex

    from plone.i18n.normalizer.interfaces import IIDNormalizer
    from zope.component import getUtility

    raw = _userid_candidate(source, claims or {}, subject)
    normalized = getUtility(IIDNormalizer).normalize(raw) if raw else ""
    if not normalized:
        # A provider that sent nothing usable must not stop the login, and
        # must not mint an empty or partial id either.
        logger.info("No %r to mint a userid from; falling back to a UUID", source)
        return uuid4().hex

    if _available(normalized):
        return normalized
    # Somebody already holds it. Suffix rather than reuse: reusing would hand
    # this identity somebody else's account.
    counter = 2
    while not _available(f"{normalized}-{counter}"):
        counter += 1
    return f"{normalized}-{counter}"


#: Portal type created for a new user. Installing this add-on points it at
#: ``UserProfile`` -- see
#: :func:`~pas.plugins.identity.core.principals.sync_core_records` -- and it
#: stays a record rather than a constant so a site may substitute a user type
#: of its own. A type that does not provide :class:`IUserContent` is refused
#: rather than created.
USER_CONTENT_TYPE_RECORD = "pas.plugins.identity.user_content_type"

#: Where those objects go, relative to the site root. Derived from the
#: container settings, so moving the container in the control panel moves
#: this with it.
USER_CONTAINER_PATH_RECORD = "pas.plugins.identity.user_container_path"

#: Portal type created for a new group, ``UserGroup`` unless a site says
#: otherwise.
GROUP_CONTENT_TYPE_RECORD = "pas.plugins.identity.group_content_type"

#: Where those objects go, relative to the site root.
GROUP_CONTAINER_PATH_RECORD = "pas.plugins.identity.group_container_path"


def _reindex(obj) -> None:
    """Announce a write to whatever indexes this object.

    A membership change nobody reindexed is a membership change nobody can
    see: the layer serving these objects answers out of catalog metadata,
    which is the whole reason it never wakes one.

    :param obj: The object that changed.
    """
    from zope.lifecycleevent import modified

    modified(obj)


def _record(name: str) -> str:
    """Read a string registry record, tolerating a site that has none.

    :param name: Full dotted record name.
    :returns: The value, or an empty string.
    """
    from plone import api

    return (api.portal.get_registry_record(name, default="") or "").strip()


@implementer(IIdentityPlugin)
class IdentityPlugin(BasePlugin):
    """Multi-provider external authentication with identity linking."""

    meta_type = "Identity Plugin"
    security = None  # set by InitializeClass below
    manage_options = BasePlugin.manage_options

    #: Whether to act as an ``IChallengePlugin``. Off by default: a
    #: site that turns this on redirects anonymous 401s to the provider
    #: picker instead of the stock login form.
    challenge_enabled = False

    def __init__(self, id: str = PLUGIN_ID, title: str = PLUGIN_TITLE) -> None:
        """Create the plugin and its identity store.

        :param id: Object id inside ``acl_users``.
        :param title: Title shown in the ZMI.
        """
        self.id = id
        self.title = title
        self._store = IdentityStore()
        self._audit = AuditLog()
        self._magic_links = MagicLinkStore()
        self._logout_jtis = LogoutJTIStore()

    @property
    def store(self) -> IdentityStore:
        """Return the identity store.

        :returns: The store persisted inside this plugin.
        """
        return self._store

    @property
    def audit(self) -> AuditLog:
        """Return the audit log.

        Created on demand as well as in the constructor, so a plugin that
        predates the audit log gains one on first use rather than raising --
        an upgrade step would do the same thing later and less kindly.

        :returns: The log persisted inside this plugin.
        """
        log = getattr(self, "_audit", None)
        if log is None:
            log = self._audit = AuditLog()
        return log

    @property
    def magic_links(self) -> MagicLinkStore:
        """Return the magic-link store.

        Created on demand as well as in the constructor, for the same reason
        as :attr:`audit`.

        :returns: The store persisted inside this plugin.
        """
        store = getattr(self, "_magic_links", None)
        if store is None:
            store = self._magic_links = MagicLinkStore()
        return store

    @property
    def logout_jtis(self) -> LogoutJTIStore:
        """Return the spent logout-token identifiers.

        Its own store rather than a corner of the magic-link burn list: both
        burn a ``jti``, but one is this site's own token and the other is a
        provider's, and a shared namespace between two issuers is a
        collision waiting for somebody to explain it.

        Created on demand as well as in the constructor, for the same reason
        as :attr:`audit`.

        :returns: The store persisted inside this plugin.
        """
        store = getattr(self, "_logout_jtis", None)
        if store is None:
            store = self._logout_jtis = LogoutJTIStore()
        return store

    # ------------------------------------------------------------------
    # IExtractionPlugin
    # ------------------------------------------------------------------

    def extractCredentials(self, request: HTTPRequest) -> JSONDict:
        """Extract credentials deposited by the callback view.

        Nothing else in the request is inspected, so this is a dictionary
        lookup on every ordinary request.

        :param request: The current request.
        :returns: Credentials mapping, empty when this is not a callback.
        """
        credentials = getattr(request, "other", {}).get(CREDENTIALS_KEY)
        if not credentials:
            return {}
        return {
            "extractor": EXTRACTOR,
            "provider": credentials["provider"],
            "subject": credentials["subject"],
            "claims": credentials.get("claims", {}),
        }

    # ------------------------------------------------------------------
    # IAuthenticationPlugin
    # ------------------------------------------------------------------

    def authenticateCredentials(self, credentials: JSONDict) -> tuple[str, str] | None:
        """Resolve external credentials to a Plone principal.

        On first sight of an identity a userid is minted, and the Profile that
        *is* that user is created for it by a subscriber to the event fired
        below -- so the rest of Plone sees an ordinary user. Nothing is
        written to ``source_users``: the content object is the account, this
        plugin enumerates it, and a second record of the same person is the
        thing that then outlives the object it shadows.

        :param credentials: Mapping from :meth:`extractCredentials`.
        :returns: ``(userid, login)`` on success, ``None`` otherwise.
        """
        if credentials.get("extractor") != EXTRACTOR:
            return self._authenticate_content_password(credentials)

        provider = credentials["provider"]
        subject = credentials["subject"]
        claims: Claims = credentials.get("claims", {})

        userid = self._store.userid_for(provider, subject)
        is_new_identity = userid is None
        # Read before touch() overwrites the snapshot: the avatar is fetched
        # only when the provider changed it, and that is the one part of
        # signing in that makes a network request.
        previous_picture = self._remembered_picture(provider, subject)
        is_new_user = False
        if is_new_identity:
            userid = self._adopt_by_verified_email(provider, claims)
            if userid is None:
                is_new_user = True
                userid = mint_userid(
                    source=self._userid_source(provider),
                    claims=claims,
                    subject=subject,
                )
            self._store.add(provider, subject, userid, claims)
        else:
            self._store.touch(provider, subject, claims)
            self._warn_if_orphaned(userid)

        notify(
            ExternalIdentityAuthenticated(
                userid=userid,
                provider=provider,
                subject=subject,
                claims=claims,
                is_new_user=is_new_user,
                is_new_identity=is_new_identity,
            )
        )

        if is_new_user:
            self._warn_if_unclaimed(userid)

        # After the event, and that ordering is load-bearing.
        #
        # Both of these writes are *fallbacks*: they put a value in
        # `portal_memberdata` only for a user whose Profile does not claim it.
        # `_apply_property_map` asks `_properties_owned_elsewhere` and
        # `_sync_portrait` asks whether the user has a Profile at all, and on
        # a first login neither question has an honest answer yet -- the
        # Profile is created by a subscriber to the event above. Asked too
        # early, both were told "nobody owns this user" and wrote into
        # `portal_memberdata`, leaving the Profile empty on exactly the login
        # that mattered. Then nothing corrected it: the property map skips a
        # field that already has a value, and the avatar is refetched only
        # when the provider changes its URL, so one badly-timed answer became
        # permanent.
        #
        # A fallback runs after everyone entitled to claim has been told.
        #
        # Every login, not just the first: a name or address changed at the
        # provider should reach Plone without the user being recreated.
        self._apply_property_map(userid, provider, claims)
        self._sync_portrait(userid, provider, claims, previous_picture)
        self._sync_federated_groups(userid, provider, subject, claims)
        return (userid, userid)

    # -- IUserAdderPlugin --------------------------------------------------

    def doAddUser(self, login: str, password: str) -> bool:
        """Create the configured content object for a new user, if there is one.

        PAS walks every registered adder and stops at the first that returns
        true -- ``ZODBUserManager.doAddUser`` returns ``False`` on a duplicate
        id, so declining is the protocol rather than something invented here.
        This one declines only when a site has pointed the records at a type
        that is not a user, which is a misconfiguration rather than a mode;
        ``source_users`` then adds the user, exactly as it did before this
        add-on existed.

        The container is created here if it is missing. Where Profiles live is
        set late -- a policy profile may move it after this add-on is
        installed -- so it is not made at install time, and the first person
        to need one is what brings it into being.

        The password is **not** stored here. This plugin creates the record a
        user *is*; where a credential lives is a separate decision, and on a
        site that has not made it the credential still belongs to
        ``source_users``. So adding a user through the ordinary API creates a
        content object and a credential, and neither store is guessing about
        the other. An externally authenticated user has neither -- nothing
        writes them a row, and they sign in at their provider.

        :param login: The login name, already transformed by PAS.
        :param password: The password PAS was given. Ignored, deliberately.
        :returns: Whether this plugin created the user.
        """
        from pas.plugins.identity.core.container import PROFILE

        configured = self._configured(
            USER_CONTENT_TYPE_RECORD,
            USER_CONTAINER_PATH_RECORD,
            IUserContent,
            create_kind=PROFILE,
        )
        if configured is None:
            return False
        container, portal_type = configured

        from plone import api

        with api.env.adopt_roles(["Manager"]):
            obj = api.content.create(
                container=container,
                type=portal_type,
                id=login,
                userid=login,
                login=login,
            )
        self._delegate_credential(obj, login, password)
        logger.info("Created %s %r for %s", portal_type, login, login)
        return True

    def _delegate_credential(self, obj, login: str, password: str) -> None:
        """Put the password where a password can live.

        Not on the content object. A Dexterity field holding a credential is
        serialized by ``plone.restapi``, exported by GenericSetup, indexable
        and snapshotted by versioning -- four separate paths that each fail by
        disclosing it. So the content object is the record a user *is*, and
        ``source_users`` stays the credential store.

        A site adding a user through the ordinary API therefore ends up with
        someone who can actually sign in. An externally authenticated user
        needs none of this -- they have no password to put anywhere, and
        nothing writes a ``source_users`` row for them.

        A site that would rather keep credentials on the content type opts
        into something providing
        :class:`~pas.plugins.identity.core.interfaces.ICredentialStorage`,
        and this step then has nothing to do.

        :param obj: The content object just created, asked first.
        :param login: The login name, which is also the userid.
        :param password: The password PAS was given. Nothing is stored when
            it is empty -- an externally authenticated user has none, and a
            blank one is not a credential.
        """
        if not password:
            return

        storage = ICredentialStorage(obj, None)
        if storage is not None:
            storage.set_password(password)
            return

        try:
            self._source_users().addUser(login, login, password)
        except KeyError:
            # Already there. PAS asked us to add a user it does not think
            # exists, so the content object is the new half; refusing the
            # whole thing over an existing credential would be worse.
            logger.info("%s already has a source_users credential", login)

    def _container(self, path: str):
        """Resolve a configured container, or ``None``.

        :param path: Path relative to the site root.
        :returns: The container, or ``None`` when the path names nothing.
        """
        from plone import api

        portal = api.portal.get()
        return portal.unrestrictedTraverse(path.strip("/"), None)

    def _provides(self, portal_type: str, marker) -> bool:
        """Report whether a portal type's schema provides a marker.

        Asked of the FTI rather than of an instance, because the answer has
        to be known before anything is created. A record naming a type that
        is not a user, or not a group, is a misconfiguration, and creating
        the object anyway would leave every later query having to tolerate
        it.

        :param portal_type: The type to check.
        :param marker: :class:`IUserContent` or :class:`IGroupContent`.
        :returns: Whether objects of that type satisfy the marker.
        """
        from plone import api
        from plone.dexterity.interfaces import IDexterityFTI

        fti = getattr(api.portal.get_tool("portal_types"), portal_type, None)
        if not IDexterityFTI.providedBy(fti):
            return False
        try:
            schema = fti.lookupSchema()
        except (AttributeError, ImportError):
            # A type whose schema will not load is not one to create in, and
            # a broken FTI must not break adding a user or a group.
            return False
        return schema.isOrExtends(marker)

    def _configured(
        self,
        type_record: str,
        path_record: str,
        marker,
        create_kind: str = "",
    ):
        """Return where to create, or ``None`` when this is not our job.

        One place for the ways a site declines: no type, no container path, a
        path that resolves to nothing, and a type that is not what the marker
        requires.

        :param type_record: Registry record naming the portal type.
        :param path_record: Registry record naming the container path.
        :param marker: The interface the type has to provide.
        :param create_kind: :data:`~pas.plugins.identity.core.container.PROFILE`
            or :data:`~pas.plugins.identity.core.container.GROUP` to create the
            container when it is missing. Empty -- the default -- keeps this a
            read: the paths that only want to *find* something must not make
            a folder as a side effect.
        :returns: ``(container, portal_type)``, or ``None``.
        """
        portal_type = _record(type_record)
        container_path = _record(path_record)
        if not portal_type or not container_path:
            return None

        container = self._container(container_path)
        if container is None and create_kind:
            self._make_container(create_kind)
            # Re-resolved through the record rather than taken from the call
            # above. The container settings and this record normally derive
            # from each other; where a site has pulled them apart, the record
            # is what says where principals go, and filing them into whatever
            # was just created somewhere else would be worse than declining.
            container = self._container(container_path)
        if container is None:
            logger.warning("%r does not resolve to a container", container_path)
            return None

        if not self._provides(portal_type, marker):
            logger.warning("%r does not provide %s", portal_type, marker.__name__)
            return None
        return container, portal_type

    def _make_container(self, kind: str) -> None:
        """Create the configured principal container, if it can be created.

        Run as a Manager: the person triggering this is usually mid-login and
        holds no roles yet, and the add permissions the container is about to
        be granted are exactly what stops anyone else filing a principal.

        Silent when the configured *parent* path does not resolve -- a folder
        somebody named and never created. The caller then finds no container
        at the path it asked about and declines, which is the report.

        :param kind: :data:`~pas.plugins.identity.core.container.PROFILE` or
            :data:`~pas.plugins.identity.core.container.GROUP`.
        """
        from pas.plugins.identity.core.container import ContainerNotFound
        from pas.plugins.identity.core.container import get_container
        from plone import api

        try:
            with api.env.adopt_roles(["Manager"]):
                get_container(create=True, kind=kind)
        except ContainerNotFound:
            pass

    def _content_user(self, userid: str):
        """Return the content object that *is* this user, if there is one.

        One traversal rather than a search, which is what the
        ``IUserContent`` contract's "the object id is the userid" clause
        buys.

        :param userid: Canonical Plone userid.
        :returns: The object, or ``None``.
        """
        configured = self._configured(
            USER_CONTENT_TYPE_RECORD, USER_CONTAINER_PATH_RECORD, IUserContent
        )
        if configured is None:
            return None
        container, portal_type = configured
        obj = container.get(userid)
        return obj if getattr(obj, "portal_type", None) == portal_type else None

    # -- IGroupManagement --------------------------------------------------
    #
    # PAS has no IGroupAdderPlugin. Group creation goes through PlonePAS's
    # GroupTool, which loops over IGroupManagement plugins with the same
    # "stop at the first that returns true" semantics the user adder relies
    # on, so declining works the same way here.
    #
    # Of the six methods the interface declares, PlonePAS's tool calls four:
    # addGroup, removeGroup, addPrincipalToGroup and removePrincipalFromGroup.
    # `updateGroup` and `setRolesForGroup` are declared and never reached --
    # the tool handles the first itself through the group object and routes
    # the second to a role manager. They are implemented as honest refusals
    # rather than as silent successes.

    def addGroup(self, id: str, **kw) -> bool:
        """Create the configured content object for a new group.

        :param id: The group id, which is also the object's id.
        :param kw: ``title`` and ``description``, as the tool sends them.
        :returns: Whether this plugin created the group.
        """
        from pas.plugins.identity.core.container import GROUP

        configured = self._configured(
            GROUP_CONTENT_TYPE_RECORD,
            GROUP_CONTAINER_PATH_RECORD,
            IGroupContent,
            create_kind=GROUP,
        )
        if configured is None:
            return False
        container, portal_type = configured

        from plone import api

        with api.env.adopt_roles(["Manager"]):
            api.content.create(
                container=container,
                type=portal_type,
                id=id,
                group_id=id,
                title=kw.get("title") or id,
                description=kw.get("description", ""),
            )
        logger.info("Created %s %r", portal_type, id)
        return True

    def removeGroup(self, group_id: str) -> bool:
        """Delete a group this plugin owns.

        Declines for a group it did not create, so a site running both this
        and ``source_groups`` does not have one deleting the other's.

        :param group_id: The group to remove.
        :returns: Whether it was removed.
        """
        group = self._content_group(group_id)
        if group is None:
            return False

        from plone import api

        with api.env.adopt_roles(["Manager"]):
            api.content.delete(obj=group, check_linkintegrity=False)
        logger.info("Removed group %r", group_id)
        return True

    def addPrincipalToGroup(self, principal_id: str, group_id: str) -> bool:
        """Record that a principal belongs to a group.

        Written to the *member*, because that is the direction Plone asks the
        question in: ``getGroupsForPrincipal`` runs on every permission check
        touching a local role, and listing a group's members does not.

        The member may itself be a group, which nests it: everybody in the
        inner group is in the outer one. The write is the same field on the
        same side, which is what makes the nesting a walk over one edge rather
        than a second kind of relation -- see
        :mod:`pas.plugins.identity.core.nesting`.

        :param principal_id: The user or group to add.
        :param group_id: The group to add them to.
        :returns: Whether the membership was recorded.
        """
        if self._content_group(group_id) is None:
            return False
        if principal_id == group_id:
            # A group inside itself grants nothing and means nothing; the
            # closure would answer correctly and the edit form would show a
            # row nobody can account for.
            logger.info("Refusing to nest group %r inside itself", principal_id)
            return False

        member = self._content_user(principal_id) or self._content_group(principal_id)
        if member is None:
            return False

        current = tuple(getattr(member, "group_ids", ()) or ())
        if group_id not in current:
            member.group_ids = (*current, group_id)
            _reindex(member)
        return True

    def removePrincipalFromGroup(self, principal_id: str, group_id: str) -> bool:
        """Remove a principal from a group.

        The counterpart of :meth:`addPrincipalToGroup`, and it un-nests a
        group for the same reason that one nests it.

        :param principal_id: The user or group to remove.
        :param group_id: The group to remove them from.
        :returns: Whether the membership was removed.
        """
        member = self._content_user(principal_id) or self._content_group(principal_id)
        if member is None:
            return False

        current = tuple(getattr(member, "group_ids", ()) or ())
        if group_id not in current:
            return False
        member.group_ids = tuple(g for g in current if g != group_id)
        _reindex(member)
        return True

    def updateGroup(self, id: str, **kw) -> bool:
        """Refuse: PlonePAS edits a group through the group object instead.

        :param id: The group id.
        :param kw: Ignored.
        :returns: Always ``False``.
        """
        return False

    def setRolesForGroup(self, group_id: str, roles=()) -> bool:
        """Refuse: PlonePAS routes roles to a role manager, not here.

        :param group_id: The group id.
        :param roles: Ignored.
        :returns: Always ``False``.
        """
        return False

    def _content_group(self, group_id: str):
        """Return the content object that *is* this group, if there is one.

        :param group_id: The group id.
        :returns: The object, or ``None``.
        """
        configured = self._configured(
            GROUP_CONTENT_TYPE_RECORD, GROUP_CONTAINER_PATH_RECORD, IGroupContent
        )
        if configured is None:
            return None
        container, portal_type = configured
        obj = container.get(group_id)
        return obj if getattr(obj, "portal_type", None) == portal_type else None

    def _authenticate_content_password(
        self, credentials: JSONDict
    ) -> tuple[str, str] | None:
        """Authenticate against a password kept on the user's own object.

        Answers only where a site has opted its user type into
        :class:`~pas.plugins.identity.core.interfaces.ICredentialStorage`.
        That is not the default, so on an ordinary site the adaptation fails
        and ``source_users`` answers exactly as it always did.

        This lives on the identity plugin rather than the profile one on
        purpose. That plugin serves properties, enumeration and groups and
        must never become a way to log in -- there is a test named for it --
        because the plugin that authenticates a userid is the one ``@users``
        reports as its source, and a site's answer to "where did this account
        come from" should not change with where its properties are kept.

        The login is resolved through PAS rather than by guessing that it
        equals the userid. Enumeration is the profile plugin's job, and asking
        it is what makes a login name that differs from the userid work.

        :param credentials: PAS's extracted credentials.
        :returns: ``(userid, login)`` on success, or ``None``.
        """
        login = credentials.get("login")
        password = credentials.get("password")
        if not login or not password:
            return None

        userid = self._userid_for_login(login)
        if userid is None:
            return None

        obj = self._content_user(userid)
        if obj is None:
            return None

        storage = ICredentialStorage(obj, None)
        if storage is None or not storage.check_password(password):
            return None
        return (userid, login)

    def _userid_for_login(self, login: str) -> str | None:
        """Return the userid behind a login name, asking PAS.

        ``exact_match`` is not optional: ``searchUsers`` matches substrings,
        so ``alice`` would otherwise also find ``alice2`` and this would
        authenticate whichever record came back first.

        :param login: The login name offered.
        :returns: The userid, or ``None`` when nothing matches.
        """
        for record in self._getPAS().searchUsers(login=login, exact_match=True):
            found = record.get("id")
            if found:
                return found
        return None

    def _remembered_picture(self, provider: str, subject: str) -> str:
        """Return the avatar URL stored the last time this identity signed in.

        :param provider: Provider id.
        :param subject: Provider-side subject.
        :returns: The remembered URL, or an empty string.
        """
        record = self._store.get(provider, subject)
        if record is None:
            return ""
        return str(record.claims.get("picture_url") or "")

    def _sync_federated_groups(
        self, userid: str, provider: str, subject: str, claims: Claims
    ) -> None:
        """Reconcile the groups a provider grants this user.

        Runs on every login, because a membership revoked at the provider has
        to go away here too, and nobody is going to notice that by hand.

        The reconciliation is fenced. What the provider granted last time is
        on the identity record, so this adds what is newly granted and removes
        only what *this provider* granted before and no longer does. A group
        an administrator granted locally was never in that set and is never
        touched; neither is a group granted by a second provider, which keeps
        its own record.

        A provider with an empty map returns immediately rather than
        reconciling against nothing. Otherwise clearing a map would silently
        strip every group it had granted, at the next login, with no other
        sign -- and an operator clearing a map is at least as likely to be
        rewriting it. Removing the provider's grants is a thing to ask for
        explicitly.

        Membership is written through PlonePAS's group tool rather than to any
        store of ours, so it lands wherever this site keeps membership: a
        Profile's ``group_ids`` on a site that keeps users as content, and
        ``source_groups`` on one that does not. That also means
        ``getGroupsForPrincipal`` stays exactly as cheap as it was.

        :param userid: The user signing in.
        :param provider: Provider id.
        :param subject: Provider-side subject identifier.
        :param claims: The claims of this login.
        """
        from pas.plugins.identity.core.controlpanel import get_provider
        from pas.plugins.identity.core.groupmap import claimed_groups
        from pas.plugins.identity.core.groupmap import map_groups
        from plone import api

        config = get_provider(provider)
        if config is None or not config.groupmap:
            return

        claim_path = (config.config.get("group_claim") or "").strip() or getattr(
            config.driver, "default_group_claim", ""
        )
        if not claim_path:
            # The driver says this provider has no groups, so the config
            # schema offered no field to name one. A map stored against it
            # anyway -- by an import, or by a driver that was swapped out --
            # grants nothing rather than guessing at a claim name.
            return
        granted = map_groups(config.groupmap, claimed_groups(claim_path, claims))

        record = self._store.get(provider, subject)
        if record is None:  # pragma: no cover - can't-happen: just stored above
            return
        previous = set(record.groups)
        if granted == previous:
            return

        with api.env.adopt_roles(["Manager"]):
            for group_id in sorted(previous - granted):
                if api.group.get(groupname=group_id) is not None:
                    api.group.remove_user(groupname=group_id, username=userid)
            # A group named in the map but absent from the site is skipped
            # rather than created. The map is edited by hand and a typo in it
            # must not mint a group, and `addPrincipalToGroup` would decline
            # anyway -- recording it as granted would then make the next login
            # try to take away something never given.
            actually_granted = set()
            for group_id in sorted(granted):
                if api.group.get(groupname=group_id) is None:
                    logger.warning(
                        "Provider %r maps a group to %r, which this site does "
                        "not have; %r was not added to it",
                        provider,
                        group_id,
                        userid,
                    )
                    continue
                api.group.add_user(groupname=group_id, username=userid)
                actually_granted.add(group_id)

        record.groups = tuple(sorted(actually_granted))

    def _sync_portrait(
        self, userid: str, provider_id: str, claims: Claims, previous: str
    ) -> None:
        """Copy the provider's avatar into portrait storage when it changed.

        Off unless the site switched it on -- see
        :mod:`pas.plugins.identity.core.portraits` for why that is the
        default. Fetching only on change keeps a network request out of
        every sign-in, and a URL that failed is not retried until the
        provider offers a different one.

        :param userid: Canonical Plone userid.
        :param provider_id: The provider, whose configuration decides whether
            a plain-HTTP URL may be fetched at all.
        :param claims: Normalized claims.
        :param previous: The URL synced last time, if any.
        """
        from pas.plugins.identity.core.portraits import sync_portrait

        url = str(claims.get("picture_url") or "")
        if not url or url == previous:
            return
        sync_portrait(userid, url, allow_http=self._picture_over_http(provider_id))

    def _picture_over_http(self, provider_id: str) -> bool:
        """Whether this provider may have its avatar fetched over plain HTTP.

        :param provider_id: The provider.
        :returns: Whether it is configured to allow it; false when the
            provider is gone or says nothing, which is the safe answer.
        """
        from pas.plugins.identity.core.controlpanel import get_provider

        config = get_provider(provider_id)
        if config is None:
            return False
        return bool(config.config.get("picture_over_http"))

    def _userid_source(self, provider_id: str) -> str:
        """Return the userid strategy configured for a provider.

        :param provider_id: The provider.
        :returns: One of :data:`USERID_SOURCES`; ``uuid`` when the provider
            is gone or says nothing.
        """
        from pas.plugins.identity.core.controlpanel import get_provider

        config = get_provider(provider_id)
        if config is None:
            return "uuid"
        return str(config.config.get("userid_source") or "uuid")

    def _adopt_by_verified_email(self, provider: str, claims: Claims) -> str | None:
        """Find an existing account to attach this identity to.

        Two switches, both the operator's and both off by default, because
        this is the step where somebody signing in with a provider ends up
        inside an account that already existed.

        ``auto_link_by_email``
            Whether to look for an account at all.

        ``trust_email_verification``
            Whether *this* provider saying ``email_verified`` means anything.
            The address being matched on is the one it just sent, so a
            provider whose word this site does not take cannot reach an
            account by asserting somebody else's address -- which is the
            takeover in :doc:`/concepts/email-verification`, and which
            auto-linking alone did not stop: the match was against an address
            some *other*, trusted route had verified.

        Even with both on, the address has to already be verified here: by a
        magic link this site sent, or by a provider this site trusts.

        :param provider: Provider id the login came from.
        :param claims: Normalized claims from the provider.
        :returns: The userid to adopt, or ``None`` to mint a fresh one.
        """
        from pas.plugins.identity.core.controlpanel import get_provider
        from pas.plugins.identity.core.verification import trusts_verification

        config = get_provider(provider)
        if config is None or not config.config.get("auto_link_by_email"):
            return None
        if not trusts_verification(provider):
            return None
        # Only a literal True counts, exactly as in the driver layer: a
        # missing key or a string "false" must not read as verified.
        if claims.get("email_verified") is not True:
            return None
        address = (claims.get("email") or "").strip().lower()
        if not address:
            return None
        owner = self._store.userid_for(EMAIL_PROVIDER, address)
        if owner is None:
            return None
        if self._getPAS().getUserById(owner) is None:
            # The identity outlived the account. Adopting it would sign this
            # person into a userid nothing resolves: no properties, no roles,
            # invisible to every search, and a traceback from the first line
            # that touches the user. A fresh account is not what the operator
            # configured, but it is a working login and it is recoverable --
            # the stale identity is a `remove` away from letting the next one
            # link properly.
            logger.warning(
                "Not attaching %s identity to %s: the verified address %r is "
                "held for a userid this site has no account for",
                provider,
                owner,
                address,
            )
            return None
        logger.info("Attaching %s identity to %s by verified email", provider, owner)
        return owner

    # ------------------------------------------------------------------
    # ICredentialsResetPlugin
    # ------------------------------------------------------------------

    def resetCredentials(self, request: HTTPRequest, response: HTTPResponse) -> None:
        """Drop any credentials this plugin put on the request.

        The session ticket and JWT are owned by ``plone.session`` and
        ``jwt_auth``; PAS resets those through their own plugins.

        :param request: The current request.
        :param response: The current response.
        """
        if hasattr(request, "other"):
            request.other.pop(CREDENTIALS_KEY, None)

    # ------------------------------------------------------------------
    # IChallengePlugin (opt-in)
    # ------------------------------------------------------------------

    def challenge(self, request: HTTPRequest, response: HTTPResponse) -> bool:
        """Redirect an unauthorized request to the provider picker.

        :param request: The current request.
        :param response: The current response.
        :returns: Whether the challenge was issued.
        """
        if not self.challenge_enabled:
            return False
        url = f"{self._portal_url()}/{LOGIN_VIEW}"
        came_from = request.get("ACTUAL_URL", "")
        query = request.get("QUERY_STRING")
        if came_from and query:
            # The query string is not decoration. An OAuth authorization
            # request *is* its query string, so a `came_from` built from the
            # path alone resumes a request with no client, no redirect URI
            # and no PKCE challenge -- which fails in a way that reads like a
            # client bug.
            came_from = f"{came_from}?{query}"
        # Stripped to a site-local URL before being handed back, exactly as
        # the stock CookieAuthHelper does: this value ends up in a redirect
        # after login, and an absolute one would make the login form an open
        # redirect. Reduced *before* the emptiness test, because a URL that is
        # nothing but a host reduces to nothing, and appending an empty
        # `came_from=` is worse than appending none.
        came_from = url_local(came_from)
        if came_from:
            # Quoted, or the first `&` of the query string would be read as
            # another parameter of the login URL rather than part of the
            # return address.
            url = f"{url}?came_from={quote(came_from)}"
        response.redirect(url, lock=True)
        return True

    def _portal_url(self) -> str:
        """Return the portal URL.

        :returns: Absolute URL of the Plone site this plugin lives in.
        """
        from plone import api

        return api.portal.get().absolute_url()

    # ------------------------------------------------------------------
    # Linking API -- used by the ``@identities`` service
    # ------------------------------------------------------------------

    def link(
        self, userid: str, provider: str, subject: str, claims: Claims
    ) -> IdentityRecord:
        """Attach an external identity to an existing userid.

        :param userid: Canonical Plone userid, already authenticated.
        :param provider: Provider id.
        :param subject: Provider-side subject identifier.
        :param claims: Normalized claims.
        :returns: The stored record.
        :raises IdentityCollision: When another userid already owns it.
        """
        record = self._store.add(provider, subject, userid, claims)
        notify(IdentityLinked(userid, provider, subject, claims))
        return record

    def unlink(self, userid: str, provider: str, subject: str) -> None:
        """Detach an external identity from a userid.

        :param userid: Canonical Plone userid.
        :param provider: Provider id.
        :param subject: Provider-side subject identifier.
        :raises KeyError: When the identity is unknown or owned by someone else.
        :raises LockoutRefused: When this is the user's last way in.
        """
        owner = self._store.userid_for(provider, subject)
        if owner != userid:
            raise KeyError(f"{provider}:{subject} is not linked to {userid}")
        if not self.can_unlink(userid, provider, subject):
            raise LockoutRefused(
                f"{provider}:{subject} is the only way {userid} can authenticate"
            )
        self._store.remove(provider, subject)
        notify(IdentityUnlinked(userid, provider, subject))

    def can_unlink(self, userid: str, provider: str, subject: str) -> bool:
        """Decide whether unlinking would lock the user out.

        Unlinking is allowed while the user keeps at least one other external
        identity, a verified email identity, or a ``source_users`` password.

        :param userid: Canonical Plone userid.
        :param provider: Provider id.
        :param subject: Provider-side subject identifier.
        :returns: Whether the unlink is safe.
        """
        from pas.plugins.identity.core.store import normalize_subject

        normalized = normalize_subject(provider, subject)
        others = [
            r
            for r in self._store.identities_for(userid)
            if not (r.provider == provider and r.subject == normalized)
        ]
        if others:
            return True
        return self._has_local_password(userid)

    def has_verified_email(self, userid: str) -> bool:
        """Report whether the user owns a verified email identity.

        :param userid: Canonical Plone userid.
        :returns: Whether such an identity exists.
        """
        return any(
            r.provider == EMAIL_PROVIDER for r in self._store.identities_for(userid)
        )

    def _has_local_password(self, userid: str) -> bool:
        """Report whether the user has a password they can actually log in with.

        An externally authenticated user has no ``source_users`` row at all --
        their Profile is the account, and nothing ever wrote them a
        credential -- so the absence of a row is the honest answer to "could
        you still get in without this identity?". A row exists only where
        somebody set a password: through ``api.user.create``, or through the
        stock forms.

        A password kept on the Profile itself, by a site that enabled the
        password behaviour, is not counted here. That errs toward refusing an
        unlink, which is the safe direction.

        :param userid: Canonical Plone userid.
        :returns: Whether a usable local password exists.
        """
        passwords = getattr(self._source_users(), "_user_passwords", {})
        return userid in passwords

    # ------------------------------------------------------------------
    # Decoration of the stock plugins
    # ------------------------------------------------------------------

    def _source_users(self) -> ZODBUserManager:
        """Return the site's ``source_users`` plugin.

        Reached through ``_getPAS()`` rather than ``aq_parent``: the plugin is
        usually acquired through the request, so ``aq_parent`` is a
        ``RequestContainer`` and any lookup on it silently resolves elsewhere.

        :returns: The ZODBUserManager instance.
        """
        return self._getPAS()["source_users"]

    def _warn_if_orphaned(self, userid: str) -> None:
        """Say so when a known identity resolves to an account that is gone.

        An identity outlives the account it was minted for -- a user deleted
        while the identity stayed in the store, an export restored without one
        half. The login is not a first one, so nothing on that path creates
        anything; what puts the account back is the subscriber that mints a
        Profile on every sign-in, and it does so quietly because it runs for
        every user on every login.

        Quietly is wrong here. An account reappearing is not what an operator
        who deleted one expects, and removing the identity as well is what
        makes the deletion stick. So this is the one place that can tell the
        two apart, and it says so.

        The **same** userid is restored rather than a fresh one. It is what
        the identity points at, what anything this person owns is owned by,
        and what the store would go on resolving to anyway; minting a new one
        would strand all of it and leave the same dead record behind.

        :param userid: The userid the identity resolved to.
        """
        if self._getPAS().getUserById(userid) is not None:
            return
        logger.warning(
            "Identity resolved to %s, which has no account: it is about to be "
            "created again. Remove the identity as well if the deletion was "
            "deliberate.",
            userid,
        )

    def _warn_if_unclaimed(self, userid: str) -> None:
        """Say so when a new user ended up with no record at all.

        Nothing writes a ``source_users`` account for an externally
        authenticated user: the content object is the account, and it is
        created by a subscriber to the event this method is called after --
        this package's own, or a site's. If nothing did, the login still
        succeeds and returns a principal that does not exist: no properties,
        no roles, invisible to every search. That is a configuration this
        cannot fix from here, and the one thing worse than it is finding out
        weeks later, so it is said once, at the moment it becomes true,
        naming the consequence.

        :param userid: The userid just minted.
        """
        if self._content_user(userid) is not None:
            return
        logger.warning(
            "No user object was created for %s: nothing wrote a %s, so the "
            "account exists as an identity and as nothing else",
            userid,
            _record(USER_CONTENT_TYPE_RECORD),
        )

    def _properties_owned_elsewhere(self, userid: str) -> bool:
        """Report whether another plugin owns this user's properties.

        The profile plugin does, for a user who has a Profile: it serves the
        property sheet, it applies the same property map, and it remembers
        which fields the provider wrote so a human's edit survives the next
        login. Writing through its sheet from here would defeat that -- the
        write would land, and nothing here knows it should not have.

        Asked per user rather than per site. A site always has the profile
        plugin now, and still has users it does not serve: an account created
        before the add-on was installed and not signed in with since has no
        Profile, and its properties are ``portal_memberdata``'s to keep.

        :param userid: Canonical Plone userid.
        :returns: Whether to leave this user's properties alone.
        """
        from plone import api

        member = api.user.get(userid=userid)
        if member is None:
            return False

        acl_users = api.portal.get_tool("acl_users")
        for _plugin_id, plugin in acl_users.plugins.listPlugins(IPropertiesPlugin):
            if not IOwnsUserProperties.providedBy(plugin):
                continue
            if plugin.getPropertiesForUser(member.getUser()) is not None:
                return True
        return False

    def _apply_property_map(
        self, userid: str, provider_id: str, claims: Claims
    ) -> None:
        """Write the provider's mapped claims onto the user.

        A property that already holds a value locally is left alone. The
        provider is the source of truth for a field nobody has touched, but
        an edit made in Plone must not be undone by the next login -- which
        is what an unconditional write on every login would do.

        Runs for every provider, mapped or not; a provider with no map
        resolves to nothing and writes nothing.

        :param userid: Canonical Plone userid.
        :param provider_id: Provider the claims came from.
        :param claims: Normalized claims.
        """
        from pas.plugins.identity.core.controlpanel import get_provider
        from pas.plugins.identity.core.propertymap import apply_property_map
        from plone import api

        config = get_provider(provider_id)
        if config is None or not config.propertymap:
            return

        if self._properties_owned_elsewhere(userid):
            return

        member = api.user.get(userid=userid)
        if member is None:  # pragma: no cover - can't-happen: just authenticated
            logger.warning("Authenticated user %s is not retrievable", userid)
            return

        resolved = apply_property_map(config.propertymap, claims)

        updates = {
            field: value
            for field, value in resolved.items()
            if not member.getProperty(field, None)
        }
        # A portrait is an image in member storage, not a property: writing
        # a URL string into it through setMemberProperties would store the
        # URL. Avatars have their own path -- see :meth:`_sync_portrait` --
        # which fetches, scales and stores the bytes, behind the opt-in that
        # exists because the URL is a claim the user may control.
        updates.pop("portrait", None)
        if updates:
            member.setMemberProperties(updates)


classImplements(
    IdentityPlugin,
    IExtractionPlugin,
    IAuthenticationPlugin,
    ICredentialsResetPlugin,
    IChallengePlugin,
    IUserAdderPlugin,
    IGroupManagement,
)

InitializeClass(IdentityPlugin)


__all__ = ["IdentityPlugin", "mint_userid"]
