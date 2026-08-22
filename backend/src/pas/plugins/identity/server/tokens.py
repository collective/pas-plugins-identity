"""Access tokens.

Self-encoded, per C7: everything a resource server needs to accept the token
is inside the token, so issuing one is a signature over data already in hand
and writes nothing. That is what keeps the token endpoint's ZODB write
frequency at human-login frequency rather than at API-call frequency, and it
is the reason authorization codes and refresh tokens -- which genuinely must
be single-use -- are the only things this layer persists.

The cost of that choice is stated in D3 and has to stay stated: there is no
denylist in v1, so a token remains good until it expires. The access-token
lifetime is therefore also the worst case between revoking a client and the
last token minted for it going quiet.
"""

from datetime import datetime
from datetime import timedelta
from datetime import UTC
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.server.claims import claims_for
from pas.plugins.identity.server.claims import OPENID_SCOPE
from pas.plugins.identity.server.interfaces import ServerError
from pas.plugins.identity.server.keys import ALGORITHM
from pas.plugins.identity.server.keys import current_key
from pas.plugins.identity.server.keys import key_set
from plone import api

import secrets


#: Registry key holding the issuer URL.
ISSUER_RECORD = "pas.plugins.identity.server_issuer"

#: Registry key holding the access-token lifetime, in seconds.
TTL_RECORD = "pas.plugins.identity.server_access_token_ttl"

#: How long an ``id_token`` is good for, in seconds. Much shorter than an
#: access token: a relying party validates it the moment it arrives and then
#: has its own session, so a long-lived one is only a longer window in which
#: a leaked copy is worth something.
ID_TOKEN_TTL = 300

#: Token type, as it appears in a token endpoint response. Not a credential:
#: S105 matches the name, not the value, and RFC 6749 fixes this string.
TOKEN_TYPE = "Bearer"  # noqa: S105


class TokenError(ServerError):
    """A token cannot be minted, or will not be accepted.

    A subclass rather than a bare :class:`ServerError` so that the Bearer
    plugin can refuse a request without having to distinguish a malformed
    token from an unknown client.
    """


def _signing_key() -> JSONDict:
    """Return the key to sign with, as a token-layer failure.

    The key ring speaks :class:`ServerError`, which is right for it: an empty
    ring is a configuration problem, not a token problem. Everything reached
    through this module, though, is documented as raising
    :class:`TokenError`, and the Bearer plugin catches exactly that.

    :returns: The active private JWK.
    :raises TokenError: When the ring is empty.
    """
    try:
        return current_key()
    except ServerError as exc:
        raise TokenError(str(exc)) from exc


def _verification_keys():
    """Return the key set to verify against, as a token-layer failure.

    :returns: The authlib key set.
    :raises TokenError: When the ring is empty.
    """
    try:
        return key_set()
    except ServerError as exc:
        raise TokenError(str(exc)) from exc


def get_issuer() -> str:
    """Return the configured issuer URL.

    Configured rather than derived from the portal URL: it goes in every
    token as ``iss`` and in the discovery document, and a relying party
    compares it byte for byte. A proxy, a virtual host or a stray trailing
    slash would otherwise be enough to make tokens stop validating.

    :returns: The issuer URL, without a trailing slash.
    :raises TokenError: When no issuer is configured. The server signs
        nothing until the site has said what it is called.
    """
    issuer = (api.portal.get_registry_record(ISSUER_RECORD, default="") or "").strip()
    if not issuer:
        raise TokenError(
            "No issuer is configured for the authorization server; set "
            f"{ISSUER_RECORD} to the URL relying parties will see"
        )
    return issuer.rstrip("/")


def get_ttl() -> int:
    """Return the access-token lifetime in seconds.

    :returns: The configured lifetime, or the D3 default of fifteen minutes
        when the record is missing.
    """
    return api.portal.get_registry_record(TTL_RECORD, default=900) or 900


def mint_access_token(
    client_id: str,
    subject: str,
    scope: str = "",
    ttl: int | None = None,
) -> tuple[str, int]:
    """Mint a signed access token.

    :param client_id: The client the token is issued to. It is also the
        audience: a token minted for one client must not be replayable at a
        resource server that trusts another.
    :param subject: The Plone userid the token acts for. For a
        client-credentials grant this is the client itself, which is why the
        Bearer plugin has to look at ``sub`` rather than assume a human.
    :param scope: Space-separated granted scopes.
    :param ttl: Lifetime override in seconds; the configured lifetime by
        default.
    :returns: The token and its lifetime in seconds.
    :raises TokenError: When there is no issuer or no signing key.
    """
    from authlib.jose import JsonWebToken

    lifetime = get_ttl() if ttl is None else ttl
    now = datetime.now(UTC)
    key = _signing_key()
    payload = {
        "iss": get_issuer(),
        "sub": subject,
        "aud": client_id,
        "client_id": client_id,
        "scope": scope,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=lifetime)).timestamp()),
        # Present so a deployment that later grows a denylist has something
        # to put in it, and so two tokens minted in the same second for the
        # same subject are still distinguishable in an audit trail.
        "jti": secrets.token_urlsafe(16),
    }
    header = {"alg": ALGORITHM, "kid": key["kid"], "typ": "at+jwt"}
    token = JsonWebToken([ALGORITHM]).encode(header, payload, key)
    # authlib hands back bytes; everything downstream wants a str.
    return token.decode("ascii"), lifetime


