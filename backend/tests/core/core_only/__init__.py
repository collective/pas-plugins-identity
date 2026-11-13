"""A site with the ``core`` profile and nothing else.

Authentication without users as content: no types, no catalog, no Profile
plugin, and no :class:`~pas.plugins.identity.core.interfaces.IUsersAsContent`
marker on the site. Users live where Plone keeps them without this package,
in ``source_users`` and ``mutable_properties``, and the identity plugin writes
them there.

The modules here share the site fixture in ``conftest.py`` and the sign-in
helper below.
"""

from pas.plugins.identity import PACKAGE_NAME
from pas.plugins.identity.core.pas import EXTRACTOR


#: The profile these sites are built from.
CORE_PROFILE = f"{PACKAGE_NAME}:core"

#: The provider every sign-in here comes through.
PROVIDER = "oidc-generic"

#: Well-formed claims, as a driver normalizes them.
CLAIMS = {
    "fullname": "Érico Andrei",
    "email": "erico@plone.org",
    "email_verified": True,
    "emails": (
        {"address": "erico@plone.org", "verified": True, "primary": True},
        {"address": "ericof@example.com", "verified": True, "primary": False},
    ),
    "picture_url": "",
    "username": "ericof",
    "raw": {"location": "Brasília", "groups": ["staff"]},
}


def sign_in(plugin, subject: str = "dex-subject-1", claims=None) -> str:
    """Run a federated login and return the userid it resolved to.

    :param plugin: The identity plugin.
    :param subject: The provider-side subject.
    :param claims: Claims to authenticate with. ``None`` means :data:`CLAIMS`.
    :returns: The userid.
    :raises AssertionError: When the login was declined.
    """
    result = plugin.authenticateCredentials({
        "extractor": EXTRACTOR,
        "provider": PROVIDER,
        "subject": subject,
        "claims": CLAIMS if claims is None else claims,
    })
    assert result is not None, "the login was declined"
    userid, _ = result
    return userid
