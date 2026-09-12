"""The driver for a Keycloak realm."""

from pas.plugins.identity.core.drivers.oidc import GenericOIDCDriver
from pas.plugins.identity.core.drivers.settings import IKeycloakSettings


class KeycloakDriver(GenericOIDCDriver):
    """A Keycloak realm, signing people in as any OIDC provider does.

    Discovery, the flow and the claim normalization are the generic OIDC
    ones. What this adds is what a Keycloak realm can be known in advance to
    want, which the generic driver has no business assuming about an
    arbitrary provider: how its issuer is spelled, which of its claims makes a
    readable userid, and whether its ``email_verified`` counts.

    The scope, the property map and the group claim stay the generic ones,
    on purpose. Under ``openid email profile`` a default realm releases
    ``name``, ``given_name``, ``family_name``, ``preferred_username``,
    ``email`` and ``email_verified``, and nothing else: no ``website``, no
    ``picture`` and no ``address``, because its user profile has no attribute
    to fill them from. A map row naming any of them would resolve to nothing.
    Groups arrive as ``groups`` too, but only once somebody adds a Group
    Membership mapper to the client, which is a step on the realm side that
    no default here can take.
    """

    driver_id = "keycloak"
    settings_schema = IKeycloakSettings
    title = "Keycloak"
    icon_resource = "pas.plugins.identity.core.drivers:icons/keycloak.svg"

    #: The realm's username, rather than a fresh random one.
    #:
    #: Every Keycloak user has one, and a realm releases it as
    #: ``preferred_username`` under the ``profile`` scope this driver already
    #: asks for. ``sub`` is a UUID, stable and unreadable. The identity is
    #: still recorded against ``sub``, so a username the realm renames later
    #: does not lose the link; the local userid keeps the name it was minted
    #: with, and a name already taken locally gets a numeric suffix instead.
    default_userid_source = "username"

    #: A realm's word on an address counts here by default.
    #:
    #: A Keycloak realm is almost always run by the organization running the
    #: site, so its verification is that organization's own, and it sends
    #: ``email_verified`` as a real boolean. Only the default: a realm that
    #: lets people sign up without verifying their address, or whose
    #: administrators mark addresses verified by hand, is a reason for the
    #: operator to switch it off.
    default_trust_email_verification = True
