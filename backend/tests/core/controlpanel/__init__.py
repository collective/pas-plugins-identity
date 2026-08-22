"""Shared values for the provider configuration tests."""

GITHUB_PROVIDER = {
    "id": "github",
    "driver": "github",
    "title": "GitHub",
    "enabled": True,
    "config": {
        "client_id": "Iv1.abc123",
        "client_secret": "gho_supersecret",
        "scope": "read:user user:email",
    },
}

DISABLED_PROVIDER = {
    "id": "google",
    "driver": "google",
    "title": "Google",
    "enabled": False,
    "config": {"client_id": "g-abc", "client_secret": "g-secret"},
}

#: A provider whose driver was removed from the site.
ORPHANED_PROVIDER = {
    "id": "legacy",
    "driver": "no-such-driver",
    "title": "Legacy",
    "enabled": True,
    "config": {"client_id": "legacy-id", "client_secret": "legacy-secret"},
}
