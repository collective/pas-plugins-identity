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
from pas.plugins.identity.core.interfaces import IIdentityPlugin
from pas.plugins.identity.core.interfaces import IOwnsUserProperties
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
from Products.PluggableAuthService.interfaces.plugins import IAuthenticationPlugin
from Products.PluggableAuthService.interfaces.plugins import IChallengePlugin
from Products.PluggableAuthService.interfaces.plugins import ICredentialsResetPlugin
from Products.PluggableAuthService.interfaces.plugins import IExtractionPlugin
from Products.PluggableAuthService.interfaces.plugins import IPropertiesPlugin
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

        On first sight of an identity a userid is minted and a
        matching ``source_users`` account is created, so the rest of Plone
        sees an ordinary user.

        :param credentials: Mapping from :meth:`extractCredentials`.
        :returns: ``(userid, login)`` on success, ``None`` otherwise.
        """
        if credentials.get("extractor") != EXTRACTOR:
            return None

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
                self._create_plone_user(userid, claims)
            self._store.add(provider, subject, userid, claims)
        else:
            self._store.touch(provider, subject, claims)

        # Every login, not just the first: a name or address changed at the
        # provider should reach Plone without the user being recreated.
        self._apply_property_map(userid, provider, claims)
        self._sync_portrait(userid, claims, previous_picture)

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
        return (userid, userid)

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

    def _sync_portrait(self, userid: str, claims: Claims, previous: str) -> None:
        """Copy the provider's avatar into portrait storage when it changed.

        Off unless the site switched it on -- see
        :mod:`pas.plugins.identity.core.portraits` for why that is the
        default. Fetching only on change keeps a network request out of
        every sign-in, and a URL that failed is not retried until the
        provider offers a different one.

        :param userid: Canonical Plone userid.
        :param claims: Normalized claims.
        :param previous: The URL synced last time, if any.
        """
        from pas.plugins.identity.core.portraits import sync_portrait

        url = str(claims.get("picture_url") or "")
        if not url or url == previous:
            return
        sync_portrait(userid, url)

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
        if owner is not None:
            logger.info(
                "Attaching %s identity to %s by verified email", provider, owner
            )
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

        :param userid: The freshly minted userid.
        :param claims: Normalized claims used to seed the property sheet.
        """
        self._source_users().addUser(userid, userid, secrets.token_urlsafe(32))
        self._placeholder_passwords.insert(userid)
        self._seed_properties(userid, claims)

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

        The ``[profile]`` layer's plugin does, for a user who has a Profile:
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
)

InitializeClass(IdentityPlugin)


__all__ = ["IdentityPlugin", "mint_userid"]
