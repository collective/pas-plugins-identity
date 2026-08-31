"""The OpenID Connect discovery document.

What a relying party reads first, and often the only thing an integrator has
to configure: point a conforming client at the issuer URL and everything else
in this document is how it finds the endpoints, the keys and the capabilities.

Every URL here is built from the *configured issuer*, never from the portal
URL. That is the issuer being configured rather than derived from the
portal URL, paying off rather than a stylistic choice. A
client fetches this document from ``<issuer>/.well-known/openid-configuration``
and then compares the ``issuer`` field to the URL it used, byte for byte; if
the two disagree it must refuse the document. Deriving the endpoints from
``portal_url`` would make that comparison depend on virtual hosting, a proxy
header, or a trailing slash -- which is exactly the class of deployment detail
the configured issuer exists to be immune to.

The document is deliberately a description of what this server *does*, not a
menu of what OIDC allows. Every algorithm, grant and method listed here is one
the code implements and the tests exercise; a client that trusts this document
and then gets a surprise has been lied to by it.
"""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.server.claims import OPENID_SCOPE
from pas.plugins.identity.server.claims import SCOPE_CLAIMS
from pas.plugins.identity.server.grants.codes import CHALLENGE_METHOD
from pas.plugins.identity.server.grants.tokens import get_issuer
from pas.plugins.identity.server.interfaces import GRANT_TYPES
from pas.plugins.identity.server.utils.keys import ALGORITHM


#: Path the document is published at, relative to the issuer. Fixed by
#: RFC 8414 and OpenID Connect Discovery; a client appends it without asking.
WELL_KNOWN = ".well-known"

#: The document's name under :data:`WELL_KNOWN`.
DISCOVERY_DOCUMENT = "openid-configuration"

#: View names of the endpoints the document advertises.
AUTHORIZE_VIEW = "@@oauth-authorize"
TOKEN_VIEW = "@@oauth-token"  # noqa: S105 - a view name, not a credential
USERINFO_VIEW = "@@oauth-userinfo"
JWKS_VIEW = "@@oauth-jwks"

#: Claims that appear in every token this server signs, whatever was asked
#: for. Advertised alongside the scope-gated ones because a relying party
#: reading ``claims_supported`` wants the whole set it might encounter.
ALWAYS_CLAIMS = ("sub", "iss", "aud", "exp", "iat")


def scopes_supported() -> list[str]:
    """Return the scopes a client may ask for.

    :returns: ``openid`` first, then the scopes that release claims, sorted so
        the document is byte-stable between requests -- a client that caches
        it and diffs on change should see a change only when one happened.
    """
    return [OPENID_SCOPE, *sorted(SCOPE_CLAIMS)]


def claims_supported() -> list[str]:
    """Return every claim this server can emit.

    :returns: The always-present claims followed by every scope-gated one,
        deduplicated and sorted.
    """
    gated = {claim for claims in SCOPE_CLAIMS.values() for claim in claims}
    return [*ALWAYS_CLAIMS, *sorted(gated)]


def metadata() -> JSONDict:
    """Return the discovery document.

    :returns: The OpenID provider metadata, ready to serialize.
    :raises TokenError: When no issuer is configured. Publishing a discovery
        document without one would advertise endpoints under whatever URL the
        request happened to arrive on, which is the misconfiguration the
        configured issuer exists to prevent.
    """
    issuer = get_issuer()
    return {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/{AUTHORIZE_VIEW}",
        "token_endpoint": f"{issuer}/{TOKEN_VIEW}",
        "userinfo_endpoint": f"{issuer}/{USERINFO_VIEW}",
        "jwks_uri": f"{issuer}/{JWKS_VIEW}",
        "scopes_supported": scopes_supported(),
        "claims_supported": claims_supported(),
        # One response type, because this server implements one flow. OAuth
        # 2.1 removes the implicit grant and there is no reason to put a
        # token in a URL fragment.
        "response_types_supported": ["code"],
        "response_modes_supported": ["query"],
        "grant_types_supported": list(GRANT_TYPES),
        # ``public`` rather than ``pairwise``: the ``sub`` is the Plone
        # userid, and every relying party sees the same one. Pairwise subjects
        # would need a per-client mapping this server does not keep.
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": [ALGORITHM],
        # ``client_secret_basic`` is first because RFC 6749 §2.3.1 requires a
        # server to accept it and makes the form optional, so it is what an
        # unconfigured client will try; a client that reads this list and
        # takes the head gets the one both ends are surest about.
        # ``none`` is the public-client method, and it is listed because
        # public clients are supported -- with PKCE made mandatory for them,
        # which is what the next line says.
        "token_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post",
            "none",
        ],
        "code_challenge_methods_supported": [CHALLENGE_METHOD],
        # Stated rather than implied: a client reading this knows it may send
        # prompt=none and get login_required back instead of a login page.
        "prompt_values_supported": ["none"],
    }
