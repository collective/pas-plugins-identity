"""Recorded provider payloads for the driver tests.

These are trimmed captures of real responses, kept here so claim
normalization is tested without any provider in the loop (Gate 4).
"""

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

#: Userinfo from a Dex instance, the CI provider (C2).
DEX_USERINFO = {
    "sub": "CgVlcmljbxIFbG9jYWw",
    "name": "Érico Andrei",
    "preferred_username": "ericof",
    "email": "erico@plone.org",
    "email_verified": True,
    "groups": ["plone-developers"],
}

#: A payload whose address the provider does NOT assert as verified -- the
#: S2 attack shape.
UNVERIFIED_OIDC = {
    "sub": "attacker-subject",
    "name": "Not Érico",
    "email": "erico@plone.org",
    "email_verified": False,
}
