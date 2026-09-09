"""The ``email`` scope: the address, and whether this site believes it.

``email_verified`` is the claim a relying party will auto-link accounts on, so
what it asserts matters more than what it costs to compute. It is this site's
own finding, never a provider's assertion passed through -- the core layer
refuses to trust a provider on that question, and emitting it on that basis
would export the problem rather than solve it.
"""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.pas import PLUGIN_ID as CORE_PLUGIN_ID
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from pas.plugins.identity.server.serializers.base import ScopeSerializer
from plone import api


def email_is_verified(userid: str, address: str) -> bool:
    """Whether this site holds the address as verified for that user.

    One question, asked of one place: is there an ``email`` identity for this
    address owned by this userid? That is what a magic link writes, and -- for
    a provider the operator marked ``trust_email_verification`` -- what a
    login through that provider writes too.

    So a relying party reading this claim is being told what this site
    believes, on the terms this site set. It is *not* a provider's assertion
    passed through: a provider nobody here trusts can say ``email_verified``
    all day and this stays false. See :doc:`/concepts/email-verification`.

    :param userid: The Plone userid.
    :param address: The address being asserted.
    :returns: Whether it is verified.
    """
    plugin = api.portal.get_tool("acl_users").get(CORE_PLUGIN_ID)
    if plugin is None:  # pragma: no cover - can't-happen: core is always installed
        return False
    return any(
        record.provider == EMAIL_PROVIDER and record.subject == address.strip().lower()
        for record in plugin.store.identities_for(userid)
    )


class EmailScope(ScopeSerializer):
    """Serialize the ``email`` scope."""

    claims = ("email", "email_verified")

    def __call__(self, user) -> JSONDict:
        """Return the address and its status.

        ``email_verified`` is sent only alongside an address. A statement
        about a claim that is not there is a claim about nothing, and OIDC
        readers differ on what to do with it -- so a user with no address
        gets neither, rather than a bare ``false`` a relying party might read
        as "this site checked and it failed".

        :param user: The Plone user the token acts for.
        :returns: Claim name to value.
        """
        address = user.getProperty("email", "")
        if not address:
            return {}
        return {
            "email": address,
            "email_verified": email_is_verified(user.getId(), address),
        }
