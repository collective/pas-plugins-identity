"""Recorded provider payloads for the driver tests.

These are trimmed captures of real responses, kept here so claim
normalization is tested without any provider in the loop.
"""

from pas.plugins.identity.core.drivers.base import BaseDriver
from pas.plugins.identity.core.drivers.emaillink import EmailDriver
from pas.plugins.identity.core.drivers.github import GitHubDriver
from pas.plugins.identity.core.drivers.google import GoogleDriver
from pas.plugins.identity.core.drivers.oidc import GenericOIDCDriver


#: Every driver this package ships.
ALL_DRIVERS: tuple[type[BaseDriver], ...] = (
    GitHubDriver,
    GoogleDriver,
    GenericOIDCDriver,
    EmailDriver,
)

#: The OAuth drivers, which are the ones holding a client secret.
OAUTH_DRIVERS: tuple[type[BaseDriver], ...] = (
    GitHubDriver,
    GoogleDriver,
    GenericOIDCDriver,
)

#: Keys the normalized schema always carries.
CLAIM_KEYS = {"fullname", "email", "email_verified", "picture_url", "username", "raw"}

#: ``GET /user`` on GitHub, with ``email_verified`` merged in by the flow
#: from ``GET /user/emails``.
GITHUB_USER = {
    "id": 1234567,
    "node_id": "MDQ6VXNlcjEyMzQ1Njc=",
    "login": "ericof",
    "name": "Érico Andrei",
    "email": "Erico@Plone.ORG",
    "email_verified": True,
    "avatar_url": "https://avatars.githubusercontent.com/u/1234567?v=4",
    "html_url": "https://github.com/ericof",
}

#: A GitHub account with no display name set.
GITHUB_USER_NO_NAME = {
    "id": 7654321,
    "login": "anon-dev",
    "name": None,
    "email": "anon@example.com",
    "email_verified": True,
    "avatar_url": "https://avatars.githubusercontent.com/u/7654321?v=4",
}

#: Google ``id_token`` claims for a Workspace account.
GOOGLE_USERINFO = {
    "sub": "104928374650192837465",
    "name": "Érico Andrei",
    "given_name": "Érico",
    "family_name": "Andrei",
    "email": "erico@plone.org",
    "email_verified": True,
    "picture": "https://lh3.googleusercontent.com/a/ACg8ocK",
    "hd": "plone.org",
}

#: Userinfo from a Dex instance, the provider the flow tests run against.
DEX_USERINFO = {
    "sub": "CgVlcmljbxIFbG9jYWw",
    "name": "Érico Andrei",
    "preferred_username": "ericof",
    "email": "erico@plone.org",
    "email_verified": True,
    "groups": ["plone-developers"],
}

#: A payload whose address the provider does NOT assert as verified: the
#: shape an attacker uses to claim somebody else's address.
UNVERIFIED_OIDC = {
    "sub": "attacker-subject",
    "name": "Not Érico",
    "email": "erico@plone.org",
    "email_verified": False,
}
