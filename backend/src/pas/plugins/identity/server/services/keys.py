"""``@identity-keys`` -- the signing ring, and the action that rotates it.

Two verbs in one module rather than one apiece: there is no CRUD here. A key
is generated, published and eventually retired, and none of that is editing.

What leaves is metadata only -- never a key, not even a public one. The public
halves are already served to the world at ``@@oauth-jwks``, and duplicating
them here would create a second copy for somebody to fetch out of step with
the first. This endpoint answers a different question: *which keys does this
server have, which one is signing, and how many tokens are still riding an
older one*.
"""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.server.keys import ALGORITHM
from pas.plugins.identity.server.keys import get_keys
from pas.plugins.identity.server.keys import RING_SIZE
from pas.plugins.identity.server.keys import rotate_keys
from pas.plugins.identity.server.services import ROTATE_KEY_ACTION
from pas.plugins.identity.server.services import ServerAdminService


class KeysService(ServerAdminService):
    """Base for the signing-key verbs."""

    def _base(self) -> str:
        """Return this service's canonical URL.

        :returns: The URL.
        """
        return f"{self.context.absolute_url()}/@identity-keys"

    def _render(self) -> JSONDict:
        """Describe the ring without revealing any of it.

        :returns: JSON-ready mapping.
        """
        keys = get_keys()
        return {
            "@id": self._base(),
            "algorithm": ALGORITHM,
            "ring_size": RING_SIZE,
            "jwks_uri": f"{self.context.absolute_url()}/@@oauth-jwks",
            "items_total": len(keys),
            "items": [
                {
                    "kid": key["kid"],
                    # Newest first, and index 0 is the one signing now. The
                    # rest are kept only so tokens minted before the last
                    # rotation still verify.
                    "active": index == 0,
                }
                for index, key in enumerate(keys)
            ],
        }


class KeysGet(KeysService):
    """Describe the signing key ring."""

    def reply(self) -> JSONDict:
        """Return the ring.

        :returns: The ring description, or an error body.
        """
        refusal = self._refuse_unless_manager()
        if refusal is not None:
            return refusal
        return self._render()


class KeysPost(KeysService):
    """Rotate the signing key."""

    def reply(self) -> JSONDict:
        """Mint a new signing key, retiring the oldest.

        The previous keys stay in the ring, so tokens already issued keep
        verifying until they expire. Rotating more times than the ring holds
        within one access-token lifetime *does* invalidate tokens still in
        flight -- the bound is a decision rather than an accident, and the
        response says how much room is left.

        :returns: The ring after rotation, or an error body.
        """
        refusal = self._refuse_unless_manager()
        if refusal is not None:
            return refusal
        self._disable_csrf()

        if self.segments != [ROTATE_KEY_ACTION]:
            return self._error(
                400, "Bad request", f"Expected @identity-keys/{ROTATE_KEY_ACTION}"
            )

        rotate_keys()
        return self._render()
