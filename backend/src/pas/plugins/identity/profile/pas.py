"""Properties and enumeration served from catalog brains.

This is the claim the whole ``[profile]`` design rests on: a site can back its
users with content objects and still answer "what is this user's full name"
and "who matches 'liddell'" without loading a single Profile from the ZODB.
Every read here goes through catalog metadata, and the tests for this module
assert the object-load count is zero while they run.

Why it matters: enumeration is called on paths where waking content is
unacceptable -- rendering a Sharing tab, resolving a local role, listing group
members. ``Products.membrane`` does wake objects on the *properties* path --
its ``MembranePropertyManager`` adapts ``brain._unrestrictedGetObject()``,
uncached -- though not on enumeration, which stays on brains. That is
architecture rather than oversight: membrane's property values live on the
content object and are read through an adapter on it, so a brain cannot
answer. This layer copies the values it serves into catalog metadata instead,
which is what lets a brain answer and what the tests in ``tests/profile``
measure on every CI run.

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
this plugin, not an incidental property.
"""

from AccessControl.class_init import InitializeClass
from pas.plugins.identity.profile.catalog import group_brains
from pas.plugins.identity.profile.catalog import profile_brains
from pas.plugins.identity.profile.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.profile.catalog import query_catalog
from plone import api
from Products.PlonePAS.interfaces.group import IGroupIntrospection
from Products.PlonePAS.plugins.group import PloneGroup
from Products.PluggableAuthService.interfaces.plugins import IGroupEnumerationPlugin
from Products.PluggableAuthService.interfaces.plugins import IGroupsPlugin
from Products.PluggableAuthService.interfaces.plugins import IPropertiesPlugin
from Products.PluggableAuthService.interfaces.plugins import IRolesPlugin
from Products.PluggableAuthService.interfaces.plugins import IUserEnumerationPlugin
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.PropertiedUser import PropertiedUser
from Products.PluggableAuthService.UserPropertySheet import UserPropertySheet
from Products.PluggableAuthService.utils import classImplements
from Products.ZCatalog.CatalogBrains import AbstractCatalogBrain
from zope.interface import implementer
from ZPublisher.HTTPRequest import HTTPRequest


#: Object id of the plugin inside ``acl_users``.
PLUGIN_ID = "identity_profile"

#: Title shown in the ZMI.
PLUGIN_TITLE = "Identity: profile-backed properties and enumeration"

#: Registry record listing the workflow states a Profile is enumerated in.
ENUMERATION_STATES_RECORD = "pas.plugins.identity.profile_enumeration_states"

#: Registry record listing the workflow states a Group is enumerated in.
GROUP_STATES_RECORD = "pas.plugins.identity.group_enumeration_states"

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


def _as_terms(value: str | list[str] | tuple[str, ...] | None) -> list[str]:
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


