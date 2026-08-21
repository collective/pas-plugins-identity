"""Properties and enumeration served from catalog brains (§4.7, C6).

This is the claim the whole ``[profile]`` design rests on: a site can back its
users with content objects and still answer "what is this user's full name"
and "who matches 'liddell'" without loading a single Profile from the ZODB.
Every read here goes through catalog metadata, and Gate 6b's tests assert the
object-load count is zero while they run.

Why it matters: enumeration is called on paths where waking content is
unacceptable -- rendering a Sharing tab, resolving a local role, listing group
members. Membrane's userproperties plugin is the cautionary example (C9), and
avoiding that shape is the reason this package does not depend on it.

**Ordering.** Plone resolves a member property by walking the ordered property
sheets and taking the first that *has* the property, so this plugin has to sit
above ``mutable_properties`` for a Profile to be authoritative. The install
handler moves it to the top of ``IPropertiesPlugin``; nothing else enforces it,
which is why there is a test that would fail if the move were dropped.

**Duplicates.** ``PluggableAuthService.searchUsers`` concatenates what every
enumerator returns and does not deduplicate. Core leaves ``source_users``
active and enumerating, so the same human is returned by both plugins. What
makes them collapse back into one row is that both return the *same canonical
userid* as ``id``: the Sharing tab, ``@users`` and PlonePAS's search view all
merge on that key. Agreement on the userid is therefore a hard requirement of
this plugin, not an incidental property (I1).
"""

from AccessControl.class_init import InitializeClass
from pas.plugins.identity.profile.catalog import all_brains
from pas.plugins.identity.profile.catalog import query_catalog
from plone import api
from Products.PluggableAuthService.interfaces.plugins import IPropertiesPlugin
from Products.PluggableAuthService.interfaces.plugins import IUserEnumerationPlugin
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.UserPropertySheet import UserPropertySheet
from Products.PluggableAuthService.utils import classImplements
from typing import Any
from zope.interface import implementer


#: Object id of the plugin inside ``acl_users``.
PLUGIN_ID = "identity_profile"

#: Title shown in the ZMI.
PLUGIN_TITLE = "Identity: profile-backed properties and enumeration"

#: Registry record listing the workflow states a Profile is enumerated in.
ENUMERATION_STATES_RECORD = "pas.plugins.identity.profile_enumeration_states"

#: Member properties served from brain metadata. Deliberately the standard
#: Plone set and nothing invented: a property Plone has no idea about is a
#: property no template will render.
PROPERTY_FIELDS = (
    "fullname",
    "email",
    "home_page",
    "description",
    "location",
)

#: Extra ``enumerateUsers`` keywords this plugin understands, mapped to the
#: brain attribute they match against. ``name`` is what the Sharing tab sends.
SEARCH_FIELDS = {
    "fullname": "fullname",
    "email": "email",
    "name": "login",
}


