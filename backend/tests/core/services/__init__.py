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
