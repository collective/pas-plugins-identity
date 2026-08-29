"""When a provider's word about an address counts as proof here.

This package used to answer that question with "never". Only a magic link sent
from this site and followed from it made an address verified, and a provider
asserting ``email_verified`` was carried, shown, and acted on nowhere. The
reasoning is in :doc:`/concepts/email-verification` and it has not changed:
somebody who can register at a permissive provider with an address that is
yours must not thereby be you here.

What changed is who decides (Érico, 2026-08-29). Google and GitHub do verify
an address before they call it verified, and telling somebody who signed in
with Google to go and prove the address Google just proved is a worse flow for
no security. So the answer is now the operator's, per provider, and its name
is ``trust_email_verification``:

* **On** -- an address this provider says it verified is recorded here as
  verified, which means an ``email`` identity in the store, which is what a
  magic link creates. Not a second flag beside it: one notion of verified, so
  there is nothing for the two to disagree about.
* **Off** -- the claim is still carried and still shown. It proves nothing.

Defaults come from the driver, so a site gets the sensible answer without
configuring anything and can overrule it either way.

**What being verified buys, and therefore what this switch is worth.** A
verified address is what ``auto_link_by_email`` attaches a *new* provider
account to, and it is what this site exports as ``email_verified`` when it acts
as an authorization server. Switching this on for a provider that does not
really check is the account-takeover in that document, so the switch is off
unless a driver says otherwise and the field says what it costs.

**The email provider is not routed through here.** Its verification *is* the
identity -- redeeming the link writes it -- so there is nothing left for this
module to record, and calling it anyway would be a second write of the row that
had just been written.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.interfaces import IdentityCollision
from pas.plugins.identity.core.pas import PLUGIN_ID as CORE_PLUGIN_ID
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from pas.plugins.identity.core.utils.emails import normalize
from plone import api


def trusts_verification(provider_id: str) -> bool:
    """Report whether this site takes a provider's word about an address.

    :param provider_id: The provider the claims came from.
    :returns: The provider's ``trust_email_verification`` setting, and
        ``False`` for a provider this site no longer has -- an identity can
        outlive the configuration that created it, and the safe answer for a
        provider nobody can inspect is the one that proves nothing.
    """
    from pas.plugins.identity.core.controlpanel import get_provider

    config = get_provider(provider_id)
    if config is None:
        return False
    return bool(config.config.get("trust_email_verification"))


def verified_by_provider(claims: Claims) -> tuple[str, ...]:
    """Return the addresses a provider says it verified, in its own order.

    Read off ``emails``, which every driver fills -- with one entry for the
    single address most providers send. ``email_verified`` on its own is not
    consulted: it describes ``email``, which is the first entry of that list.

    Only a literal ``True`` counts, exactly as everywhere else this package
    reads the flag: a string ``"true"`` and a ``1`` are both truthy and neither
    is a provider saying yes.

    :param claims: Normalized claims.
    :returns: The addresses, normalized and de-duplicated.
    """
    found: list[str] = []
    for reported in claims.get("emails") or ():
        if reported.get("verified") is not True:
            continue
        address = normalize(reported.get("address"))
        if address and address not in found:
            found.append(address)
    return tuple(found)


def record_verified_addresses(
    userid: str, provider_id: str, claims: Claims
) -> tuple[str, ...]:
    """Record a trusted provider's verified addresses as verified here.

    Written through the plugin's ``link`` rather than straight into the store,
    so that everything a magic link causes happens here too: the audit entry,
    and the reindex that keeps the Profile's derived ``email`` true in the
    catalog metadata every read of it comes from.

    An address already held for this user is left alone; an address held for
    *somebody else* is refused and logged. Two people cannot both have proved
    the same mailbox, and quietly moving the identity would be one person
    taking the other's account -- which is the whole thing being guarded
    against.

    :param userid: The user who just authenticated or linked.
    :param provider_id: The provider the claims came from.
    :param claims: Normalized claims.
    :returns: The addresses newly recorded as verified, empty when there is
        nothing to record -- which is the ordinary case.
    """
    if provider_id == EMAIL_PROVIDER:
        return ()
    addresses = verified_by_provider(claims)
    if not addresses or not trusts_verification(provider_id):
        return ()

    plugin = api.portal.get_tool("acl_users").get(CORE_PLUGIN_ID)
    if plugin is None:  # pragma: no cover - can't-happen: core is always installed
        return ()

    recorded = []
    for address in addresses:
        owner = plugin.store.userid_for(EMAIL_PROVIDER, address)
        if owner == userid:
            continue
        if owner is not None:
            logger.warning(
                "Not recording %r as verified for %s on %s's word: it is "
                "already verified for %s",
                address,
                userid,
                provider_id,
                owner,
            )
            continue
        try:
            plugin.link(
                userid,
                EMAIL_PROVIDER,
                address,
                {"email": address, "email_verified": True, "raw": {}},
            )
        except IdentityCollision:  # pragma: no cover - the lookup just ruled it out
            continue
        logger.info(
            "Recorded %r as verified for %s on %s's word", address, userid, provider_id
        )
        recorded.append(address)
    return tuple(recorded)


__all__ = [
    "record_verified_addresses",
    "trusts_verification",
    "verified_by_provider",
]
