"""Running the enrichers a deployment has installed.

The extension point for everything the claim-to-field property map cannot
express. The map moves a scalar from a provider document to one of four
Profile fields; an enricher runs code against the whole payload and writes
whatever the Profile's behaviors actually carry. The case it was built for is
an add-on whose behavior adds a **list** field, which the map cannot reach at
all: ``_scalar`` reads a list as an absent claim, deliberately, so that an
OIDC ``address`` object is never written into somebody's location as a repr.

The contract is :class:`~pas.plugins.identity.core.interfaces.IProfileEnricher`
and the reasoning behind its shape is there. This module is the plumbing:
find them, run them in a defined order, keep one from breaking the rest, and
fire a single modification event for whatever they changed between them.

**Nothing here decides what may be written.** An enricher is trusted code and
runs elevated, because the person it writes for is mid-login and holds no
roles. The package's own ownership fence is not applied on its behalf either
-- the scalar comparison that fence uses answers the wrong question about a
list -- so each enricher is handed a private mapping and makes that decision
itself. See the interface for why that is not something this module can do
for them.
"""

from collections.abc import Iterable
from pas.plugins.identity import logger
from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.interfaces import IProfileEnricher
from persistent.mapping import PersistentMapping
from zope.annotation.interfaces import IAnnotations
from zope.component import getUtilitiesFor
from zope.lifecycleevent import modified


#: Annotation key holding every enricher's private mapping, keyed by the name
#: it is registered under.
#:
#: Separate from the annotation the package's own claim sync uses. That one is
#: a flat mapping of field name to last-written value and is read by
#: ``_provider_may_write`` on every login; an enricher writing into it could
#: silently change who owns ``fullname``. A namespace per enricher also means
#: two add-ons cannot collide, and that removing an add-on leaves a mapping
#: nothing reads rather than one something else misreads.
ENRICHER_VALUES_KEY = "pas.plugins.identity.enrichers"


def memory_for(profile, name: str) -> PersistentMapping:
    """Return the private mapping belonging to one enricher.

    Created on first use. Public because a test, a migration or an add-on's
    own uninstall step has a legitimate reason to read or clear it.

    :param profile: The Profile.
    :param name: The name the enricher is registered under.
    :returns: That enricher's mapping, empty the first time.
    """
    annotations = IAnnotations(profile)
    if ENRICHER_VALUES_KEY not in annotations:
        annotations[ENRICHER_VALUES_KEY] = PersistentMapping()
    store = annotations[ENRICHER_VALUES_KEY]
    if name not in store:
        store[name] = PersistentMapping()
    return store[name]


def _changed_fields(result: object, name: str) -> list[str]:
    """Read an enricher's return value as a list of field names.

    Defensive because the return value decides whether a modification event
    fires, and an enricher that returns ``None`` -- which a function with no
    explicit return does -- would otherwise raise here rather than in the code
    that actually got it wrong. A string is refused rather than iterated: a
    single field name returned bare would otherwise arrive as a list of its
    characters and be reported as several fields.

    :param result: Whatever the enricher returned.
    :param name: The enricher's name, for the log line.
    :returns: The field names, empty when there is nothing usable.
    """
    if result is None:
        return []
    if isinstance(result, str) or not isinstance(result, Iterable):
        logger.warning(
            "Enricher %r returned %r rather than a list of field names; "
            "treating it as no change",
            name,
            type(result).__name__,
        )
        return []
    return [str(field) for field in result]


def enrich_profile(profile, claims: Claims, provider=None) -> list[str]:
    """Run every installed enricher against one Profile.

    Ordered by registered name, so a site with two enrichers gets the same
    order on every login and on every instance. That is a weak guarantee and
    a deliberate one: it makes runs reproducible without implying that
    enrichers may depend on each other, which they may not.

    Each is isolated. An enricher that raises is logged with its traceback and
    the next one runs, because the alternative is an add-on defect that stops
    everybody signing in -- including whoever would go and remove it. This is
    the same rule the enrichment fetch already follows in
    :meth:`~pas.plugins.identity.core.flows.IdentityFlow._enrich`, for the
    same reason.

    One modification event is fired at the end when anything changed, not one
    per enricher: the event reindexes the Profile and re-runs the completeness
    check, and doing that twice for one login is work nobody asked for. It is
    fired at all because the writes here are writes like any other -- the
    catalog carries these fields for a site that indexes them, and
    ``reconcile`` has to see a field an enricher has just filled.

    :param profile: The Profile, after the package's own writes.
    :param claims: The normalized claims, whose ``raw`` is the provider's
        payload.
    :param provider: The provider configuration this login came through, or
        ``None`` where there is no provider. Passed straight through: an
        enricher reads ``driver_id`` to know what shape the payload is, which
        is the alternative to sniffing for a key and firing on the wrong
        login.
    :returns: Every field name any enricher reported changing, in the order
        they ran. Names may repeat when two enrichers touch one field, which
        is reported rather than resolved.
    """
    changed: list[str] = []
    seen: dict[str, str] = {}
    registered = sorted(getUtilitiesFor(IProfileEnricher), key=lambda pair: pair[0])
    for name, enricher in registered:
        try:
            fields = _changed_fields(
                enricher.enrich(profile, claims, provider, memory_for(profile, name)),
                name,
            )
        except Exception:
            # Logged with the traceback because this is somebody else's code
            # failing inside our login, and the message alone rarely says
            # which add-on to go and look at.
            logger.exception(
                "Enricher %r failed for %s; the login continues without it",
                name,
                profile.getId(),
            )
            continue
        for field in fields:
            if field in seen and seen[field] != name:
                logger.warning(
                    "Enrichers %r and %r both wrote %r on %s; the later one "
                    "wins and the order is by name",
                    seen[field],
                    name,
                    field,
                    profile.getId(),
                )
            seen[field] = name
        changed.extend(fields)
        if fields:
            logger.debug("Enricher %r wrote %s on %s", name, fields, profile.getId())
    if changed:
        modified(profile)
    return changed


__all__ = ["ENRICHER_VALUES_KEY", "enrich_profile", "memory_for"]
