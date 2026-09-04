"""Repairing a provider that sends its verification flags as text.

``email_verified`` is a boolean in OpenID Connect, and
:meth:`~pas.plugins.identity.core.drivers.base.BaseDriver._email_verified`
accepts nothing else: only a literal ``True`` counts, because a forged or
sloppy payload must never satisfy the link-by-email gate. That is the right
default and it does not change.

Some providers send the string ``"true"`` instead. Oracle Access Manager does,
and so do some Keycloak configurations. Against one of those, every user is
silently unverified here: automatic linking by email never fires, an address
the provider genuinely checked is recorded as unchecked, and nothing says why.
The behaviour is defensible; being undiagnosable is not.

So the repair happens **before** the claims are normalized, on a copy, and
only for a provider whose operator has said this is what it does. Two
properties are worth stating, because both are the point:

* **The strict check is untouched.** By the time anything reads
  ``email_verified`` it is a real boolean, and every gate downstream still
  insists on ``is True``. There is no second, laxer path through the
  verification logic -- there is one path, and a malformed payload is made
  well-formed before it reaches it.
* **It is per-provider, never site-wide.** A site-wide switch would weaken the
  gate for every provider that never needed it, including the ones whose
  payloads are correct and whose word is trusted.

Only the flags OpenID Connect defines as booleans are touched, and only when
the value is exactly one of the two strings a provider means them as. Anything
else is left alone to be refused by the strict check, which is what should
happen to a value nobody can read with confidence.
"""

from pas.plugins.identity.core.interfaces import JSONDict


#: The claims OpenID Connect defines as booleans, and which providers get
#: wrong. ``phone_number_verified`` is here because a provider that sends one
#: as a string sends both that way -- it is a fact about the provider's
#: serializer, not about the claim.
BOOLEAN_CLAIMS = ("email_verified", "phone_number_verified")

#: What a provider means by each string. Compared case-insensitively after
#: stripping, because a serializer that gets the type wrong is not one to
#: trust about whitespace either.
#:
#: Deliberately short. ``"1"``, ``"yes"`` and ``"on"`` are not here: each is a
#: guess about what somebody meant, and guessing wrong grants a verified
#: address. A provider that sends one of those is a bug report, not a case to
#: silently accommodate.
STRINGS = {"true": True, "false": False}


def repaired_flags(payload: JSONDict) -> JSONDict:
    """Return the payload with string verification flags read as booleans.

    :param payload: The provider's payload, which is not modified.
    :returns: A shallow copy with any string boolean in
        :data:`BOOLEAN_CLAIMS` replaced by the boolean it spells. A payload
        with none is copied and otherwise unchanged, so the caller never has
        to ask whether anything happened.
    """
    repaired = dict(payload)
    for claim in BOOLEAN_CLAIMS:
        value = repaired.get(claim)
        if isinstance(value, str) and value.strip().lower() in STRINGS:
            repaired[claim] = STRINGS[value.strip().lower()]
    return repaired
