"""The ``address`` scope: where this person says they are."""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.server.serializers.base import ScopeSerializer


class AddressScope(ScopeSerializer):
    """Serialize the ``address`` scope."""

    claims = ("address",)

    def __call__(self, user) -> JSONDict:
        """Return the address claim for one user.

        Plone's ``location`` is one free-text line, which is exactly what the
        ``formatted`` member of the OIDC address claim is for. Splitting it
        into street, locality and postal code would be guessing.

        :param user: The Plone user the token acts for.
        :returns: Claim name to value.
        """
        location = user.getProperty("location", "")
        if not location:
            return {}
        return {"address": {"formatted": location}}
