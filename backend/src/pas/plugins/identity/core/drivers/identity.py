"""The driver for a Plone site running this same package as an IdP."""

from pas.plugins.identity.core.drivers.oidc import GenericOIDCDriver


class PloneIdentityDriver(GenericOIDCDriver):
    """Another Plone site, signing people in through its ``[server]`` layer.

    Discovery, the flow and the claim normalization are the generic OIDC
    ones -- an authorization server built on this package is a conforming
    OIDC provider and gets no special path through the code. What this adds
    is the configuration a *peer* can be known in advance to want, which the
    generic driver has no business guessing about an arbitrary provider.
    """

    driver_id = "plone-identity"
    title = "Plone site"

    #: ``address`` on top of the generic three.
    #:
    #: The server layer publishes an address claim -- the member's
    #: ``location``, wrapped as the ``formatted`` member OIDC defines -- and
    #: it is released by a scope of its own. Asking for it here is what makes
    #: the mapping below resolve to anything.
    default_scope = ("openid", "email", "profile", "address")

    #: The remote userid, rather than a fresh random one.
    #:
    #: A peer running this package mints an opaque, stable userid and puts it
    #: in ``sub``, so mirroring it means one person keeps one id across the
    #: federation -- which is the point of federating rather than each site
    #: inventing its own name for the same human. A userid already taken
    #: locally is still never handed out; that collision gets a suffix like
    #: any other.
    default_userid_source = "subject"

    #: Everything the peer's ``SCOPE_CLAIMS`` actually releases.
    #:
    #: Written against the normalized names where normalization produces one
    #: (``name`` arrives as ``fullname``, ``picture`` as ``picture_url``) and
    #: against the raw claim where it does not. ``address.formatted`` is the
    #: dotted path this package's property map exists for: the claim is an
    #: object and the formatted member is the readable line.
    #:
    #: There is no biography claim and no group claim to map, so nothing
    #: writes to ``description``.
    default_propertymap = {  # noqa: RUF012
        "email": "email",
        "fullname": "fullname",
        "website": "home_page",
        "address.formatted": "location",
        "picture_url": "portrait",
    }

    extra_fields = {  # noqa: RUF012
        "issuer": {
            "type": "string",
            "title": "Issuer URL",
            "required": True,
            "secret": False,
            "description": (
                "The other site's URL, as it serves "
                "/.well-known/openid-configuration -- for a Plone site that "
                "is the site root, with no path segment after it."
            ),
            "order": 10,
        },
    }
