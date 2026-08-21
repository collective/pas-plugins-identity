"""The PAS plugin (§4.1).

Implements extraction, authentication, credentials reset and -- off by default
-- challenge. It deliberately does **not** implement properties, enumeration,
groups, roles or user adding: on first login it *decorates* the stock
``source_users`` and ``mutable_properties`` plugins instead, which is what lets
core install and work with no extras (I5).

Extraction and authentication only ever run at callback time (I6). An ordinary
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
from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.interfaces import IIdentityPlugin
from pas.plugins.identity.core.interfaces import LockoutRefused
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
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements
from typing import Any
from uuid import uuid4
from zope.event import notify
from zope.interface import implementer

import secrets


#: Where the provider picker lives, for the optional challenge plugin.
LOGIN_VIEW = "@@identity-login"


def mint_userid() -> str:
    """Mint a canonical userid (D10, I1).

    A random UUID: never derived from provider claims, so it leaks nothing
    about where the account came from and cannot change when a claim does.

    :returns: 32 hex characters.
    """
    return uuid4().hex


@implementer(IIdentityPlugin)
class IdentityPlugin(BasePlugin):
    """Multi-provider external authentication with identity linking."""

    meta_type = "Identity Plugin"
    security = None  # set by InitializeClass below
    manage_options = BasePlugin.manage_options

    #: Whether to act as an ``IChallengePlugin``. Off by default (§4.1): a
    #: site that turns this on redirects anonymous 401s to the provider
    #: picker instead of the stock login form.
    challenge_enabled = False

    #: Userids whose ``source_users`` password is a plugin-generated
    #: placeholder rather than something the human can type (S4).
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
        self._placeholder_passwords = OOSet()

    @property
    def store(self) -> IdentityStore:
        """Return the identity store (§4.2).

        :returns: The store persisted inside this plugin.
        """
        return self._store

    @property
    def audit(self) -> AuditLog:
        """Return the audit log (§4.6).

        Created on demand as well as in the constructor, so a plugin that
        predates the audit log gains one on first use rather than raising --
        an upgrade step would do the same thing later and less kindly.

        :returns: The log persisted inside this plugin.
        """
        log = getattr(self, "_audit", None)
        if log is None:
            log = self._audit = AuditLog()
        return log

    # ------------------------------------------------------------------
    # IExtractionPlugin
    # ------------------------------------------------------------------

    def extractCredentials(self, request: Any) -> dict[str, Any]:
        """Extract credentials deposited by the callback view.

        Nothing else in the request is inspected, so this is a dictionary
        lookup on every ordinary request (I6).

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

    def authenticateCredentials(
        self, credentials: dict[str, Any]
    ) -> tuple[str, str] | None:
        """Resolve external credentials to a Plone principal.

        On first sight of an identity a userid is minted (I1/D10) and a
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
        is_new_user = userid is None
        if is_new_user:
            userid = mint_userid()
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
                is_new_identity=is_new_user,
            )
        )
        return (userid, userid)

    # ------------------------------------------------------------------
    # ICredentialsResetPlugin
    # ------------------------------------------------------------------

    def resetCredentials(self, request: Any, response: Any) -> None:
        """Drop any credentials this plugin put on the request.

        The session ticket and JWT are owned by ``plone.session`` and
        ``jwt_auth``; PAS resets those through their own plugins.

        :param request: The current request.
        :param response: The current response.
        """
        if hasattr(request, "other"):
            request.other.pop(CREDENTIALS_KEY, None)

    # ------------------------------------------------------------------
    # IChallengePlugin (opt-in, §4.1)
    # ------------------------------------------------------------------

    def challenge(self, request: Any, response: Any) -> bool:
        """Redirect an unauthorized request to the provider picker.

        :param request: The current request.
        :param response: The current response.
        :returns: Whether the challenge was issued.
        """
        if not self.challenge_enabled:
            return False
        url = f"{self._portal_url()}/{LOGIN_VIEW}"
        came_from = request.get("ACTUAL_URL", "")
        if came_from:
            url = f"{url}?came_from={came_from}"
        response.redirect(url, lock=True)
        return True

    def _portal_url(self) -> str:
        """Return the portal URL.

        :returns: Absolute URL of the Plone site this plugin lives in.
        """
        from plone import api

        return api.portal.get().absolute_url()

    # ------------------------------------------------------------------
    # Linking API -- used by the ``@identities`` service (§Gate 2)
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
        :raises IdentityCollision: When another userid already owns it (S3).
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
        :raises LockoutRefused: When this is the user's last way in (S4).
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
        """Decide whether unlinking would lock the user out (S4).

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
        is not a way in. Counting it would defeat S4 entirely: the guard would
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

    def _source_users(self) -> Any:
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
        S4 guard does not mistake it for one.

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
        ``mutable_properties`` for something else (I5).

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


classImplements(
    IdentityPlugin,
    IExtractionPlugin,
    IAuthenticationPlugin,
    ICredentialsResetPlugin,
    IChallengePlugin,
)

InitializeClass(IdentityPlugin)


__all__ = ["IdentityPlugin", "mint_userid"]
