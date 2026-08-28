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
from BTrees.OOBTree import OOSet
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

import secrets


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


#: Portal type created for a new user, on a site keeping users as content.
#: Empty means this plugin adds nobody and ``source_users`` does it.
USER_CONTENT_TYPE_RECORD = "pas.plugins.identity.user_content_type"

#: Where those objects go, relative to the site root.
USER_CONTAINER_PATH_RECORD = "pas.plugins.identity.user_container_path"

#: Portal type created for a new group, on a site keeping groups as content.
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

    #: Userids whose ``source_users`` password is a plugin-generated
    #: placeholder rather than something the human can type.
    _placeholder_passwords: OOSet

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
        self._placeholder_passwords = OOSet()

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

        On first sight of an identity a userid is minted and a user record is
        created for it, so the rest of Plone sees an ordinary user: a
        ``source_users`` account on an ordinary site, and on a site that
        keeps its users as content, the content object -- created by whatever
        the site configured to claim it, in a subscriber to the event fired
        below.

        :param credentials: Mapping from :meth:`extractCredentials`.
        :returns: ``(userid, login)`` on success, ``None`` otherwise.
        """
        if credentials.get("extractor") != EXTRACTOR:
            return self._authenticate_content_password(credentials)

        provider = credentials["provider"]
        subject = credentials["subject"]
        claims: Claims = self._settle_email(credentials.get("claims", {}))

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
                self._create_plone_user(userid, claims)
            self._store.add(provider, subject, userid, claims)
        else:
            self._store.touch(provider, subject, claims)

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

        if is_new_user and self._keeps_users_as_content():
            self._warn_if_unclaimed(userid)

        # After the event, and that ordering is load-bearing.
        #
        # Both of these writes are *fallbacks*: they put a value in core's own
        # store only for a user nobody else claims. `_apply_property_map` asks
        # `_properties_owned_elsewhere` and `_sync_portrait` asks
        # `IProfileSupport`, and on a first login neither question has an
        # honest answer yet -- the thing that would claim the user is created
        # by a subscriber to the event above. Asked too early, both were told
        # "nobody owns this user" and wrote into `portal_memberdata`, leaving
        # the claimed store empty on exactly the login that mattered. Then
        # nothing corrected it: the property map skips a field that already
        # has a value, and the avatar is refetched only when the provider
        # changes its URL, so one badly-timed answer became permanent.
        #
        # A fallback runs after everyone entitled to claim has been told. That
        # is the rule, and it names no layer.
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
        This one declines whenever the site has not been configured to keep
        its users as content, which is every site until somebody sets the two
        records, and ``source_users`` then adds the user exactly as before.

        The password is **not** stored here. This plugin creates the record a
        user *is*; where a credential lives is a separate decision, and on a
        site that has not made it the credential still belongs to
        ``source_users``. So a site running this creates a content object and
        a credential, and neither store is guessing about the other. An
        externally authenticated user has neither a password nor a
        ``source_users`` row -- see :meth:`_create_plone_user`.

        :param login: The login name, already transformed by PAS.
        :param password: The password PAS was given. Ignored, deliberately.
        :returns: Whether this plugin created the user.
        """
        configured = self._configured(
            USER_CONTENT_TYPE_RECORD, USER_CONTAINER_PATH_RECORD, IUserContent
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
        :meth:`_create_plone_user` writes no ``source_users`` row for them on
        a site that keeps its users as content.

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

    def _configured(self, type_record: str, path_record: str, marker):
        """Return where to create, or ``None`` when this is not our job.

        One place for the four ways a site declines: no type, no container, a
        container that does not resolve, and a type that is not what the
        marker requires.

        :param type_record: Registry record naming the portal type.
        :param path_record: Registry record naming the container path.
        :param marker: The interface the type has to provide.
        :returns: ``(container, portal_type)``, or ``None``.
        """
        portal_type = _record(type_record)
        container_path = _record(path_record)
        if not portal_type or not container_path:
            return None

        container = self._container(container_path)
        if container is None:
            logger.warning("%r does not resolve to a container", container_path)
            return None

        if not self._provides(portal_type, marker):
            logger.warning("%r does not provide %s", portal_type, marker.__name__)
            return None
        return container, portal_type

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
        configured = self._configured(
            GROUP_CONTENT_TYPE_RECORD, GROUP_CONTAINER_PATH_RECORD, IGroupContent
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
        """Record that a user belongs to a group.

        Written to the *user*, because that is the direction Plone asks the
        question in: ``getGroupsForPrincipal`` runs on every permission check
        touching a local role, and listing a group's members does not.

        Refuses to nest a group inside a group. A recursive membership answer
        computed from catalog metadata stops being a single lookup, which is
        the property the whole design rests on.

        :param principal_id: The user to add.
        :param group_id: The group to add them to.
        :returns: Whether the membership was recorded.
        """
        if self._content_group(principal_id) is not None:
            logger.info("Refusing to nest group %r inside %r", principal_id, group_id)
            return False

        user = self._content_user(principal_id)
        if user is None or self._content_group(group_id) is None:
            return False

        current = tuple(getattr(user, "group_ids", ()) or ())
        if group_id not in current:
            user.group_ids = (*current, group_id)
            _reindex(user)
        return True

    def removePrincipalFromGroup(self, principal_id: str, group_id: str) -> bool:
        """Remove a user from a group.

        :param principal_id: The user to remove.
        :param group_id: The group to remove them from.
        :returns: Whether the membership was removed.
        """
        user = self._content_user(principal_id)
        if user is None:
            return False

        current = tuple(getattr(user, "group_ids", ()) or ())
        if group_id not in current:
            return False
        user.group_ids = tuple(g for g in current if g != group_id)
        _reindex(user)
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

        Answers only where a site both keeps its users as content *and* has
        opted something into
        :class:`~pas.plugins.identity.core.interfaces.ICredentialStorage`.
        Neither is the default, so on an ordinary site the adaptation fails
        and ``source_users`` answers exactly as it always did.

        This lives here rather than in the ``[content]`` layer on purpose.
        That layer serves properties, enumeration and groups and must never
        become a way to log in -- there is a test named for it -- because the
        plugin that authenticates a userid is the one ``@users`` reports as
        its source, and a site's answer to "where did this account come
        from" should not change with an optional property store. Core already
        authenticates; this is one more thing it authenticates against.

        The login is resolved through PAS rather than by guessing that it
        equals the userid. Enumeration is the layer's job, and asking it is
        what makes a login name that differs from the userid work.

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

    def _users_are_content(self) -> bool:
        """Report whether this site intends its users to be content objects.

        Deliberately narrower than :meth:`_keeps_users_as_content`, which
        also insists the container resolves. That is the right question
        before *creating* something and the wrong one before deciding whether
        anybody will be able to answer a question later: the container is
        made while the first profile is minted, so it is absent on exactly
        the login this is asked about.

        :returns: Whether a user content type is configured and is one this
            plugin may create a user in.
        """
        portal_type = _record(USER_CONTENT_TYPE_RECORD)
        return bool(portal_type) and self._provides(portal_type, IUserContent)

    def _settle_email(self, claims: Claims) -> Claims:
        """Choose an offered address when nothing here can ask for one.

        A driver that was offered several addresses picks none of them and
        carries the list instead, so the user can say which is theirs on
        their profile. That only works on a site that *has* profiles: with
        the ``[content]`` layer absent there is no profile, no form and no
        gate, so nobody is ever asked and the account simply has no address
        -- worse than the guess the choice replaced, because the guess was at
        least usually right.

        So the question is asked only where it can be answered. On a site
        that keeps its users as content the list is left alone and the flow
        holds the user on the form. Anywhere else the first offer is taken,
        which is the address the driver ordered first: the account's primary
        verified one where there is one.

        Asked with :meth:`_users_are_content` rather than
        :meth:`_keeps_users_as_content`, and the difference matters exactly
        once. The latter also requires the *container* to resolve, and the
        container is created while the first profile is minted -- in a
        subscriber to the event fired further down this method. On the very
        first login to a fresh site it therefore does not exist yet, and
        asking that question here would answer "no profiles" for the one
        user most likely to be offered a list.

        :param claims: Normalized claims from the driver.
        :returns: The claims, with ``email`` filled in when this site has no
            way of asking. Unchanged in every other case, including when the
            driver sent an address of its own.
        """
        choices = claims.get("email_choices") or ()
        if not choices or claims.get("email"):
            return claims
        if self._users_are_content():
            return claims
        chosen = choices[0]
        logger.info(
            "No profile to ask on: taking %s of %d offered addresses",
            chosen.get("address", ""),
            len(choices),
        )
        return {
            **claims,
            "email": chosen.get("address", ""),
            "email_verified": chosen.get("verified") is True,
        }

    def _adopt_by_verified_email(self, provider: str, claims: Claims) -> str | None:
        """Find an existing account to attach this identity to.

        Auto-linking by email is off unless the operator switched it on for
        this provider, and even then it matches only against an ``email``
        identity **this site** verified with a magic link. A provider saying
        ``email_verified`` about an address is not evidence: anyone who can
        register at that provider with a chosen address could otherwise walk
        into the matching Plone account.

        :param provider: Provider id the login came from.
        :param claims: Normalized claims from the provider.
        :returns: The userid to adopt, or ``None`` to mint a fresh one.
        """
        from pas.plugins.identity.core.controlpanel import get_provider

        config = get_provider(provider)
        if config is None or not config.config.get("auto_link_by_email"):
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

        Every account this plugin creates carries a random placeholder in
        ``source_users`` -- see :meth:`_create_plone_user` -- and a placeholder
        is not a way in. Counting it would defeat the lockout guard entirely: it would
        report "you still have a password" for every externally-created user,
        and cheerfully unlink their last identity.

        Known limitation: if a Manager later sets a real password for such an
        account through the stock forms, this plugin is not told, and the
        account stays flagged as placeholder-only. That errs toward refusing an
        unlink, which is the safe direction.

        :param userid: Canonical Plone userid.
        :returns: Whether a usable local password exists.
        """
        if userid in self._placeholder_passwords:
            return False
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

    def _create_plone_user(self, userid: str, claims: Claims) -> None:
        """Create the ``source_users`` account backing a new identity.

        The account gets a random placeholder password so the stock plugins
        have a complete record. Nobody is ever shown it and it is not a way in
        -- the userid is recorded in :attr:`_placeholder_passwords` so that the
        lockout guard does not mistake it for one.

        **Not on a site that keeps its users as content.** There the content
        object *is* the account: this plugin enumerates it, and
        :meth:`_authenticate_content_password` signs in against a password
        held on it, so a ``source_users`` row would be a second record of the
        same person -- the one that turns up in
        {menuselection}`acl_users --> source_users --> Users`, that nothing
        keeps in step, and that outlives the object it shadows. Creating the
        content half is the site's own business, the same way it is for a
        user added through :meth:`doAddUser`; core declines here exactly as
        it declines there.

        :param userid: The freshly minted userid.
        :param claims: Normalized claims used to seed the property sheet.
        """
        if self._keeps_users_as_content():
            return

        self._source_users().addUser(userid, userid, secrets.token_urlsafe(32))
        self._placeholder_passwords.insert(userid)
        self._seed_properties(userid, claims)

    def _warn_if_unclaimed(self, userid: str) -> None:
        """Say so when a new user ended up with no record at all.

        A site that keeps its users as content has told core not to mint a
        ``source_users`` account, and something else -- the ``[content]``
        layer's subscriber, or a site's own -- creates the object instead. If
        nothing did, the login still succeeds and returns a principal that
        does not exist: no properties, no roles, invisible to every search.
        That is a configuration this cannot fix from here, and the one thing
        worse than it is finding out weeks later, so it is said once, at the
        moment it becomes true, naming the consequence.

        :param userid: The userid just minted.
        """
        if self._content_user(userid) is not None:
            return
        logger.warning(
            "No user object was created for %s: this site keeps its users as "
            "content, so nothing wrote a %s -- the account exists as an "
            "identity and as nothing else",
            userid,
            _record(USER_CONTENT_TYPE_RECORD),
        )

    def _keeps_users_as_content(self) -> bool:
        """Report whether this site's users are content objects.

        :returns: Whether a type and a container are configured, and the type
            is one this plugin may create a user in.
        """
        return (
            self._configured(
                USER_CONTENT_TYPE_RECORD, USER_CONTAINER_PATH_RECORD, IUserContent
            )
            is not None
        )

    def _seed_properties(self, userid: str, claims: Claims) -> None:
        """Write the claims Plone knows how to display onto the user.

        Goes through ``plone.api``, which hands back the ``MemberData``
        wrapper. The bare ``PloneUser`` that PAS returns has no
        ``setMemberProperties`` -- reaching for it there fails with an
        acquisition error naming ``RequestContainer``, which reads like a
        request bug rather than a wrong object.

        ``setMemberProperties`` routes to whichever mutable property provider
        the site has, so core keeps working on a site that swapped
        ``mutable_properties`` for something else.

        :param userid: Canonical Plone userid.
        :param claims: Normalized claims.
        """
        from plone import api

        member = api.user.get(userid=userid)
        if member is None:  # pragma: no cover - can't-happen: just created above
            logger.warning("Newly created user %s is not retrievable", userid)
            return
        member.setMemberProperties({
            "fullname": claims.get("fullname", ""),
            "email": claims.get("email", ""),
        })

    def _properties_owned_elsewhere(self, userid: str) -> bool:
        """Report whether another plugin owns this user's properties.

        The ``[content]`` layer's plugin does, for a user who has a Profile:
        it serves the property sheet, it applies the same property map, and it
        remembers which fields the provider wrote so a human's edit survives
        the next login. Writing through its sheet from here would defeat that
        -- the write would land, and nothing here knows it should not have.

        Asked per user rather than per site, because a site can run the layer
        and still have users it does not serve.

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
