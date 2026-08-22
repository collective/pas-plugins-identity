"""Audit subscribers.

The audit log is fed from the event contract rather than from the code paths
that fire the events. That keeps the recording in one place and means an
integrator who fires ``IdentityLinked`` from their own code gets an audit
entry for free -- and, less comfortably but more honestly, that anything which
forgets to fire an event is invisible here too.

Failures have no event to hang off: a callback refused for a bad state has no
userid and no successful anything, so those are recorded by the caller.
"""

from pas.plugins.identity.core import audit
from pas.plugins.identity.core import events
from pas.plugins.identity.core.audit import record
from zope.component import adapter
from zope.globalrequest import getRequest


@adapter(events.IExternalIdentityAuthenticated)
def record_authentication(event: events.ExternalIdentityAuthenticated) -> None:
    """Record a successful external authentication.

    :param event: The event.
    """
    record(
        event.userid,
        audit.AUTHENTICATED,
        event.provider,
        True,
        {
            "subject": event.subject,
            "is_new_user": event.is_new_user,
            "is_new_identity": event.is_new_identity,
        },
        request=getRequest(),
    )


@adapter(events.IIdentityLinked)
def record_link(event: events.IdentityLinked) -> None:
    """Record an identity being linked.

    :param event: The event.
    """
    record(
        event.userid,
        audit.IDENTITY_LINKED,
        event.provider,
        True,
        {"subject": event.subject},
        request=getRequest(),
    )


@adapter(events.IIdentityUnlinked)
def record_unlink(event: events.IdentityUnlinked) -> None:
    """Record an identity being unlinked.

    :param event: The event.
    """
    record(
        event.userid,
        audit.IDENTITY_UNLINKED,
        event.provider,
        True,
        {"subject": event.subject},
        request=getRequest(),
    )


@adapter(events.IEmailVerified)
def record_email_verified(event: events.EmailVerified) -> None:
    """Record an email address being proven.

    The address is the whole point of the event, so it is stored regardless of
    the PII flag: this package already holds it as an identity subject, and an
    audit entry that will not say *which* address was verified is useless.

    :param event: The event.
    """
    record(
        event.userid,
        audit.EMAIL_VERIFIED,
        "email",
        True,
        {"address": event.address},
        request=getRequest(),
    )


@adapter(events.IUserClaimsRefreshed)
def record_claims_refresh(event: events.UserClaimsRefreshed) -> None:
    """Record stored claims being refreshed on a later login.

    The claims themselves are not recorded: they are the user's personal data,
    they change on every login, and the useful fact is that a refresh happened.

    :param event: The event.
    """
    record(
        event.userid,
        audit.CLAIMS_REFRESHED,
        event.provider,
        True,
        request=getRequest(),
    )
