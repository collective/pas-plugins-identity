"""Properties and enumeration served from catalog brains.

This is the claim the whole design rests on: a site backs its
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
which is what lets a brain answer and what the tests in ``tests/content``
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
from pas.plugins.identity import logger
from pas.plugins.identity.core.catalog import group_brains
from pas.plugins.identity.core.catalog import profile_brains
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.catalog import query_catalog
from pas.plugins.identity.core.interfaces import IOwnsUserProperties
from pas.plugins.identity.core.nesting import build_edges
from pas.plugins.identity.core.nesting import close_over
from pas.plugins.identity.core.nesting import members_of
from plone import api
from Products.PlonePAS.interfaces.capabilities import IDeleteCapability
from Products.PlonePAS.interfaces.group import IGroupIntrospection
from Products.PlonePAS.interfaces.plugins import IUserManagement
from Products.PlonePAS.plugins.group import PloneGroup
from Products.PlonePAS.sheet import MutablePropertySheet
from Products.PluggableAuthService.interfaces.plugins import IGroupEnumerationPlugin
from Products.PluggableAuthService.interfaces.plugins import IGroupsPlugin
from Products.PluggableAuthService.interfaces.plugins import IPropertiesPlugin
from Products.PluggableAuthService.interfaces.plugins import IRolesPlugin
from Products.PluggableAuthService.interfaces.plugins import IUserEnumerationPlugin
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.PropertiedUser import PropertiedUser
from Products.PluggableAuthService.utils import classImplements
from Products.ZCatalog.CatalogBrains import AbstractCatalogBrain
from zope.interface import implementer
from zope.lifecycleevent import modified
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
    IOwnsUserProperties,
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

    def enumeration_states(self) -> tuple[str, ...]:
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
        states = self.enumeration_states()
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
    ) -> MutablePropertySheet | None:
        """Return the property sheet backed by this user's Profile.

        Mutable, and that is not a detail. ``MemberData.setMemberProperties``
        walks the ordered sheets and, for each key, stops at the first sheet
        that *has* it -- writing only if that sheet is mutable and silently
        writing nowhere at all if it is not. This plugin sits at the top of
        the order and has every field on it, so an immutable sheet here does
        not mean "these properties are read-only": it means every write to
        them, from the user's own preferences form, from ``@users``, from the
        login path, returns successfully having done nothing.

        **A field the Profile has no value for is filled from the plugins
        below.** The sheet still *declares* every field, because that is what
        routes a write here rather than into ``portal_memberdata`` -- but
        declaring it with an empty string used to mean the search stopped at
        this sheet and answered "nothing", which is not the same answer as
        "this user has no fullname". Every consumer read the empty string:
        the user listing, the author page, and -- how it was found -- the
        ``[server]`` layer, which omits an empty claim and so released an
        ``id_token`` carrying neither ``name`` nor ``email`` for a user who
        plainly had both.

        Declaring the field and filling it from below is the only combination
        that gets both halves right. Omitting the field instead reads
        correctly and then sends the *write* to ``portal_memberdata``, which
        quietly stops the Profile being the store for every field it does not
        already hold.

        :param user: The PAS user.
        :param request: The request, passed to the plugins consulted for a
            value this Profile does not carry.
        :returns: A property sheet, or ``None`` when the user has no Profile.
        """
        brain = self._brain_for_userid(user.getId())
        if brain is None:
            return None
        values = {field: getattr(brain, field, None) or "" for field in PROPERTY_FIELDS}
        missing = [field for field, value in values.items() if not value]
        if missing:
            values.update(self._inherited(user, request, missing))
        return MutablePropertySheet(self.id, **values)

    def _inherited(
        self,
        user: PropertiedUser,
        request: HTTPRequest | None,
        fields: list[str],
    ) -> dict[str, str]:
        """Return values for *fields* from the property plugins below this one.

        Asked of the other ``IPropertiesPlugin`` plugins in their configured
        order, which is the order PAS itself would have consulted had this
        sheet not declared the field. Self is skipped, so a plugin cannot
        answer its own question.

        A properties plugin may answer with a property sheet **or** with a
        plain mapping -- PAS accepts both, and ``PluggableAuthService``'s own
        ``_findUser`` hands whatever comes back to ``addPropertysheet``
        without looking. Asking only for ``getProperty`` here raised an
        ``AttributeError`` from inside ``getUserById``, which surfaces as
        every user on the site becoming unfetchable rather than as anything
        about properties.

        :param user: The PAS user.
        :param request: The request, handed on unchanged.
        :param fields: Fields this Profile has no value for.
        :returns: Field to value, holding only the fields something answered.
        """
        found: dict[str, str] = {}
        plugins = self._getPAS()._getOb("plugins")
        for plugin_id, plugin in plugins.listPlugins(IPropertiesPlugin):
            if plugin_id == self.id:
                continue
            data = plugin.getPropertiesForUser(user, request)
            if data is None:
                continue
            read = data.get if isinstance(data, dict) else data.getProperty
            for field in fields:
                if field in found:
                    continue
                try:
                    value = read(field, "")
                except Exception:
                    # One misbehaving properties plugin must not make every
                    # user on the site unfetchable: this runs inside
                    # `getUserById`.
                    logger.exception(
                        "Properties plugin %s failed answering for %s",
                        plugin_id,
                        user.getId(),
                    )
                    break
                if value:
                    found[field] = value
            if len(found) == len(fields):
                break
        return found

    def setPropertiesForUser(
        self, user: PropertiedUser, propertysheet: MutablePropertySheet
    ) -> None:
        """Write a sheet back onto the user's Profile.

        Called by :class:`~Products.PlonePAS.sheet.MutablePropertySheet`,
        which resolves this plugin by the id the sheet was built with.

        Runs unrestricted. The permission to edit a Profile is decided on the
        Profile, by the workflow -- see the ``profile`` profile's
        ``rolemap.xml`` -- and PAS has already resolved who is asking by the
        time a property write arrives here; re-deciding it against the
        catalog's brain would be a second, weaker answer to a question
        already answered.

        :param user: The PAS user.
        :param propertysheet: The sheet holding the new values.
        """
        from pas.plugins.identity.core.subscribers import get_profile

        profile = get_profile(user.getId())
        if profile is None:  # pragma: no cover - the sheet came from a Profile
            return

        changed = False
        for field in PROPERTY_FIELDS:
            if not propertysheet.hasProperty(field):
                continue
            value = propertysheet.getProperty(field)
            before = getattr(profile, field, None) or ""
            if before == (value or ""):
                continue
            setattr(profile, field, value)
            # Compared again afterwards rather than assumed. ``email`` is
            # derived from the profile's address list, and a write of it is
            # an instruction about that list rather than an assignment -- an
            # empty one changes nothing, and reporting a change here would
            # reindex on every save of a form that left the box blank.
            if (getattr(profile, field, None) or "") != before:
                changed = True

        if changed:
            # The catalog is this layer's only read path -- the property sheet
            # above is served from a brain -- so a write nobody reindexed is a
            # write nobody can see.
            modified(profile)

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

    def active_group_brains(self) -> list[AbstractCatalogBrain]:
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
        return {brain.group_id for brain in self.active_group_brains()}

    def group_edges(self) -> dict[str, tuple[str, ...]]:
        """Return the group-in-group graph, read from brains.

        One catalog query and no object loads, which is what makes the
        transitive answers below affordable on the paths that ask them. Only
        active groups are in it, so a deactivated group neither grants nor
        conducts -- deactivating has to remove the access of everybody who
        reached something *through* that group, or it is not a control.

        :returns: Group id to the ids of the groups it belongs to.
        """
        return build_edges(self.active_group_brains())

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

        Nesting is closed over here rather than stored: a group carries
        ``group_ids`` too, and a member of an inner group is a member of every
        group that group belongs to. The walk is over the group graph, which
        is the small one -- it grows with the number of teams, not with the
        number of people -- and it comes out of catalog metadata in a single
        query. See :mod:`pas.plugins.identity.core.nesting`.

        :param principal: The user PAS is asking about.
        :param request: The request, unused.
        :returns: Group ids, direct and inherited.
        """
        principal_id = principal.getId()
        brain = self._brain_for_userid(principal_id)
        if brain is not None:
            claimed = tuple(getattr(brain, "group_ids", None) or ())
            return close_over(claimed, self.group_edges()) if claimed else ()

        # A group is a principal too, and PAS asks this about one while
        # working out what a group's roles are. Answering it here means the
        # nesting holds however the question arrives, rather than only on the
        # path that happens to start from a user.
        edges = self.group_edges()
        if principal_id in edges:
            return tuple(
                group_id
                for group_id in close_over(edges[principal_id], edges)
                # A cycle would otherwise make a group a member of itself,
                # which nothing downstream expects to see.
                if group_id != principal_id
            )
        return ()

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
        for brain in self.active_group_brains():
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

        A nested group's members are included. The nesting is resolved into a
        list of group ids first and the catalog is then asked for all of them
        at once -- ``group_ids`` is a KeywordIndex, so a query naming ten
        groups is still one query, where recursing per level would be one per
        level per branch.

        Groups nested under this one are *not* returned as members. PAS
        expects userids here, and a group id among them would be resolved as
        a user by everything that reads the answer. Which groups feed into
        this one is a different question, and
        :meth:`getNestedGroupIds` answers it.

        :param group_id: The group id.
        :returns: Userids, sorted.
        """
        catalog = query_catalog()
        if catalog is None:
            return ()
        feeding = members_of(group_id, self.group_edges())
        if not feeding:
            return ()
        states = self.enumeration_states()
        return tuple(
            sorted({
                brain.userid
                for brain in catalog.unrestrictedSearchResults(
                    portal_type=PROFILE_PORTAL_TYPE, group_ids=list(feeding)
                )
                if brain.review_state in states
            })
        )

    def getNestedGroupIds(self, group_id: str) -> tuple[str, ...]:
        """Return the groups nested under one group, at any depth.

        Not part of any PAS interface -- it is this package's own question,
        asked by the group view and by ``@group-members``. The group itself
        is excluded: a caller asking what is *inside* a group does not want
        the group back.

        :param group_id: The outer group.
        :returns: Group ids, sorted.
        """
        feeding = members_of(group_id, self.group_edges())
        return tuple(gid for gid in feeding if gid != group_id)

    def getGroupParentIds(self, group_id: str) -> tuple[str, ...]:
        """Return the groups one group is directly a member of.

        The stored edges rather than the closure, because this is the value
        an edit form shows: what somebody typed, not what it implies.

        :param group_id: The inner group.
        :returns: Group ids, in stored order.
        """
        for brain in self.active_group_brains():
            if brain.group_id == group_id:
                return tuple(getattr(brain, "group_ids", None) or ())
        return ()

    # -- IUserManagement / IDeleteCapability -----------------------------
    #
    # Deleting a user has to reach the object, because the object is the
    # account. Without this, ``api.user.delete`` removed whatever
    # ``source_users`` held -- usually nothing, for a user who signed in
    # through a provider -- and left the Profile answering enumeration and
    # serving properties, so the user was not deleted and nothing said so.
    #
    # PlonePAS walks every ``IUserManagement`` plugin and swallows the
    # ordinary exceptions, so declining for a userid this plugin does not
    # hold is the protocol rather than a failure.

    def doDeleteUser(self, userid: str) -> bool:
        """Delete the Profile that *is* this user.

        The identity records are deliberately left alone. An identity outlives
        the account by design here -- it is what lets a person sign in again
        with the same userid -- and removing it is a separate decision an
        operator makes deliberately. A login through an identity whose account
        is gone says so at warning level; see
        :meth:`~pas.plugins.identity.core.pas.plugin.IdentityPlugin._warn_if_orphaned`.

        :param userid: Canonical Plone userid.
        :returns: Whether a Profile was deleted.
        :raises KeyError: If this plugin holds no Profile for that userid,
            which is how PAS is told to try the next plugin.
        """
        brain = self._brain_for_userid(userid)
        if brain is None:
            raise KeyError(userid)

        from plone import api

        with api.env.adopt_roles(["Manager"]):
            api.content.delete(
                obj=brain._unrestrictedGetObject(), check_linkintegrity=False
            )
        logger.info("Deleted the profile of %s", userid)
        return True

    def doChangeUser(self, principal_id: str, password: str) -> None:
        """Refuse: this plugin is not a credential store.

        Declared because ``IUserManagement`` declares it, and answered
        honestly rather than silently. ``RuntimeError`` is what PlonePAS's
        ``userSetPassword`` expects from a plugin that cannot set a password,
        and it moves on to the next one.

        A site that keeps passwords on the Profile does so through the
        password *behavior*, which core adapts to on the authentication path.
        Wiring it here as well would give a site two ways to write the same
        credential.

        :param principal_id: Canonical Plone userid.
        :param password: The new password.
        :raises RuntimeError: Always.
        """
        raise RuntimeError(
            f"{PLUGIN_ID} does not store passwords; see the password behavior"
        )

    def allowDeletePrincipal(self, principal_id: str) -> bool:
        """Report whether the Plone UI may offer to delete this user.

        Answered from the catalog, because the users listing asks it once per
        row.

        :param principal_id: Canonical Plone userid.
        :returns: Whether this plugin holds a Profile for them.
        """
        return self._brain_for_userid(principal_id) is not None


classImplements(
    IdentityProfilePlugin,
    IOwnsUserProperties,
    IPropertiesPlugin,
    IUserEnumerationPlugin,
    IGroupsPlugin,
    IGroupEnumerationPlugin,
    IGroupIntrospection,
    IUserManagement,
    IDeleteCapability,
)

InitializeClass(IdentityProfilePlugin)


__all__ = ["PLUGIN_ID", "PLUGIN_TITLE", "IdentityProfilePlugin"]
