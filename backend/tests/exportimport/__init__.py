"""Shared values for the export/import tests."""

#: One provider, one subject, one human -- the smallest thing worth moving.
PROVIDER = "oidc-generic"
SUBJECT = "CgVlcmljbxIFbG9jYWw"
USERID = "8f2c1e5b9a7d4c6e8f0a1b2c3d4e5f60"
LOGIN = "ericof"
ADDRESS = "erico@plone.org"

CLAIMS = {
    "fullname": "Érico Andrei",
    "email": ADDRESS,
    "email_verified": True,
    "emails": [{"address": ADDRESS, "verified": True}],
    "username": LOGIN,
    "raw": {},
}
