"""Provider metadata resolution.

Drivers are static declarations and never perform I/O, but something has to
turn "the ``dex`` provider" into the endpoint set
:mod:`pas.plugins.identity.core.flows` needs. That is this module, and it
knows exactly two ways to do it: a published constant for providers whose
endpoints do not move, and OIDC discovery for everyone else.

Discovery results are cached per issuer, so a login costs one round trip
rather than three. The cache is per process and deliberately dumb -- a
discovery document that changes mid-TTL is a provider migration, which is
rare, operator-visible, and handled by :func:`forget`.
"""

from datetime import datetime
from datetime import timedelta
from datetime import UTC
from pas.plugins.identity import logger
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.interfaces import FlowError
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.interfaces import ProviderUnusable
from urllib.parse import urlparse

import requests


#: Providers whose endpoints are published and stable, so there is nothing to
#: discover. GitHub is plain OAuth2: it issues no ``id_token`` and the flow
#: falls back to its userinfo endpoint.
STATIC_METADATA: dict[str, JSONDict] = {
    "github": {
        "authorization_endpoint": "https://github.com/login/oauth/authorize",
        "token_endpoint": "https://github.com/login/oauth/access_token",
        "userinfo_endpoint": "https://api.github.com/user",
        # `/user` omits the address of anybody who marked it private and
        # carries no `email_verified` at all. This is where both live.
        "emails_endpoint": "https://api.github.com/user/emails",
    },
}

#: Drivers that discover their metadata, but from an issuer the driver fixes
#: rather than one the operator types. Nobody should be configuring Google's
#: issuer URL by hand.
DRIVER_ISSUERS: dict[str, str] = {
    "google": "https://accounts.google.com",
}

#: The config field a driver declares when the operator supplies its issuer.
#:
#: Asked of the driver rather than looked up in a list of driver ids, which
#: is what this used to be. A list is wrong here for the reason driver
#: frameworks exist: ``plone-identity`` is a ``GenericOIDCDriver`` subclass,
#: it discovers its metadata exactly as its parent does, and naming only the
#: parent meant it was refused for having "no authorization endpoints" --
#: an error about a driver that plainly had one. Any driver that asks an
#: operator for an issuer is discovered from it, including one this package
#: has never heard of.
#:
#: The distinction the old list was keeping is kept: a driver that declares
#: no issuer field -- ``email``, whose magic link never leaves the site --
#: is refused rather than sent to discovery with an empty URL.
ISSUER_FIELD = "issuer"

#: Where an OIDC issuer publishes its metadata (RFC 8414).
DISCOVERY_PATH = "/.well-known/openid-configuration"

#: How long a discovery document is trusted before it is fetched again.
DISCOVERY_TTL = timedelta(hours=12)

#: Network timeout for discovery, in seconds. A provider that cannot answer
#: this quickly is down, and a login should say so rather than hang.
DISCOVERY_TIMEOUT = 10

#: Issuer -> (fetched at, metadata).
_CACHE: dict[str, tuple[datetime, JSONDict]] = {}


def forget(issuer: str | None = None) -> None:
    """Drop cached discovery, for one issuer or for all of them.

    Called by the control panel's test-connection action, and by tests.

    :param issuer: Issuer to forget; ``None`` clears the whole cache.
    """
    if issuer is None:
        _CACHE.clear()
    else:
        _CACHE.pop(issuer, None)


def metadata_for(provider: ProviderConfig) -> JSONDict:
    """Return the endpoint metadata for a configured provider.

    :param provider: The configured provider.
    :returns: Metadata carrying at least an ``authorization_endpoint`` and a
        ``token_endpoint``; OIDC providers additionally carry ``issuer`` and
        ``jwks``.
    :raises ProviderUnusable: When the driver has no metadata source or the
        issuer is unconfigured.
    :raises FlowError: When discovery itself fails.
    """
    static = STATIC_METADATA.get(provider.driver_id)
    if static is not None:
        return dict(static)
    return discover(issuer_for(provider))


