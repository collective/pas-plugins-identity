"""The public API of ``pas.plugins.identity``.

One import path, for everything a downstream package needs::

    from pas.plugins.identity import api

    api.IProfileEnricher            # register against
    api.IdentityLinked              # subscribe to
    api.UserProfile                 # type hint, adapt
    api.profile.get_current()       # do

**It carries four kinds of thing, not one.** A façade of helper functions
would miss most of what a policy package actually imports: interfaces to
register adapters against, event classes to subscribe to, content classes to
type-hint and adapt, and the constants the container is addressed by. Those
are the surface; the functions are the smaller half.

**Namespaces.** Operations are grouped the way :mod:`plone.api` groups them,
which is the idiom this audience already knows:

==================  =========================================================
:mod:`.profile`     Finding a person's Profile
:mod:`.portrait`    Their picture, in whichever store holds it
:mod:`.provider`    The providers this site signs people in against
:mod:`.claims`      What this site releases about a person  (``[server]``)
:mod:`.clients`     The OAuth clients registered here       (``[server]``)
==================  =========================================================

**Conventions**, fixed once so that the surface stays predictable as it grows:

- **Arguments.** A userid where the question is about a *person*; the object
  where it is about a *Profile*.
- **Returns.** Lookups answer ``None``. Operations that cannot proceed raise.
- **Names.** Verb first, no redundant noun: ``api.profile.get``, never
  ``api.get_profile``, and no ``_of`` suffixes -- the namespace already says
  what the noun is.
- **No implicit current user.** :func:`.profile.get` takes its argument;
  :func:`.profile.get_current` takes none. A default that fell back to the
  current user would make ``None`` mean both "I did not say whose" and "the
  lookup missed".

**This module imports every layer and nothing imports it.** That is enforced
by an import-linter contract rather than left to discipline, because ``api``
spans ``core`` and ``server`` both: anything in ``core`` importing it would
reach the optional layer transitively and break the no-extras install. The
same reason ``plone.api`` is not imported by Plone core.

Naming note: ``from pas.plugins.identity import api`` shadows
``from plone import api``, and a module wanting both should alias one::

    from pas.plugins.identity import api as identity_api
"""

from pas.plugins.identity.api import claims
from pas.plugins.identity.api import clients
from pas.plugins.identity.api import portrait
from pas.plugins.identity.api import profile
from pas.plugins.identity.api import provider
from pas.plugins.identity.core.container import GROUP
from pas.plugins.identity.core.container import PROFILE
from pas.plugins.identity.core.contents.group import UserGroup
from pas.plugins.identity.core.contents.profile import UserProfile
from pas.plugins.identity.core.events import EmailVerified
from pas.plugins.identity.core.events import ExternalIdentityAuthenticated
from pas.plugins.identity.core.events import IdentityLinked
from pas.plugins.identity.core.events import IdentityUnlinked
from pas.plugins.identity.core.events import SessionsRevoked
from pas.plugins.identity.core.events import UserClaimsRefreshed
from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.interfaces import ClaimsError
from pas.plugins.identity.core.interfaces import IAuditSink
from pas.plugins.identity.core.interfaces import IAuditSource
from pas.plugins.identity.core.interfaces import IdentityCollision
from pas.plugins.identity.core.interfaces import IDriver
from pas.plugins.identity.core.interfaces import IGroupContent
from pas.plugins.identity.core.interfaces import IIdentityProfileCatalog
from pas.plugins.identity.core.interfaces import IIdentityStore
from pas.plugins.identity.core.interfaces import IProfileEnricher
from pas.plugins.identity.core.interfaces import IUserContent
from pas.plugins.identity.core.interfaces import IUserGroup
from pas.plugins.identity.core.interfaces import IUserProfile
from pas.plugins.identity.core.interfaces import ProviderEmail
from pas.plugins.identity.core.interfaces import ProviderUnusable
from pas.plugins.identity.core.store import IdentityRecord
from pas.plugins.identity.core.utils.propertymap import MAPPABLE_FIELDS


# Sorted, because RUF022 requires it -- so this list does not group by kind.
# The docstring above is where the four kinds are named.
__all__ = [
    "GROUP",
    "MAPPABLE_FIELDS",
    "PROFILE",
    "Claims",
    "ClaimsError",
    "EmailVerified",
    "ExternalIdentityAuthenticated",
    "IAuditSink",
    "IAuditSource",
    "IDriver",
    "IGroupContent",
    "IIdentityProfileCatalog",
    "IIdentityStore",
    "IProfileEnricher",
    "IUserContent",
    "IUserGroup",
    "IUserProfile",
    "IdentityCollision",
    "IdentityLinked",
    "IdentityRecord",
    "IdentityUnlinked",
    "ProviderEmail",
    "ProviderUnusable",
    "SessionsRevoked",
    "UserClaimsRefreshed",
    "UserGroup",
    "UserProfile",
    "claims",
    "clients",
    "portrait",
    "profile",
    "provider",
]
