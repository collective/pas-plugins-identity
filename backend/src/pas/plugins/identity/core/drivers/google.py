"""The Google driver."""

from pas.plugins.identity.core.drivers.base import BaseDriver


class GoogleDriver(BaseDriver):
    """Google OIDC."""

    driver_id = "google"
    title = "Google"
    default_scope = ("openid", "email", "profile")
    subject_keys = ("sub",)
