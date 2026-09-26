"""How much of the catalog one user lookup reads.

PAS resolves every ``getUserById`` through ``enumerateUsers(id=...,
exact_match=True)``, and that call used to scan every Profile brain. One
lookup was O(n) in Profiles, and anything resolving many users was O(n²): on
a site with 1,727 Profiles, ``GET @users`` spent about 47 seconds before
reading a property, and one ``GET @groups`` ran for more than seven minutes,
long enough to fill every worker and get the container restarted (issue #110).

Measured here as work rather than time. A timing test on a shared CI runner
either passes a regression or fails for a noisy neighbour; the number of
brains the catalog hands back is what the fix changes, and it is exact. Each
test states how many brains a call may read, on a site large enough that a
scan cannot hide inside the bound.
"""

from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.catalog import query_catalog
from pas.plugins.identity.core.pas.profile import ENUMERATION_STATES_RECORD
from pas.plugins.identity.core.pas.profile import IdentityProfilePlugin
from plone import api

import pytest


#: Profiles on the site. Large against every bound below, so a scan cannot
#: pass for a lookup, and small enough to build in a couple of seconds.
PROFILES = 60


@pytest.fixture
def brains_read(portal, monkeypatch):
    """Count the brains the identity catalog returns, from now on.

    Wraps ``unrestrictedSearchResults`` on the catalog instance, which is the
    only way this package queries it, so a scan and an index lookup are
    counted by the same meter.

    :param portal: The Plone site.
    :param monkeypatch: pytest's monkeypatch, which puts the method back.
    :returns: A one-element list holding the running total.
    """
    catalog = query_catalog()
    original = catalog.unrestrictedSearchResults
    total = [0]

    def counting(*args, **kwargs):
        results = original(*args, **kwargs)
        total[0] += len(results)
        return results

    monkeypatch.setattr(catalog, "unrestrictedSearchResults", counting)
    return total


