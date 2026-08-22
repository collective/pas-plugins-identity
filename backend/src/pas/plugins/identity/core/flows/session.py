"""Flow session storage.

:class:`~pas.plugins.identity.core.flows.FlowManager` needs a mapping that
survives between the two requests of an authorization flow. Plone 6.2 ships no
``session_data_manager`` tool, so the storage lives here: a cookie, signed with
a key from ``plone.keyring`` the way ``plone.session`` signs its auth tickets.

Signed rather than merely encoded, because the cookie carries the ``state``,
the PKCE ``code_verifier`` and the ``nonce``, and the callback has to be
bound to the session that *started* the flow. With an unsigned cookie an
attacker authors all three in their own browser and that binding becomes a
suggestion.

The signing key is derived from the keyring rather than used directly, so a
flow cookie can never be confused with -- or forged from -- anything else
signed with the same ring. Every key in the ring is accepted on verification,
so a rotation does not strand a login that is already in flight.
"""

from collections.abc import Iterator
from collections.abc import MutableMapping
from pas.plugins.identity import logger
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.interfaces import JSONValue
from plone.keyring.interfaces import IKeyManager
from zope.component import getUtility
from ZPublisher.HTTPRequest import HTTPRequest

import hashlib
import hmac
import json


#: Cookie holding the pending flow attempts.
COOKIE_NAME = "__pas_identity_flow"

#: Keyring whose secrets sign the cookie.
KEY_RING = "_system"

#: Domain separator mixed into the derived key, so this signature cannot be
#: replayed against -- or produced by -- another consumer of the same ring.
KEY_PURPOSE = b"pas.plugins.identity.flow.v1"

#: ``Lax`` and not ``Strict``: the provider sends the user back with a
#: top-level GET navigation from its own origin, and ``Strict`` would withhold
#: the cookie on exactly that request -- breaking every login.
COOKIE_SAME_SITE = "Lax"


def _derive(key: str | bytes) -> bytes:
    """Derive this module's signing key from one keyring secret.

    :param key: A secret from the keyring.
    :returns: The derived key.
    """
    material = key.encode("utf-8") if isinstance(key, str) else key
    return hmac.new(material, KEY_PURPOSE, hashlib.sha256).digest()


def signing_keys() -> list[bytes]:
    """Return the derived keys, current first.

    :returns: One derived key per live secret in the ring.
    :raises RuntimeError: When the ring holds no usable secret.
    """
    ring = getUtility(IKeyManager)[KEY_RING]
    keys = [_derive(secret) for secret in ring if secret]
    if not keys:
        raise RuntimeError(f"keyring {KEY_RING!r} holds no secret")
    return keys


def encode(data: JSONDict) -> str:
    """Render a mapping as a signed cookie value.

    :param data: JSON-serializable mapping.
    :returns: ``<payload>.<signature>``, both URL-safe base64.
    """
    from base64 import urlsafe_b64encode

    payload = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = hmac.new(signing_keys()[0], payload, hashlib.sha256).digest()
    return (
        f"{urlsafe_b64encode(payload).decode('ascii')}"
        f".{urlsafe_b64encode(signature).decode('ascii')}"
    )


def decode(raw: str) -> JSONDict:
    """Read a signed cookie value, refusing anything that does not verify.

    A bad cookie is never an error the user sees: it yields an empty session,
    which means the callback finds no attempt and is refused by
    :meth:`~pas.plugins.identity.core.flows.FlowManager.pop` like any other
    unknown state.

    :param raw: The cookie value.
    :returns: The mapping, or ``{}`` when the value is absent, malformed, or
        not signed by a key currently in the ring.
    """
    from base64 import urlsafe_b64decode
    from binascii import Error as BinasciiError

    if not raw or "." not in raw:
        return {}
    encoded_payload, _, encoded_signature = raw.partition(".")
    try:
        payload = urlsafe_b64decode(encoded_payload)
        signature = urlsafe_b64decode(encoded_signature)
    except (BinasciiError, ValueError):
        logger.info("Discarding a flow cookie that is not base64")
        return {}

    if not any(
        hmac.compare_digest(hmac.new(key, payload, hashlib.sha256).digest(), signature)
        for key in signing_keys()
    ):
        logger.info("Discarding a flow cookie with an invalid signature")
        return {}

    try:
        data = json.loads(payload)
    except ValueError:
        logger.info("Discarding a signed flow cookie that is not JSON")
        return {}
    if not isinstance(data, dict):
        logger.info("Discarding a signed flow cookie that is not an object")
        return {}
    return data


class FlowSession(MutableMapping):
    """The flow manager's session, stored in a signed cookie.

    Reads the cookie once on construction and rewrites it on every mutation,
    which is cheap: there is at most a handful of pending attempts, each of
    them a few hundred bytes, and they are dropped as soon as they are used or
    expire.
    """

    def __init__(self, request: HTTPRequest) -> None:
        """Bind the session to a request and its response.

        :param request: The current request.
        """
        self.request = request
        self._data = decode(request.cookies.get(COOKIE_NAME, ""))

    def __getitem__(self, key: str) -> JSONValue:
        """Return one stored value.

        :param key: Key to read.
        :returns: The stored value.
        :raises KeyError: When the key is absent.
        """
        return self._data[key]

    def __setitem__(self, key: str, value: JSONValue) -> None:
        """Store a value and rewrite the cookie.

        :param key: Key to write.
        :param value: JSON-serializable value.
        """
        self._data[key] = value
        self._write()

    def __delitem__(self, key: str) -> None:
        """Drop a value and rewrite the cookie.

        :param key: Key to remove.
        :raises KeyError: When the key is absent.
        """
        del self._data[key]
        self._write()

    def __iter__(self) -> Iterator[str]:
        """Iterate the stored keys.

        :returns: Iterator over the keys.
        """
        return iter(self._data)

    def __len__(self) -> int:
        """Return the number of stored keys.

        :returns: How many keys are stored.
        """
        return len(self._data)

    def _write(self) -> None:
        """Persist the current contents to the response cookie."""
        response = self.request.response
        if not any(self._data.values()):
            # Nothing pending: expire the cookie rather than leave a signed
            # empty object sitting in the browser.
            response.expireCookie(COOKIE_NAME, path="/")
            return
        response.setCookie(
            COOKIE_NAME,
            encode(self._data),
            path="/",
            http_only=True,
            secure=self.request.get("SERVER_URL", "").startswith("https:"),
            same_site=COOKIE_SAME_SITE,
        )
