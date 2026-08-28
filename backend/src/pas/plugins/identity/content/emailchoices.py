"""The addresses a user's providers offered and nobody has picked between.

A provider is not obliged to send one address. GitHub returns every address on
the account, and choosing among them is not this package's to do: it decides
which identity the person is here as, and -- where the operator enabled
auto-linking -- which existing account a verified-email link would attach to.
So the driver carries the list instead of guessing, the profile is minted
without an address and is therefore ``incomplete``, and the required-
information gate holds the user on the form that asks.

This module is what that form is built from, and it is one module because two
endpoints answer with it: ``@my-profile`` names the addresses so a frontend
can explain itself, and ``@types`` puts them in the ``email`` field's schema so
the form renders a choice rather than an empty box. Two gatherings would
eventually disagree about which addresses exist, and the disagreement would
look like a form offering something the API says is not on offer.
"""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.pas import PLUGIN_ID as CORE_PLUGIN_ID
from plone import api


def offered_addresses(userid: str) -> list[JSONDict]:
    """Return the addresses this user's identities offer, unchosen.

    Gathered across every linked identity rather than one, because a person
    with two providers has been offered addresses by both and the form asks
    one question. Deduplicated on the address itself, keeping the first
    provider that offered it: the same address from two providers is one
    answer, and which of them mentioned it first is not something to make the
    user resolve.

    The provider id is carried so a form can say where an address came from.
    ``verified`` is the *provider's* claim and is carried for the same reason
    -- to be shown, never to be acted on. Only an address this site confirmed
    with a magic link counts as verified anywhere in this package.

    :param userid: The userid to gather for. Callers resolve this from the
        authenticated user; nothing here checks who is asking.
    :returns: The addresses, empty when nothing offers any.
    """
    plugin = api.portal.get_tool("acl_users").get(CORE_PLUGIN_ID)
    if plugin is None:  # pragma: no cover - can't-happen: core is always installed
        return []
    choices: dict[str, JSONDict] = {}
    for record in plugin.store.identities_for(userid):
        for offered in record.claims.get("email_choices") or ():
            address = str(offered.get("address", "")).strip().lower()
            if not address or address in choices:
                continue
            choices[address] = {
                "address": address,
                "verified": offered.get("verified") is True,
                "primary": offered.get("primary") is True,
                "provider": record.provider,
            }
    return list(choices.values())


__all__ = ["offered_addresses"]