def decode_access_token(token: str, audience: str | None = None) -> JSONDict:
    """Validate a token and return its claims.

    :param token: The encoded token.
    :param audience: When given, the client id the token must be addressed
        to. Omitting it validates everything except the audience, which is
        only right for a caller that has no opinion about who the token was
        for.
    :returns: The validated claims.
    :raises TokenError: For anything wrong with the token -- bad signature,
        expired, wrong issuer, wrong audience, unparseable. One exception for
        all of them on purpose: telling a caller *which* check failed tells
        an attacker which part of their forgery to work on next.
    """
    from authlib.jose import JsonWebToken
    from authlib.jose.errors import JoseError

    claims_options = {
        "iss": {"essential": True, "value": get_issuer()},
        "exp": {"essential": True},
        "sub": {"essential": True},
    }
    if audience is not None:
        claims_options["aud"] = {"essential": True, "value": audience}

    try:
        claims = JsonWebToken([ALGORITHM]).decode(
            token,
            key=_verification_keys(),
            claims_options=claims_options,
        )
        claims.validate()
    except JoseError as exc:
        raise TokenError("The access token was refused") from exc
    except (AttributeError, ValueError) as exc:
        # A token that is not even a JWS reaches authlib as something it
        # cannot split; that is a refusal, not a server error.
        raise TokenError("The access token was refused") from exc
    return dict(claims)


def mint_id_token(
    client_id: str,
    subject: str,
    scope: str = "",
    nonce: str = "",
) -> str:
    """Mint an ``id_token`` for a relying party.

    An access token and an ``id_token`` say different things and are read by
    different parties, which is why this is not a flag on
    :func:`mint_access_token`. An access token is a *credential*: the relying
    party carries it back here and this server reads it. An ``id_token`` is a
    *statement*, signed for the relying party to read itself and never sent
    anywhere. The claims go inside it for that reason -- so a relying party
    learns who signed in without a second round trip -- while the userinfo
    endpoint stays available for the ones that prefer to ask.

    :param client_id: The client the statement is addressed to.
    :param subject: The Plone userid it is about.
    :param scope: Space-separated granted scopes, deciding which claims are
        released.
    :param nonce: The nonce from the authorization request, echoed verbatim.
        This is the relying party's binding between the browser it sent here
        and the token it is now reading; omitting it when one was sent makes
        the token useless to a conforming client, and this package's own
        client refuses such a token outright.
    :returns: The encoded token.
    :raises TokenError: When there is no issuer or no signing key.
    """
    from authlib.jose import JsonWebToken

    now = datetime.now(UTC)
    key = _signing_key()
    payload = {
        **claims_for(subject, scope),
        "iss": get_issuer(),
        "aud": client_id,
        "iat": int(now.timestamp()),
        # Its own lifetime, and a short one: an id_token is consumed the
        # moment it arrives, so it has no reason to outlive the exchange
        # that produced it.
        "exp": int((now + timedelta(seconds=ID_TOKEN_TTL)).timestamp()),
    }
    if nonce:
        payload["nonce"] = nonce
    header = {"alg": ALGORITHM, "kid": key["kid"], "typ": "JWT"}
    return JsonWebToken([ALGORITHM]).encode(header, payload, key).decode("ascii")


def token_response(
    client_id: str,
    subject: str,
    scope: str = "",
    nonce: str = "",
) -> JSONDict:
    """Build a token endpoint response body.

    :param client_id: The client the token is for.
    :param subject: The userid the token acts for.
    :param scope: Space-separated granted scopes.
    :param nonce: The nonce from the authorization request, if any.
    :returns: An RFC 6749 token response, carrying an ``id_token`` when the
        ``openid`` scope was granted and not otherwise. A client that did not
        ask to be told who the user is does not get told.
    """
    token, lifetime = mint_access_token(client_id, subject, scope)
    body: JSONDict = {
        "access_token": token,
        "token_type": TOKEN_TYPE,
        "expires_in": lifetime,
    }
    if scope:
        body["scope"] = scope
    if OPENID_SCOPE in scope.split():
        body["id_token"] = mint_id_token(client_id, subject, scope, nonce)
    return body
