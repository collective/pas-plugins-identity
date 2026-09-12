"""Recorded provider payloads for the driver tests.

These are trimmed captures of real responses, kept here so claim
normalization is tested without any provider in the loop.
"""

from pas.plugins.identity.core.drivers.base import BaseDriver
from pas.plugins.identity.core.drivers.emaillink import EmailDriver
from pas.plugins.identity.core.drivers.github import GitHubDriver
from pas.plugins.identity.core.drivers.google import GoogleDriver
from pas.plugins.identity.core.drivers.identity import PloneIdentityDriver
from pas.plugins.identity.core.drivers.keycloak import KeycloakDriver
from pas.plugins.identity.core.drivers.oidc import GenericOIDCDriver


#: Every driver this package ships.
ALL_DRIVERS: tuple[type[BaseDriver], ...] = (
    GitHubDriver,
    GoogleDriver,
    GenericOIDCDriver,
    PloneIdentityDriver,
    KeycloakDriver,
    EmailDriver,
)

#: The OAuth drivers, which are the ones holding a client secret.
OAUTH_DRIVERS: tuple[type[BaseDriver], ...] = (
    GitHubDriver,
    GoogleDriver,
    GenericOIDCDriver,
    PloneIdentityDriver,
    KeycloakDriver,
)

#: Keys the normalized schema always carries.
CLAIM_KEYS = {
    "fullname",
    "email",
    "email_verified",
    "emails",
    "picture_url",
    "username",
    "raw",
}

#: ``GET /user`` on GitHub.
#:
#: ``email_verified`` is **not** part of that payload -- ``/user`` has no such
#: key. It is here so the normalizer is exercised against a payload that has
#: one, which is the shape every OIDC provider sends, and which is also the
#: shape the driver builds once it has merged ``GET /user/emails``. See
#: :class:`GitHubDriver` for where the real payload's address comes from.
GITHUB_USER = {
    "id": 1234567,
    "node_id": "MDQ6VXNlcjEyMzQ1Njc=",
    "login": "ericof",
    "name": "Érico Andrei",
    "email": "Erico@Plone.ORG",
    "email_verified": True,
    "avatar_url": "https://avatars.githubusercontent.com/u/1234567?v=4",
    "html_url": "https://github.com/ericof",
    # The three GitHub fills in that a Profile has somewhere to put, and that
    # `GitHubDriver.default_propertymap` therefore maps. Absent from this
    # fixture until the map existed, which meant the map could have named
    # anything at all and the tests would have agreed.
    "bio": "Plone developer.",
    "blog": "https://plone.org",
    "location": "Berlin, Germany",
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

#: Userinfo from a Plone site running this package's ``[server]`` layer.
#: ``address`` is an object whose ``formatted`` member is the readable line,
#: which is what the dotted path in the driver's mapping reaches.
PLONE_IDENTITY_USERINFO = {
    "sub": "8f14e45fceea167a5a36dedd4bea2543",
    "name": "Érico Andrei",
    "preferred_username": "ericof",
    "website": "https://plone.org",
    "picture": "http://id.localhost/portal_memberdata/portraits/ericof",
    "email": "erico@plone.org",
    "email_verified": True,
    "address": {"formatted": "São Paulo, Brazil"},
}

#: Userinfo from Keycloak 26.0, read from the realm the Docker tests import
#: (``tests/_resources/keycloak/realm.json``) with the scope
#: ``openid email profile``. Everything a default realm sends is here: it has
#: no ``website``, ``picture`` or ``address`` to send, and no ``groups``
#: until a Group Membership mapper exists.
KEYCLOAK_USERINFO = {
    "sub": "d5b148c6-e6a9-4479-8ea0-e3b28ca71ab9",
    "email_verified": True,
    "name": "Elena Example",
    "preferred_username": "elena",
    "given_name": "Elena",
    "family_name": "Example",
    "email": "elena@example.org",
}
