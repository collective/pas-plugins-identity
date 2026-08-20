"""Shared values for the PAS integration tests."""

from pas.plugins.identity.core.interfaces import Claims


#: A Dex-shaped identity, as Gate 1's functional flow produces.
DEX_IDENTITY = ("oidc-generic", "CgVlcmljbxIFbG9jYWw")

#: A second provider for the same human -- the linking scenario (Gate 2).
GITHUB_IDENTITY = ("github", "1234567")

CLAIMS: Claims = {
    "fullname": "Érico Andrei",
    "email": "erico@plone.org",
    "email_verified": True,
    "picture_url": "",
    "username": "ericof",
    "raw": {},
}

OTHER_CLAIMS: Claims = {
    "fullname": "Someone Else",
    "email": "other@example.com",
    "email_verified": True,
    "picture_url": "",
    "username": "other",
    "raw": {},
}
