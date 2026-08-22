"""Shared values for the audit log tests."""

from pas.plugins.identity.core.interfaces import Claims


#: Normalized claims, as the events carry them.
CLAIMS: Claims = {
    "fullname": "Érico Andrei",
    "email": "erico@plone.org",
    "email_verified": True,
    "picture_url": "",
    "username": "ericof",
    "raw": {},
}