def issuer_for(provider: ProviderConfig) -> str:
    """Return the issuer whose metadata describes a provider.

    :param provider: The configured provider.
    :returns: The issuer URL, without a trailing slash.
    :raises ProviderUnusable: When the driver discovers nothing, or the
        operator has not configured an issuer. Both are permanent, which is
        why they are not the plain :class:`FlowError` a failed discovery
        raises.
    """
    fixed = DRIVER_ISSUERS.get(provider.driver_id)
    if fixed is not None:
        return fixed
    if not _asks_for_an_issuer(provider):
        raise ProviderUnusable(
            f"{provider.provider_id}: driver {provider.driver_id!r} has no "
            "authorization endpoints"
        )
    issuer = (provider.config.get("issuer") or "").strip().rstrip("/")
    if not issuer:
        raise ProviderUnusable(f"{provider.provider_id}: no issuer configured")
    return issuer


def _asks_for_an_issuer(provider: ProviderConfig) -> bool:
    """Whether this provider's driver takes an issuer from the operator.

    :param provider: The configured provider.
    :returns: Whether the driver declares an ``issuer`` config field. False
        for a driver whose metadata is fixed or absent, and for a provider
        whose driver has been uninstalled -- which is the same answer as
        "nowhere to discover from", and the right one.
    """
    driver = provider.driver
    return driver is not None and ISSUER_FIELD in driver.settings_schema


def discover(issuer: str) -> JSONDict:
    """Fetch and cache an issuer's discovery document and its JWKS.

    :param issuer: Issuer URL, without a trailing slash.
    :returns: The metadata, with the key set under ``jwks``.
    :raises FlowError: When the provider cannot be reached, answers with
        something that is not a discovery document, names a different issuer
        than the one asked (RFC 8414 section 3.3), or tries to downgrade the
        connection.
    """
    cached = _CACHE.get(issuer)
    if cached is not None and datetime.now(UTC) - cached[0] < DISCOVERY_TTL:
        return dict(cached[1])

    secure = urlparse(issuer).scheme == "https"
    if not secure:
        # Plain HTTP is the operator's explicit choice -- they typed this
        # issuer URL -- and it is how the compose provider is reached in the
        # functional tests. It is still worth a line in the log.
        logger.warning("Discovering %s over plain HTTP", issuer)

    metadata = _fetch(f"{issuer}{DISCOVERY_PATH}", issuer, secure)

    declared = str(metadata.get("issuer", "")).rstrip("/")
    if declared != issuer:
        # A document naming someone else is either a misconfiguration or an
        # issuer-substitution attempt; neither is safe to authenticate on.
        raise FlowError(f"{issuer}: discovery document declares issuer {declared!r}")

    jwks_uri = metadata.get("jwks_uri")
    if jwks_uri:
        metadata["jwks"] = _fetch(jwks_uri, issuer, secure)
    else:
        # Not fatal: a provider with no JWKS simply cannot take the id_token
        # path, and the flow layer already refuses that on its own terms.
        logger.info("%s: discovery document publishes no jwks_uri", issuer)

    _CACHE[issuer] = (datetime.now(UTC), metadata)
    return dict(metadata)


def _fetch(url: str, issuer: str, secure: bool) -> JSONDict:
    """GET a JSON document from a provider.

    :param url: Absolute URL to fetch.
    :param issuer: Issuer the fetch belongs to, for error messages.
    :param secure: Whether the issuer itself was reached over HTTPS, in which
        case a URL it points at may not downgrade to plain HTTP.
    :returns: The decoded document.
    :raises FlowError: When the URL downgrades the connection, the request
        fails, or the answer is not a JSON object.
    """
    if secure and urlparse(url).scheme != "https":
        raise FlowError(f"{issuer}: refusing to downgrade to {url!r}")
    try:
        response = requests.get(url, timeout=DISCOVERY_TIMEOUT)
        response.raise_for_status()
        document = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise FlowError(f"{issuer}: could not fetch {url}: {exc}") from exc
    if not isinstance(document, dict):
        raise FlowError(f"{issuer}: {url} did not return a JSON object")
    return document
