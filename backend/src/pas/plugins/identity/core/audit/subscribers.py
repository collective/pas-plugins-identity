"""Audit subscribers (§4.6).

The audit log is fed from the event contract rather than from the code paths
that fire the events. That keeps the recording in one place and means an
integrator who fires ``IdentityLinked`` from their own code gets an audit
entry for free -- and, less comfortably but more honestly, that anything which
forgets to fire an event is invisible here too.

Failures have no event to hang off: a callback refused for a bad state has no
userid and no successful anything, so those are recorded by the caller.
"""

from pas.plugins.identity.core.audit import AUTHENTICATED
from pas.plugins.identity.core.audit import CLAIMS_REFRESHED
from pas.plugins.identity.core.audit import EMAIL_VERIFIED
from pas.plugins.identity.core.audit import IDENTITY_LINKED
from pas.plugins.identity.core.audit import IDENTITY_UNLINKED
from pas.plugins.identity.core.audit import record
from pas.plugins.identity.core.events import IEmailVerified
from pas.plugins.identity.core.events import IExternalIdentityAuthenticated
from pas.plugins.identity.core.events import IIdentityLinked
from pas.plugins.identity.core.events import IIdentityUnlinked
from pas.plugins.identity.core.events import IUserClaimsRefreshed
from zope.component import adapter
from zope.globalrequest import getRequest


@adapter(IExternalIdentityAuthenticated)
def record_authentication(event) -> None:
    """Record a successful external authentication.

    :param event: The event.
    """
    record(
        event.userid,
        AUTHENTICATED,
        event.provider,
        True,
        {
            "subject": event.subject,
            "is_new_user": event.is_new_user,
            "is_new_identity": event.is_new_identity,
        },
        request=getRequest(),
    )


@adapter(IIdentityLinked)
def record_link(event) -> None:
    """Record an identity being linked.

    :param event: The event.
    """
    record(
        event.userid,
        IDENTITY_LINKED,
        event.provider,
        True,
        {"subject": event.subject},
        request=getRequest(),
    )


@adapter(IIdentityUnlinked)
def record_unlink(event) -> None:
    """Record an identity being unlinked.

    :param event: The event.
    """
    record(
        event.userid,
        IDENTITY_UNLINKED,
        event.provider,
        True,
        {"subject": event.subject},
        request=getRequest(),
    )


@adapter(IEmailVerified)
def record_email_verified(event) -> None:
    """Record an email address being proven.

    The address is the whole point of the event, so it is stored regardless of
    the PII flag: this package already holds it as an identity subject, and an
    audit entry that will not say *which* address was verified is useless.

    :param event: The event.
    """
    record(
        event.userid,
        EMAIL_VERIFIED,
        "email",
        True,
        {"address": event.address},
        request=getRequest(),
    )


@adapter(IUserClaimsRefreshed)
def record_claims_refresh(event) -> None:
    """Record stored claims being refreshed under the D2 policy.

    The claims themselves are not recorded: they are the user's personal data,
    they change on every login, and the useful fact is that a refresh happened.

    :param event: The event.
    """
    record(
        event.userid,
        CLAIMS_REFRESHED,
        event.provider,
        True,
        request=getRequest(),
    )
