"""The event contract (§4.3) -- the public API of this package.

Consumers (profile sync, audit log, third-party integrations) subscribe to
these; nothing in this package reaches into another layer directly. Claims
carried by an event always follow the documented schema
(:class:`~pas.plugins.identity.core.interfaces.Claims`).

Schema changes after 1.0 require a version bump note.
"""

from pas.plugins.identity.core.interfaces import Claims
from zope.interface import Attribute
from zope.interface import implementer
from zope.interface import Interface


class IIdentityEvent(Interface):
    """Base for every event this package fires."""

    userid = Attribute("Canonical Plone userid the event concerns.")


class IExternalIdentityAuthenticated(IIdentityEvent):
    """Fired on every successful external authentication."""

    provider = Attribute("Provider id.")
    subject = Attribute("Provider-side subject identifier.")
    claims = Attribute("Normalized claims.")
    is_new_user = Attribute("True when the userid was minted by this login.")
    is_new_identity = Attribute("True when the identity was linked by this login.")


class IIdentityLinked(IIdentityEvent):
    """Fired when an external identity is attached to an existing userid."""

    provider = Attribute("Provider id.")
    subject = Attribute("Provider-side subject identifier.")
    claims = Attribute("Normalized claims.")


class IIdentityUnlinked(IIdentityEvent):
    """Fired when an external identity is detached from a userid."""

    provider = Attribute("Provider id.")
    subject = Attribute("Provider-side subject identifier.")


class IEmailVerified(IIdentityEvent):
    """Fired when an email address is proven to belong to a userid."""

    address = Attribute("The verified email address, lowercased.")


class IUserClaimsRefreshed(IIdentityEvent):
    """Fired when stored claims are updated by the D2 refresh policy."""

    provider = Attribute("Provider id.")
    claims = Attribute("The fresh normalized claims.")


@implementer(IExternalIdentityAuthenticated)
class ExternalIdentityAuthenticated:
    """See :class:`IExternalIdentityAuthenticated`."""

    def __init__(
        self,
        userid: str,
        provider: str,
        subject: str,
        claims: Claims,
        is_new_user: bool,
        is_new_identity: bool,
    ) -> None:
        """Record a successful external authentication.

        :param userid: Canonical Plone userid.
        :param provider: Provider id.
        :param subject: Provider-side subject identifier.
        :param claims: Normalized claims.
        :param is_new_user: Whether the userid was minted by this login.
        :param is_new_identity: Whether the identity was linked by this login.
        """
        self.userid = userid
        self.provider = provider
        self.subject = subject
        self.claims = claims
        self.is_new_user = is_new_user
        self.is_new_identity = is_new_identity


@implementer(IIdentityLinked)
class IdentityLinked:
    """See :class:`IIdentityLinked`."""

    def __init__(
        self, userid: str, provider: str, subject: str, claims: Claims
    ) -> None:
        """Record that an identity was linked.

        :param userid: Canonical Plone userid.
        :param provider: Provider id.
        :param subject: Provider-side subject identifier.
        :param claims: Normalized claims.
        """
        self.userid = userid
        self.provider = provider
        self.subject = subject
        self.claims = claims


@implementer(IIdentityUnlinked)
class IdentityUnlinked:
    """See :class:`IIdentityUnlinked`."""

    def __init__(self, userid: str, provider: str, subject: str) -> None:
        """Record that an identity was unlinked.

        :param userid: Canonical Plone userid.
        :param provider: Provider id.
        :param subject: Provider-side subject identifier.
        """
        self.userid = userid
        self.provider = provider
        self.subject = subject


@implementer(IEmailVerified)
class EmailVerified:
    """See :class:`IEmailVerified`."""

    def __init__(self, userid: str, address: str) -> None:
        """Record that an email address was verified.

        :param userid: Canonical Plone userid.
        :param address: The verified address; stored lowercased.
        """
        self.userid = userid
        self.address = address.lower()


@implementer(IUserClaimsRefreshed)
class UserClaimsRefreshed:
    """See :class:`IUserClaimsRefreshed`."""

    def __init__(self, userid: str, provider: str, claims: Claims) -> None:
        """Record that stored claims were refreshed.

        :param userid: Canonical Plone userid.
        :param provider: Provider id.
        :param claims: The fresh normalized claims.
        """
        self.userid = userid
        self.provider = provider
        self.claims = claims
