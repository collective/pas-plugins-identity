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

    #: The peer's login name, rather than a fresh random one.
    #:
    #: A peer running this package releases ``preferred_username`` under the
    #: ``profile`` scope this driver already asks for, and that is the name
    #: the person is known by on the other site -- so mirroring it means one
    #: person is recognisable by the same name across the federation rather
    #: than each site inventing its own. ``sub`` would be stable where a
    #: username is not, but it is only readable when the peer happened to
    #: mint readable userids of its own; the collision case is identical
    #: either way, since a userid already taken locally is never handed out
    #: and gets a numeric suffix instead.
    default_userid_source = "username"

    #: Everything the peer's ``SCOPE_CLAIMS`` actually releases.
    #:
    #: Written against the normalized names where normalization produces one
    #: (``name`` arrives as ``fullname``, ``picture`` as ``picture_url``) and
    #: against the raw claim where it does not. ``address.formatted`` is the
    #: dotted path this package's property map exists for: the claim is an
    #: object and the formatted member is the readable line.
    #:
    #: ``description`` is in there because a peer publishes it: OIDC has no
    #: registered claim for a biography, and the server layer releases one
    #: under ``profile`` regardless. It resolves off the raw payload, since
    #: normalization has no name of its own for it.
    default_propertymap = {  # noqa: RUF012
        "email": "email",
        "fullname": "fullname",
        "website": "home_page",
        "description": "description",
        "address.formatted": "location",
        "picture_url": "portrait",
    }

    #: A peer releases ``groups`` under the ``profile`` scope this driver
    #: already asks for, so the claim arrives without extra configuration.
    #: What it *grants* still does not: the map below is empty, and stays
    #: empty until an operator says which of the peer's groups mean something
    #: here. Two Plone sites in a federation do not have the same groups just
    #: because they run the same package.
    default_groupmap = {}  # noqa: RUF012

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