class TestOneLookup:
    """On a site whose users exist only as Profiles.

    Which is every account an import or a federated sign-in created, and the
    only case where the profile plugin is asked at all: PAS returns the first
    enumerator's answer, so a user ``source_users`` also holds is resolved
    there and never reaches this plugin. A fixture giving each user a
    ``source_users`` account measured nothing -- these tests passed with the
    scan put back.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, profile_plugin) -> None:
        self.acl_users = acl_users
        self.plugin = profile_plugin
        with api.env.adopt_roles(["Manager"]):
            for index in range(PROFILES):
                userid = f"user{index}"
                api.content.create(
                    container=portal["identity-profiles"],
                    type=PROFILE_PORTAL_TYPE,
                    id=userid,
                    userid=userid,
                    login=f"User{index}@Example.org",
                    fullname=f"User Number {index}",
                )

    def test_an_exact_id_reads_only_its_match(self, brains_read):
        results = self.plugin.enumerateUsers(id="user42", exact_match=True)

        assert [record["id"] for record in results] == ["user42"]
        assert brains_read[0] == 1

    def test_an_exact_login_reads_only_its_match(self, brains_read):
        results = self.plugin.enumerateUsers(
            login="USER42@example.org", exact_match=True
        )

        assert [record["id"] for record in results] == ["user42"]
        assert brains_read[0] == 1

    def test_a_miss_reads_nothing(self, brains_read):
        assert self.plugin.enumerateUsers(id="nobody", exact_match=True) == ()
        assert brains_read[0] == 0

    def test_get_user_by_id_does_not_grow_with_the_site(self, brains_read):
        """The call that was measured at 27 ms on 1,727 Profiles. It reads
        the lookup's brain and the property sheet's, and nothing else."""
        user = self.acl_users.getUserById("user42")

        assert user is not None
        assert brains_read[0] <= 4

    def test_resolving_everybody_is_linear(self, brains_read):
        """What ``@users`` does on load, one ``getMemberById`` per user.

        Linear means a small constant per user. Quadratic, which is what the
        scan made it, would be ``PROFILES`` per user -- 3,600 here, against a
        bound of 240.
        """
        for index in range(PROFILES):
            assert self.acl_users.getUserById(f"user{index}") is not None

        assert brains_read[0] <= 4 * PROFILES

    def test_a_substring_search_still_scans(self, brains_read):
        """The control: the meter sees a scan when there is one.

        Without it, every bound above could pass because the counter was
        wired to something the lookup never calls.
        """
        results = self.plugin.enumerateUsers(fullname="Number 4")

        assert "user4" in [record["id"] for record in results]
        assert brains_read[0] >= PROFILES


class TestGroupsOnTheSite:
    """A lookup against the number of Groups, rather than of Profiles.

    ``getGroupsForPrincipal`` used to read every Group brain to build the
    group graph, and PAS asks it five times while building one user -- once
    for the user, three times from Plone's ``recursive_groups`` for the groups
    it found, once from PlonePAS for the roles. So one ``getUserById`` read
    ``4 + 5·G`` brains, and every authenticated request paid it (issue #115).
    """

    @pytest.fixture
    def groups(self, request, portal, make_group) -> int:
        """Create the parametrized number of Groups, and alice in the first.

        Built here rather than in the test, before the meter is installed:
        the meter patches the persistent catalog, and a savepoint taken while
        the patch is on would try to pickle it.

        :param request: pytest's request, carrying the number of Groups.
        :param portal: The Plone site.
        :param make_group: Factory for Group content.
        :returns: The number of Groups on the site.
        """
        with api.env.adopt_roles(["Manager"]):
            for index in range(request.param):
                make_group(f"team{index}")
            api.content.create(
                container=portal["identity-profiles"],
                type=PROFILE_PORTAL_TYPE,
                id="alice",
                userid="alice",
                login="alice@example.org",
                group_ids=("team0",),
            )
        return request.param

    @pytest.mark.parametrize("groups", [1, 10, 50], indirect=True)
    def test_a_lookup_does_not_grow_with_the_groups(
        self, groups, acl_users, brains_read
    ):
        user = acl_users.getUserById("alice")

        assert "team0" in user.getGroups()
        assert brains_read[0] <= 7

    @pytest.mark.parametrize("groups", [10], indirect=True)
    def test_the_whole_graph_is_read_once_per_request(
        self, groups, profile_plugin, brains_read
    ):
        """The readers that do need every Group -- listings, the group
        control panel -- share one read within a request."""
        profile_plugin.getGroupIds()
        profile_plugin.enumerateGroups()
        profile_plugin.getNestedGroupIds("team0")

        assert brains_read[0] == groups


class TestTheLookupIsExact:
    """What moving to the index changed, stated so nobody rediscovers it."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, profile_plugin) -> None:
        self.plugin = profile_plugin
        with api.env.adopt_roles(["Manager"]):
            acl_users.source_users.addUser("alice", "alice", "placeholder")
            api.content.create(
                container=portal["identity-profiles"],
                type=PROFILE_PORTAL_TYPE,
                id="alice",
                userid="alice",
                login="Alice@Example.org",
            )

    def test_an_exact_id_is_case_sensitive(self):
        """As Plone userids are. The scan folded both sides, so ``Alice``
        used to find ``alice``; the ``userid`` index matches what is stored.
        """
        assert self.plugin.enumerateUsers(id="Alice", exact_match=True) == ()
        assert self.plugin.enumerateUsers(id="alice", exact_match=True)

    def test_an_exact_login_is_not(self):
        """Logins are case-insensitive in Plone, and the index stores them
        folded, so this did not change."""
        assert self.plugin.enumerateUsers(login="ALICE@example.org", exact_match=True)

    def test_an_id_and_a_login_are_ored_and_returned_once(self):
        """Two index queries merged, since PAS criteria are ORed; the brain
        both of them find is one user, not two."""
        results = self.plugin.enumerateUsers(
            id="alice", login="alice@example.org", exact_match=True
        )

        assert [record["id"] for record in results] == ["alice"]

    def test_an_id_or_a_login_finds_either(self):
        results = self.plugin.enumerateUsers(
            id="nobody", login="alice@example.org", exact_match=True
        )

        assert [record["id"] for record in results] == ["alice"]

    def test_an_empty_id_matches_nothing(self):
        """What an over-eager search box sends. The scan never matched it,
        and an index query for ``""`` must not start to."""
        assert self.plugin.enumerateUsers(id="", exact_match=True) == ()

    def test_max_results_is_honoured(self):
        results = self.plugin.enumerateUsers(
            id="alice", login="alice@example.org", exact_match=True, max_results=1
        )

        assert len(results) == 1

    def test_no_enumeration_state_finds_nobody(self, monkeypatch):
        """As the scan did. The states record cannot be emptied -- it is
        required -- so no states means the record is absent, which is a site
        where the layer is not installed, and an empty list of states must not
        read as "any state"."""
        monkeypatch.setattr(
            IdentityProfilePlugin, "enumeration_states", lambda self: ()
        )

        assert self.plugin.enumerateUsers(id="alice", exact_match=True) == ()

    def test_a_state_outside_the_record_is_not_found(self):
        """The index query filters on state as the scan did."""
        api.portal.set_registry_record(ENUMERATION_STATES_RECORD, ("complete",))

        assert self.plugin.enumerateUsers(id="alice", exact_match=True) == ()
