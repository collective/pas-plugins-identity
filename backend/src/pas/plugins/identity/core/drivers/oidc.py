"""The generic OpenID Connect driver."""

from pas.plugins.identity.core.drivers.base import BaseDriver


class GenericOIDCDriver(BaseDriver):
    """Any OIDC provider reachable through discovery."""

    driver_id = "oidc-generic"
    title = "OpenID Connect"
    default_scope = ("openid", "email", "profile")
    subject_keys = ("sub",)

    extra_fields = {  # noqa: RUF012
        "issuer": {
            "type": "string",
            "title": "Issuer URL",
            "required": True,
            "secret": False,
            "description": "Discovery is fetched from "
            "<issuer>/.well-known/openid-configuration.",
            # Ahead of the client credentials: everything else about this
            # provider is read from what the issuer discovers.
            "order": 10,
        },
        "picture_over_http": {
            "type": "bool",
            "title": "Allow the avatar to be fetched over plain HTTP",
            "required": False,
            "secret": False,
            "default": False,
            "description": (
                "Only for a provider on a network you control -- a demo or "
                "development stack with no certificate. Portrait syncing "
                "fetches a URL the provider supplies, and over plain HTTP "
                "that fetch can be aimed at an internal service and read "
                "back through the portrait. Leave this off for any provider "
                "on the public internet."
            ),
            "order": 70,
        },
    }