def _as_terms(value: Any) -> list[str]:
    """Normalize an ``enumerateUsers`` argument to a list of strings.

    PAS allows every search argument to be either a string or a sequence of
    them, and a plugin that assumes one shape fails on the other in a way that
    looks like "no results" rather than like a type error.

    :param value: A string, a sequence of strings, or ``None``.
    :returns: The terms, empty when there was nothing to search for.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(term) for term in value]


def _matches(candidate: str | None, terms: list[str], exact: bool) -> bool:
    """Test one brain value against the search terms.

    :param candidate: The value from the brain, possibly empty.
    :param terms: Terms to match, already lowercased by the caller.
    :param exact: Whether the whole value must equal a term.
    :returns: Whether this value satisfies any term.
    """
    if not candidate:
        return False
    folded = candidate.lower()
    if exact:
        return folded in terms
    return any(term in folded for term in terms)


@implementer(IPropertiesPlugin, IUserEnumerationPlugin)
class IdentityProfilePlugin(BasePlugin):
    """Serves member properties and user enumeration from the Profile catalog."""

    meta_type = "Identity Profile Plugin"
    security = None  # set by InitializeClass below
    manage_options = BasePlugin.manage_options

    def __init__(self, id: str = PLUGIN_ID, title: str = PLUGIN_TITLE) -> None:
        """Create the plugin.

        :param id: Object id inside ``acl_users``.
        :param title: Title shown in the ZMI.
        """
        self.id = id
        self.title = title

    # -- helpers ---------------------------------------------------------

    def _enumeration_states(self) -> tuple[str, ...]:
        """Return the workflow states a Profile is visible in.

        :returns: State ids; empty when the layer is not installed here.
        """
        states = api.portal.get_registry_record(ENUMERATION_STATES_RECORD, default=None)
        return tuple(states) if states else ()

    def _active_brains(self) -> list[Any]:
        """Return brains for every Profile in an enumeration-active state.

        :returns: Brains, or an empty list when the layer is not installed.
        """
        catalog = query_catalog()
        if catalog is None:
            return []
        states = self._enumeration_states()
        return [brain for brain in all_brains(catalog) if brain.review_state in states]

    def _brain_for_userid(self, userid: str | None) -> Any | None:
        """Return the brain of one user's Profile.

        Queries the ``userid`` index rather than scanning: this runs on every
        property read, which is the hottest path in the plugin.

        :param userid: Canonical Plone userid.
        :returns: The brain, or ``None``.
        """
        if not userid:
            return None
        catalog = query_catalog()
        if catalog is None:
            return None
        brains = catalog.unrestrictedSearchResults(userid=userid)
        if not brains:
            return None
        # Two Profiles for one userid is a doctor.DUPLICATE_USERID finding, not
        # something to resolve silently here. Taking the first keeps property
        # reads deterministic while the site is broken.
        return brains[0]

    # -- IPropertiesPlugin -----------------------------------------------

    def getPropertiesForUser(self, user: Any, request: Any = None) -> Any:
        """Return the property sheet backed by this user's Profile.

        :param user: The PAS user.
        :param request: The request, unused.
        :returns: A property sheet, or ``None`` when the user has no Profile.
        """
        brain = self._brain_for_userid(user.getId())
        if brain is None:
            return None
        return UserPropertySheet(
            self.id,
            **{field: getattr(brain, field, None) or "" for field in PROPERTY_FIELDS},
        )

    # -- IUserEnumerationPlugin ------------------------------------------

    def enumerateUsers(
        self,
        id: str | None = None,
        login: str | None = None,
        exact_match: bool = False,
        sort_by: str | None = None,
        max_results: int | None = None,
        **kw: Any,
    ) -> tuple[dict[str, str], ...]:
        """Enumerate users from Profile brains.

        Matching is substring by default, which is what ``source_users`` does
        and therefore what every caller expects. That rules out serving this
        from the ``SearchableText`` index, whose globbing is word-prefix only
        and would silently miss an infix match; the index is there for site
        search and admin tooling, not for this. Scanning brains is O(n) in
        Profiles, exactly as the stock plugin is O(n) in its BTree, and it
        costs no object loads (C6).

        :param id: Userid or userids to match.
        :param login: Login name or names to match; folded, since login names
            are case-insensitive and the index stores them lowercased.
        :param exact_match: Require the whole value to equal a term.
        :param sort_by: Sort key; applied by PAS, ignored here.
        :param max_results: Result cap.
        :param kw: Additional criteria; see :data:`SEARCH_FIELDS`.
        :returns: One record per matching user.
        """
        criteria = self._criteria(id, login, kw)
        results = []
        for brain in self._active_brains():
            if criteria and not self._brain_matches(brain, criteria, exact_match):
                continue
            results.append({
                "id": brain.userid,
                "login": brain.login,
                "pluginid": self.getId(),
            })
            if max_results and len(results) >= max_results:
                break
        return tuple(results)

    def _criteria(
        self, id: str | None, login: str | None, kw: dict[str, Any]
    ) -> list[tuple[str, list[str]]]:
        """Build the ``(brain attribute, terms)`` pairs to match against.

        An empty list means "no criteria", which enumerates everybody -- the
        behaviour PAS expects from a bare ``enumerateUsers()``.

        :param id: Userid argument.
        :param login: Login argument.
        :param kw: Additional criteria.
        :returns: Attribute/terms pairs, terms lowercased.
        """
        raw = [("userid", _as_terms(id)), ("login", _as_terms(login))]
        for keyword, attribute in SEARCH_FIELDS.items():
            raw.append((attribute, _as_terms(kw.get(keyword))))
        return [
            (attribute, [term.lower() for term in terms])
            for attribute, terms in raw
            if terms
        ]

    def _brain_matches(
        self,
        brain: Any,
        criteria: list[tuple[str, list[str]]],
        exact_match: bool,
    ) -> bool:
        """Test one brain against every criterion.

        Criteria are ORed, matching PAS's own plugins: the Sharing tab issues
        one search per field and merges, so a record that matched on email
        must not be dropped for failing to match on name.

        :param brain: A Profile brain.
        :param criteria: Attribute/terms pairs.
        :param exact_match: Whether matches must be exact.
        :returns: Whether the brain matches.
        """
        return any(
            _matches(getattr(brain, attribute, None), terms, exact_match)
            for attribute, terms in criteria
        )


classImplements(
    IdentityProfilePlugin,
    IPropertiesPlugin,
    IUserEnumerationPlugin,
)

InitializeClass(IdentityProfilePlugin)


__all__ = ["PLUGIN_ID", "PLUGIN_TITLE", "IdentityProfilePlugin"]
