"""The generic OpenID Connect driver."""

from pas.plugins.identity.core.drivers.base import BaseDriver


class GenericOIDCDriver(BaseDriver):
    """Any OIDC provider reachable through discovery."""

    driver_id = "oidc-generic"
    title = "OpenID Connect"
    default_scope = "openid email profile"
    subject_keys = ("sub",)

    extra_fields = {  # noqa: RUF012
        "issuer": {
            "type": "string",
            "title": "Issuer URL",
            "required": True,
            "secret": False,
            "description": "Discovery is fetched from "
            "<issuer>/.well-known/openid-configuration.",
        },
    }
