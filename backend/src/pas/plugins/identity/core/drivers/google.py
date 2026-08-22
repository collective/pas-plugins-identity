"""The Google driver."""

from pas.plugins.identity.core.drivers.base import BaseDriver


class GoogleDriver(BaseDriver):
    """Google OIDC."""

    driver_id = "google"
    title = "Google"
    default_scope = "openid email profile"
    subject_keys = ("sub",)

    extra_fields = {  # noqa: RUF012
        "hosted_domain": {
            "type": "string",
            "title": "Hosted domain",
            "required": False,
            "secret": False,
            "description": "When set, restrict logins to this Workspace domain.",
        },
        "allowed_groups": {
            "type": "list",
            "title": "Allowed groups",
            "required": False,
            "secret": False,
        },
    }
