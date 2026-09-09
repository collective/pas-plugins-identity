"""One serializer per scope, and the lookup that finds them.

A relying party asks in scopes and a person consents in scopes, so a scope is
what a serializer is registered for: a named multi-adapter on the site and the
request, where the name **is** the scope name. There is one module per shipped
scope, and every one of them subclasses
:class:`~pas.plugins.identity.server.serializers.base.ScopeSerializer`. A
downstream package adds a scope, or replaces one of these, by registering
another named adapter.

The contract is
:class:`~pas.plugins.identity.server.interfaces.IScopeSerializer` and the
reasoning behind its shape is there. This module is the lookup.

**What replaced what.** The scopes and their claims used to be two module-level
dicts in :mod:`~pas.plugins.identity.server.claims`: a scope-to-claim-names
mapping and a claim-name-to-lambda mapping. The only way a downstream package
could add either was to mutate one of those dicts at import time, which is
load-order dependent, cannot be uninstalled, and lets two packages collide
without a word -- while the scopes vocabulary's own docstring advertised the
extension as though it were supported. It is supported now.

**When there is no request.** The lookup answers with nothing rather than
raising. Every caller reaches it through a browser request in practice, and a
serializer registered for a browser layer could not be found without one
anyway; a script that reaches this without a request gets an honest empty
answer instead of a partial one that looks authoritative.
"""

from pas.plugins.identity.server.interfaces import IScopeSerializer
from pas.plugins.identity.server.serializers.base import ScopeSerializer
from plone import api
from plone.api.exc import CannotGetPortalError
from plone.base.interfaces import IPloneSiteRoot
from zope.component import getAdapters
from zope.globalrequest import getRequest
from zope.publisher.interfaces.browser import IBrowserRequest


#: What a scope serializer is registered for.
#:
#: Named here because a test registering one has to say the same pair, and a
#: second spelling of it is a registration that never wins and never says why.
SERIALIZER_FOR = (IPloneSiteRoot, IBrowserRequest)


def scope_serializers() -> list[tuple[str, ScopeSerializer]]:
    """Return every registered scope serializer.

    Sorted by scope name, so the discovery document is byte-stable between
    requests -- a client that caches it and diffs on change should see a
    change only when one happened.

    The unnamed adapter is skipped. A serializer registered without a name is
    a registration mistake rather than a scope called ``""``, and releasing
    its claims under a scope no client can ask for would hide the mistake.

    :returns: Pairs of scope name and serializer, sorted by name. Empty when
        there is no site or no request.
    """
    request = getRequest()
    if request is None:  # pragma: no cover - can't-happen: every caller is a view
        return []
    try:
        site = api.portal.get()
    except CannotGetPortalError:  # pragma: no cover - a lookup outside a site
        return []
    return sorted(
        (name, serializer)
        for name, serializer in getAdapters((site, request), IScopeSerializer)
        if name
    )


def serializer_for(scope: str) -> ScopeSerializer | None:
    """Return the serializer registered for one scope.

    :param scope: The scope name.
    :returns: The serializer, or ``None`` when nothing is registered for it.
    """
    for name, serializer in scope_serializers():
        if name == scope:
            return serializer
    return None


def declared_scopes() -> list[str]:
    """Return the name of every scope a serializer is registered for.

    :returns: Scope names, sorted. Does not include ``openid``, which
        releases nothing and therefore has no serializer.
    """
    return [name for name, _serializer in scope_serializers()]


def declared_claims(scope: str) -> tuple[str, ...]:
    """Return the claim names one scope declares.

    What the consent screen shows and what the discovery document advertises,
    which is why it is read from the declaration rather than by serializing
    somebody: a scope's answer must not depend on which user is asking.

    :param scope: The scope name.
    :returns: Claim names, empty for a scope nothing is registered for.
    """
    serializer = serializer_for(scope)
    if serializer is None:
        return ()
    return tuple(serializer.claims)


__all__ = [
    "SERIALIZER_FOR",
    "ScopeSerializer",
    "declared_claims",
    "declared_scopes",
    "scope_serializers",
    "serializer_for",
]
