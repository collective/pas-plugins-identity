"""The ``profile`` scope: who this is, as a site would display them.

Two of the claims here are not registered OIDC claims. ``description`` --
Plone's free-text biography -- and ``groups`` both ride on ``profile`` rather
than on a private scope, because both are read by name elsewhere: ``groups``
is what Keycloak, Okta and Entra all call it, and a namespaced claim only this
server's own peers would understand buys nothing but a second thing to
configure. A relying party that does not know a claim ignores it.

``groups`` riding on ``profile`` is a deliberate trade and worth naming.
``profile`` is granted for display, and group membership is authorization
data, so every relying party asking for a display scope receives it whether it
maps groups or not. What the server controls is the *content*: see
:data:`UNRELEASED_GROUPS`.
"""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.server.serializers.base import ScopeSerializer
from plone import api
from urllib.parse import quote


#: Group ids this server never puts in a ``groups`` claim.
#:
#: ``AuthenticatedUsers`` is PAS's virtual group: every principal with a
#: session is in it, so it says nothing about anybody. Releasing it would
#: also be actively harmful at the far end, where a relying party that
#: mapped it would hand its local counterpart to every federated user.
UNRELEASED_GROUPS = frozenset({"AuthenticatedUsers"})


def released_groups(user) -> list[str]:
    """Return the group ids to release for a user.

    ``PropertiedUser.getGroups`` is what PAS resolved for this principal, so
    it already includes groups reached through another plugin and through
    nesting -- which is the answer a relying party wants, rather than the
    memberships one plugin happens to hold.

    Sorted, because a claim that reorders between two logins looks like a
    change to anything diffing tokens.

    :param user: The Plone user the token acts for.
    :returns: Group ids, sorted, minus :data:`UNRELEASED_GROUPS`.
    """
    return sorted(set(user.getGroups()) - UNRELEASED_GROUPS)


def portrait_url(userid: str) -> str:
    """Return the public URL of a user's portrait, or nothing.

    Only when a portrait is actually stored. Plone's
    ``getPersonalPortrait`` falls back to a default image, and publishing a
    ``picture`` claim that every user shares would tell a relying party that
    everybody uploaded the same photograph.

    Which store holds it is not this layer's business, so the question goes
    to :func:`pas.plugins.identity.core.portraits.has_picture`, which asks
    both. Asking ``portal_memberdata`` directly was correct only while every
    avatar landed there; once a site's Profiles started winning, this
    returned an empty string for users who plainly had a picture and the
    claim was dropped without a word.

    The URL is always ``@portrait``, whichever store answers. It is a public
    endpoint by design -- a relying party fetches it server to server with no
    credentials -- and it does not disclose where a Profile lives.

    Under ``++api++``, which is not decoration. ``@portrait`` is a
    ``plone.restapi`` service, and ``plone.rest`` only takes over traversal
    for a request that asks for JSON: published bare, the URL answered 404
    for every client that did not claim to want a JSON document -- our own
    fetcher, any relying party that is not a Plone site, and a browser
    rendering the claim in an ``<img>``. The namespace is what makes the URL
    resolve for all of them, and it is already public on any site that serves
    a REST API at all.

    Built from the configured issuer rather than from the portal URL, for the
    reason the issuer is configured at all: the portal URL is whatever the
    request came in on, and this URL is handed to another site to fetch.

    :param userid: Canonical Plone userid.
    :returns: An absolute URL, or an empty string.
    """
    from pas.plugins.identity.core.portraits import has_picture
    from pas.plugins.identity.server.grants.tokens import ISSUER_RECORD

    if not has_picture(userid):
        return ""

    issuer = (api.portal.get_registry_record(ISSUER_RECORD, default="") or "").strip()
    if not issuer:
        return ""
    return f"{issuer.rstrip('/')}/++api++/@portrait/{quote(userid)}"


class ProfileScope(ScopeSerializer):
    """Serialize the ``profile`` scope."""

    claims = (
        "name",
        "preferred_username",
        "website",
        "picture",
        "description",
        "groups",
    )

    def __call__(self, user) -> JSONDict:
        """Return the display claims for one user.

        :param user: The Plone user the token acts for.
        :returns: Claim name to value. Empty values are left in and dropped
            by ``claims_for``, which applies that rule to every serializer.
        """
        return {
            "name": user.getProperty("fullname", ""),
            "preferred_username": user.getUserName(),
            "website": user.getProperty("home_page", ""),
            "picture": portrait_url(user.getId()),
            "description": user.getProperty("description", ""),
            "groups": released_groups(user),
        }
