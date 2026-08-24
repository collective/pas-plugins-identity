"""Install handlers for the two demo profiles.

One module per profile, each holding only what cannot be stated as data:
:mod:`identitydemo.setuphandlers.idp` and :mod:`identitydemo.setuphandlers.rp`.
Registry settings live in each profile's ``registry`` XML and each site's
principals and content are a ``plone.exportimport`` payload, so what is left
in Python is the handful of URLs that come from the environment -- the two
demo deployments do not agree on them, and XML cannot read an environment
variable.

What stays here is the one thing both profiles share.
"""

from identitydemo import settings

import os


class DemoRefused(RuntimeError):
    """Raised when a demo profile is applied to a site that did not opt in."""


def guard() -> None:
    """Refuse to install unless the site explicitly asked for the demo.

    Called by the relying party's handler, which is the profile that puts a
    published client secret into a site. The identity provider's handler does
    not call it: its payload is a demo user whose password is in the same
    public repository either way, and refusing to create them protects
    nobody.

    The profiles are visible in any site that has this package on its path,
    so this is what stands between a curious click in ``portal_setup`` and a
    site holding a published credential.

    :raises DemoRefused: When :data:`identitydemo.settings.OPT_IN_ENV` is
        unset or empty. Deliberately an exception rather than a silent
        no-op: a profile that appears to install and then does nothing is
        worse to debug than one that says why it stopped.
    """
    if not os.environ.get(settings.OPT_IN_ENV):
        raise DemoRefused(
            f"identitydemo ships fixed, publicly known credentials and will "
            f"not install unless {settings.OPT_IN_ENV} is set. If this is a "
            f"real site, that is the correct outcome."
        )


__all__ = ["DemoRefused", "guard"]
