"""What may go into a claims snapshot built from somebody else's store.

``claims["raw"]`` is the provider's own document, and the login path fills it
from a userinfo response or a token's claims, neither of which carries a
credential. A **migration** fills it from a store this package did not write,
and the two authomatic paths both hand over a structure that does: its
``UserIdentity`` is ``authomatic.core.User.to_dict()``, whose ``credentials``
key is a serialized :class:`authomatic.core.Credentials` holding the access
and refresh tokens for that account.

That matters more than it looks, because ``raw`` does not stay in memory. It
is stored on the :class:`~pas.plugins.identity.core.store.IdentityRecord` as a
``PersistentMapping`` and written out again verbatim by
:mod:`pas.plugins.identity.exportimport.exporter`. A token copied in during a
migration would therefore end up in the ZODB and in every principal document
exported afterwards, which are files that get copied around.

So anything building a snapshot from a foreign store scrubs it on the way in.
Once, here, rather than at each of the call sites that would each have to
remember.
"""

from pas.plugins.identity.core.interfaces import JSONDict


#: Keys never carried into a claims snapshot, whatever a source calls them.
#:
#: authomatic's own ``credentials`` first, since that is the one this package
#: provably meets. The rest are the names an OAuth2 or OIDC payload uses for
#: the same thing, because a dump is a file somebody wrote and the extraction
#: that produced it is not ours: a script that copied a whole token response
#: into ``properties`` is a likelier mistake than a malicious one, and it
#: costs nothing to refuse both. ``id_token`` is here because ``raw`` holds a
#: token's *claims*, never the signed token itself.
#:
#: Matched case-insensitively, and only as whole keys. A substring rule would
#: drop ``secret_santa_nickname``, and a provider's own vocabulary is not
#: something this package gets to redact by guessing.
SECRET_KEYS = frozenset({
    "access_token",
    "client_secret",
    "credentials",
    "id_token",
    "password",
    "refresh_token",
    "secret",
    "token",
    "token_secret",
})


def scrub_payload(payload: object) -> JSONDict:
    """Return a provider payload with nothing that could authenticate anybody.

    Top-level keys only, deliberately. A nested object in a provider document
    is that provider's own structure -- an OIDC ``address``, GitHub's ``plan``
    -- and walking into it to redact by name would mean this package deciding
    what a key it has never seen means. The credential-bearing shapes it does
    meet are all flat.

    :param payload: The provider's document, or anything at all: a dump is a
        file somebody wrote, so a list or a string where an object belongs is
        answered with an empty payload rather than an exception.
    :returns: The payload without :data:`SECRET_KEYS`.
    """
    if not isinstance(payload, dict):
        return {}
    return {
        key: value
        for key, value in payload.items()
        if str(key).casefold() not in SECRET_KEYS
    }


__all__ = ["SECRET_KEYS", "scrub_payload"]
