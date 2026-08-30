"""The generic OpenID Connect driver."""

from pas.plugins.identity.core.drivers.base import BaseDriver
from pas.plugins.identity.core.drivers.settings import IOIDCSettings
from pas.plugins.identity.core.utils.groupmap import DEFAULT_GROUP_CLAIM


class GenericOIDCDriver(BaseDriver):
    """Any OIDC provider reachable through discovery."""

    driver_id = "oidc-generic"
    title = "OpenID Connect"
    settings_schema = IOIDCSettings
    default_scope = ("openid", "email", "profile")
    subject_keys = ("sub",)

    #: The de-facto name. Not registered by OIDC, but what Keycloak, Okta and
    #: Entra all emit, so it is the right thing to try before an operator
    #: reaches for the dotted path.
    default_group_claim = DEFAULT_GROUP_CLAIM
