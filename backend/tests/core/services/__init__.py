"""Shared values for the login-flow service tests."""

#: Where the Volto callback route lives. Deliberately a different origin from
#: the backend: that is the split-deployment shape, and the redirect URI must
#: come from configuration rather than from the portal URL.
CALLBACK_URL = "https://frontend.example/login-identity"

#: Discovery metadata as resolved for the Dex fixture, trimmed to what the
#: flow layer reads.
DEX_METADATA = {
    "issuer": "http://dex:5556/dex",
    "authorization_endpoint": "http://dex:5556/dex/auth",
    "token_endpoint": "http://dex:5556/dex/token",
    "userinfo_endpoint": "http://dex:5556/dex/userinfo",
}

#: A provider record as the control panel stores it.
DEX_PROVIDER = {
    "id": "dex",
    "driver": "oidc-generic",
    "title": "Dex",
    "enabled": True,
    "config": {
        "issuer": "http://dex:5556/dex",
        "client_id": "plone",
        "client_secret": "plone-secret",
        "scope": ("openid", "email", "profile"),
    },
}

#: A second, disabled provider.
DISABLED_PROVIDER = {
    "id": "github",
    "driver": "github",
    "title": "GitHub",
    "enabled": False,
    "config": {"client_id": "Iv1.abc", "client_secret": "gho_secret"},
}

#: What Dex's userinfo endpoint answers for our test user.
USERINFO = {
    "sub": "CgVlcmljbxIFbG9jYWw",
    "name": "Érico Andrei",
    "preferred_username": "ericof",
    "email": "erico@plone.org",
    "email_verified": True,
}


#: The address the magic-link tests prove control of.
ADDRESS = "erico@plone.org"

#: The email provider record. Shared by the login tests and the linking
#: tests, which mail the same kind of link for two different purposes: a
#: second copy would let one of them keep passing against a provider the
#: other no longer configures.
EMAIL_PROVIDER_RECORD = {
    "id": "email",
    "driver": "email",
    "title": "Email",
    "enabled": True,
    "config": {"token_ttl": 900, "rate_limit_per_hour": 5},
}


def token_from(messages) -> str:
    """Pull the magic-link token out of a captured message.

    :param messages: Parsed messages.
    :returns: The token.
    """
    from urllib.parse import parse_qs
    from urllib.parse import urlparse

    text = messages[-1].get_content()
    url = next(word for word in text.split() if "magic_link=" in word)
    return parse_qs(urlparse(url).query)["magic_link"][0]
