"""``@user-account`` -- what an administrator cannot otherwise find out.

Two questions kept coming up in the users control panel and neither had an
answer anywhere in Plone:

*Which providers has this person configured?* ``@users/<id>`` does carry
``identities`` -- this package puts them there -- but as bare provider ids and
subjects. An administrator looking at a row wants the provider's *name*, when
it was linked and when it last worked, and whether the provider is still
enabled at all: an identity against a provider somebody has since turned off
is exactly the case that looks like a broken login and reads like nothing.

*When did this person last authenticate?* Nothing in Plone records it. This
package's audit log does, for every way in -- a federated sign-in, a magic
link and an ordinary password login all record ``authenticated`` -- so the
answer exists and has never been reachable per user without reading the whole
log.

So one endpoint answers both, and answers them for one user at a time. That
shape is deliberate: the audit log is bounded per user rather than globally,
so folding either answer into the ``@users`` *listing* would read one bounded
log per row on every page of it. An administrator opens this for the person
they are looking at.

``Manage users`` throughout, which is the permission the users control panel
itself is behind. The one exception is a caller asking about themselves: the
same facts are already theirs through ``@identities`` and ``@audit-log``, and
refusing them here would only mean the frontend needing two code paths to
show one panel.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core import audit
from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.interfaces import IAuditSink
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.pas import PLUGIN_ID
from plone import api
from Products.CMFCore.permissions import ManageUsers
from zope.component import queryUtility


#: What a caller needs to ask about somebody else.
MANAGE_PERMISSION = ManageUsers

#: How many recent authentication events are returned by default.
DEFAULT_EVENTS = 10

#: Ceiling on ``events``. The log is bounded per user already; this bounds
#: the response.
MAX_EVENTS = 100

#: Events that mean somebody got in. ``authenticated`` covers every way --
#: a federated sign-in, a magic link and an ordinary password login all record
#: it -- which is what makes "when did this person last authenticate" a
#: question with one answer rather than three.
SUCCESSFUL_LOGIN = audit.AUTHENTICATED


def identity_plugin():
    """Return the core PAS plugin, or ``None``.

    :returns: The plugin, or ``None`` when this package is not installed in
        the current site.
    """
    plugin = getattr(api.portal.get_tool("acl_users"), PLUGIN_ID, None)
    if plugin is None:
        logger.debug("No %s plugin in this site", PLUGIN_ID)
    return plugin


def render_identity(record) -> JSONDict:
    """Describe one linked identity for an administrator.

    :param record: An :class:`~pas.plugins.identity.core.store.IdentityRecord`.
    :returns: JSON-ready mapping. The provider is named and styled, so a
        panel can show the same button the person signs in with; and its
        current state is included, because an identity against a provider
        somebody has since turned off looks like a broken login and reads
        like nothing.
    """
    provider = get_provider(record.provider)
    entry = {
        "provider": record.provider,
        "title": provider.title if provider is not None else record.provider,
        "subject": record.subject,
        "created": record.created.isoformat(),
        "last_login": record.last_login.isoformat() if record.last_login else None,
        # Three states rather than two: configured and working, configured and
        # switched off, and not configured at all -- which is what a provider
        # deleted out from under a stored identity looks like.
        "provider_enabled": bool(provider is not None and provider.enabled),
        "provider_configured": provider is not None,
        "groups": list(record.groups),
    }
    if provider is not None:
        entry.update(provider.style())
    return entry


def audit_entries(userid: str) -> list:
    """Return a user's recorded authentication events, newest first.

    :param userid: Canonical Plone userid.
    :returns: The entries, empty when a site has unregistered the sink --
        which is a configuration answer rather than an error, exactly as it
        is for ``@audit-log``.
    """
    sink = queryUtility(IAuditSink, default=None)
    return [] if sink is None else sink.entries(userid)


def last_authenticated(entries: list) -> str | None:
    """Return when a user last got in, by any route.

    :param entries: That user's audit entries, newest first.
    :returns: An ISO timestamp, or ``None`` when the log holds no successful
        authentication for them -- which is not the same as "never logged
        in": the log is bounded, and an account dormant longer than the
        retention period has had its entries purged.
    """
    for entry in entries:
        if entry.event == SUCCESSFUL_LOGIN and entry.success:
            # Newest first, so the first match is the answer.
            return entry.timestamp.isoformat()
    return None


__all__ = [
    "DEFAULT_EVENTS",
    "MANAGE_PERMISSION",
    "MAX_EVENTS",
    "audit_entries",
    "identity_plugin",
    "last_authenticated",
    "render_identity",
]
