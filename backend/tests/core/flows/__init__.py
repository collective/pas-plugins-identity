"""Shared values for the authorization-flow tests."""

#: Where the test portal lives.
PORTAL_URL = "http://localhost:8080/plone"

#: Callback URL registered with the provider.
REDIRECT_URI = f"{PORTAL_URL}/@identity-callback"

#: Discovery metadata as Dex publishes it, trimmed to what the flows use.
DEX_METADATA = {
    "issuer": "http://dex:5556/dex",
    "authorization_endpoint": "http://dex:5556/dex/auth",
    "token_endpoint": "http://dex:5556/dex/token",
    "userinfo_endpoint": "http://dex:5556/dex/userinfo",
    "client_id": "plone",
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
