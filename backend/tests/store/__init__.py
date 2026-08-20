"""Shared values for the identity store tests."""

from pas.plugins.identity.core.interfaces import Claims


#: A userid as minted by the plugin (D10: ``uuid4().hex``).
USERID = "0f2b1c4d5e6f47a8b9c0d1e2f3a4b5c6"
OTHER_USERID = "a1b2c3d4e5f647a8b9c0d1e2f3a4b5c6"

#: A GitHub-shaped identity.
GITHUB = ("github", "1234567")

#: An email identity; the store lowercases these subjects.
EMAIL_MIXED_CASE = ("email", "Erico@Plone.ORG")
EMAIL_LOWER = ("email", "erico@plone.org")

CLAIMS: Claims = {
    "fullname": "Érico Andrei",
    "email": "erico@plone.org",
    "email_verified": True,
    "picture_url": "https://example.com/avatar.png",
    "username": "ericof",
    "raw": {"id": 1234567, "login": "ericof"},
}