@implementer(
    IPropertiesPlugin,
    IUserEnumerationPlugin,
    IGroupsPlugin,
    IGroupEnumerationPlugin,
    IGroupIntrospection,
)
class IdentityProfilePlugin(BasePlugin):
    """Serves properties, user enumeration and groups from the catalog."""

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

    def _active_brains(self) -> list[AbstractCatalogBrain]:
        """Return brains for every Profile in an enumeration-active state.

        :returns: Brains, or an empty list when the layer is not installed.
        """
        catalog = query_catalog()
        if catalog is None:
            return []
        states = self._enumeration_states()
        return [
            brain for brain in profile_brains(catalog) if brain.review_state in states
        ]

    def _brain_for_userid(self, userid: str | None) -> AbstractCatalogBrain | None:
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

    def getPropertiesForUser(
        self, user: PropertiedUser, request: HTTPRequest | None = None
    ) -> UserPropertySheet | None:
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
        **kw: str,
    ) -> tuple[dict[str, str], ...]:
        """Enumerate users from Profile brains.

        Matching is substring by default, which is what ``source_users`` does
        and therefore what every caller expects. That rules out serving this
        from the ``SearchableText`` index, whose globbing is word-prefix only
        and would silently miss an infix match; the index is there for site
        search and admin tooling, not for this. Scanning brains is O(n) in
        Profiles, exactly as the stock plugin is O(n) in its BTree, and it
        costs no object loads.

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
        self, id: str | None, login: str | None, kw: dict[str, str]
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
        brain: AbstractCatalogBrain,
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

    # -- groups -------------------------------------------------

    def _group_states(self) -> tuple[str, ...]:
        """Return the workflow states a Group is visible in.

        :returns: State ids; empty when the layer is not installed here.
        """
        states = api.portal.get_registry_record(GROUP_STATES_RECORD, default=None)
        return tuple(states) if states else ()

    def _active_group_brains(self) -> list[AbstractCatalogBrain]:
        """Return brains for every Group in an enumeration-active state.

        :returns: Brains, or an empty list when the layer is not installed.
        """
        catalog = query_catalog()
        if catalog is None:
            return []
        states = self._group_states()
        return [
            brain for brain in group_brains(catalog) if brain.review_state in states
        ]

    def _active_group_ids(self) -> set[str]:
        """Return the ids of the groups that currently exist and are active.

        :returns: Group ids.
        """
        return {brain.group_id for brain in self._active_group_brains()}

    def getGroupsForPrincipal(
        self, principal: PropertiedUser, request: HTTPRequest | None = None
    ) -> tuple[str, ...]:
        """Return the ids of the groups a principal belongs to.

        Read off the principal's own Profile brain, which is why membership
        lives on the member rather than on the group: this is asked on every
        permission check that touches a local role, and answering it must not
        cost an object load.

        Filtered against the groups that actually exist and are active, so
        deactivating a group removes its members' access without editing a
        single Profile -- and so a group id left behind by a deleted group
        does not keep granting anything.

        :param principal: The user PAS is asking about.
        :param request: The request, unused.
        :returns: Group ids.
        """
        brain = self._brain_for_userid(principal.getId())
        if brain is None:
            return ()
        claimed = tuple(getattr(brain, "group_ids", None) or ())
        if not claimed:
            return ()
        active = self._active_group_ids()
        return tuple(group_id for group_id in claimed if group_id in active)

    def enumerateGroups(
        self,
        id: str | None = None,
        exact_match: bool = False,
        sort_by: str | None = None,
        max_results: int | None = None,
        **kw: str,
    ) -> tuple[dict[str, str], ...]:
        """Enumerate groups from Group brains.

        Substring by default, like the user enumeration and for the same
        reason: it is what the stock plugins do and therefore what the Sharing
        tab expects.

        :param id: Group id or ids to match.
        :param exact_match: Require the whole value to equal a term.
        :param sort_by: Sort key; applied by PAS, ignored here.
        :param max_results: Result cap.
        :param kw: Additional criteria; ``title`` and ``name`` are understood.
        :returns: One record per matching group.
        """
        criteria = [
            (attribute, [term.lower() for term in terms])
            for attribute, terms in (
                ("group_id", _as_terms(id)),
                ("Title", _as_terms(kw.get("title"))),
                ("group_id", _as_terms(kw.get("name"))),
            )
            if terms
        ]
        results = []
        for brain in self._active_group_brains():
            if criteria and not self._brain_matches(brain, criteria, exact_match):
                continue
            results.append({
                "id": brain.group_id,
                "title": brain.Title,
                "pluginid": self.getId(),
            })
            if max_results and len(results) >= max_results:
                break
        return tuple(results)

    # -- IGroupIntrospection ---------------------------------------------

    def getGroupById(
        self, group_id: str, default: PloneGroup | None = None
    ) -> PloneGroup | None:
        """Return a decorated group object for one group id.

        Built the way PlonePAS builds its own: a ``PloneGroup`` decorated with
        every property sheet, nested group and role the site's plugins offer
        it. Constructing it by hand instead would produce something that looks
        like a group until the first template asks it a question.

        :param group_id: The group id.
        :param default: Returned when there is no such active group.
        :returns: The group, or ``default``.
        """
        if group_id not in self._active_group_ids():
            return default
        return self._decorate(group_id)

    def _decorate(self, group_id: str) -> PloneGroup:
        """Wrap a group id as a ``PloneGroup`` carrying its site data.

        :param group_id: The group id.
        :returns: The decorated group.
        """
        plugins = self._getPAS()._getOb("plugins")
        group = PloneGroup(group_id, group_id).__of__(self)

        for propfinder_id, propfinder in plugins.listPlugins(IPropertiesPlugin):
            data = propfinder.getPropertiesForUser(group, None)
            if data:
                group.addPropertysheet(propfinder_id, data)

        for _rolemaker_id, rolemaker in plugins.listPlugins(IRolesPlugin):
            roles = rolemaker.getRolesForPrincipal(group, None)
            if roles:
                group._addRoles(roles)
        group._addRoles(["Authenticated"])

        return group.__of__(self)

    def getGroupIds(self) -> list[str]:
        """Return the ids of every active group.

        :returns: Group ids, sorted so listings are stable.
        """
        return sorted(self._active_group_ids())

    def getGroups(self) -> list[PloneGroup]:
        """Return every active group, decorated.

        :returns: Group objects.
        """
        return [self._decorate(group_id) for group_id in self.getGroupIds()]

    def getGroupMembers(self, group_id: str) -> tuple[str, ...]:
        """Return the userids belonging to a group.

        The rare direction of the question, so it is the one that costs a
        catalog query rather than a metadata read. Still brains only.

        :param group_id: The group id.
        :returns: Userids, sorted.
        """
        catalog = query_catalog()
        if catalog is None:
            return ()
        states = self._enumeration_states()
        return tuple(
            sorted(
                brain.userid
                for brain in catalog.unrestrictedSearchResults(
                    portal_type=PROFILE_PORTAL_TYPE, group_ids=group_id
                )
                if brain.review_state in states
            )
        )


classImplements(
    IdentityProfilePlugin,
    IPropertiesPlugin,
    IUserEnumerationPlugin,
    IGroupsPlugin,
    IGroupEnumerationPlugin,
    IGroupIntrospection,
)

InitializeClass(IdentityProfilePlugin)


__all__ = ["PLUGIN_ID", "PLUGIN_TITLE", "IdentityProfilePlugin"]
