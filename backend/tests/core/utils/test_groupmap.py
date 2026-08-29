"""Reading a provider's group claim, and resolving it against a map.

No Plone here. The mapping is the part that is pure, and it is worth having
it that way: what a provider asserted and what that grants are two separate
questions, and only the second one has an opinion.
"""

from pas.plugins.identity.core.utils.groupmap import claimed_groups
from pas.plugins.identity.core.utils.groupmap import DEFAULT_GROUP_CLAIM
from pas.plugins.identity.core.utils.groupmap import map_groups

import pytest


def claims(**raw) -> dict:
    """Build a claims mapping carrying ``raw``.

    :param raw: The raw provider payload.
    :returns: Normalized-shaped claims.
    """
    return {"fullname": "", "email": "", "raw": dict(raw)}


class TestTheDefaultClaim:
    def test_it_is_groups(self):
        """Not registered by OIDC, but what Keycloak, Okta and Entra emit --
        and what this package's own server layer releases."""
        assert DEFAULT_GROUP_CLAIM == "groups"


class TestClaimedGroups:
    def test_a_list_of_strings(self):
        assert claimed_groups("groups", claims(groups=["editors", "staff"])) == [
            "editors",
            "staff",
        ]

    def test_a_bare_string_is_one_group(self):
        """A provider with one group per user sends a string, not a list."""
        assert claimed_groups("groups", claims(groups="editors")) == ["editors"]

    def test_a_dotted_path_reaches_a_nested_claim(self):
        """Keycloak puts them under `realm_access.roles`, which is why the
        claim is configurable rather than fixed."""
        payload = claims(realm_access={"roles": ["editors"]})

        assert claimed_groups("realm_access.roles", payload) == ["editors"]

    def test_an_absent_claim_is_no_groups(self):
        assert claimed_groups("groups", claims()) == []

    def test_values_are_stripped(self):
        assert claimed_groups("groups", claims(groups=["  editors  "])) == ["editors"]

    def test_blank_values_are_dropped(self):
        assert claimed_groups("groups", claims(groups=["", "   ", "editors"])) == [
            "editors"
        ]

    def test_duplicates_are_dropped_and_order_kept(self):
        payload = claims(groups=["staff", "editors", "staff"])

        assert claimed_groups("groups", payload) == ["staff", "editors"]

    @pytest.mark.parametrize(
        "value",
        [
            42,
            {"editors": True},
            [{"name": "editors"}],
            [1, 2],
            None,
        ],
    )
    def test_a_shape_we_do_not_understand_yields_nothing(self, value):
        """Ignored rather than coerced.

        A group name invented by stringifying a payload matches nothing in
        the map anyway, and a silent near-miss is worse than an absence.
        """
        assert claimed_groups("groups", claims(groups=value)) == []

    def test_usable_entries_survive_an_unusable_neighbour(self):
        payload = claims(groups=["editors", {"name": "staff"}, 7])

        assert claimed_groups("groups", payload) == ["editors"]


class TestMapGroups:
    def test_a_mapped_name_resolves(self):
        assert map_groups({"editors": "site-editors"}, ["editors"]) == {"site-editors"}

    def test_an_unmapped_name_grants_nothing(self):
        """Never auto-created. A group claim is whatever the provider's own
        directory is called, and minting local groups from it would let
        anyone who can name a group at the far end create one here."""
        assert map_groups({"editors": "site-editors"}, ["admins"]) == set()

    def test_two_names_may_map_to_one_group(self):
        groupmap = {"editors": "staff", "authors": "staff"}

        assert map_groups(groupmap, ["editors", "authors"]) == {"staff"}

    def test_an_entry_cleared_to_empty_grants_nothing(self):
        """How the control panel represents a row an operator blanked without
        deleting it."""
        assert map_groups({"editors": ""}, ["editors"]) == set()
        assert map_groups({"editors": "   "}, ["editors"]) == set()

    def test_an_empty_map_grants_nothing(self):
        assert map_groups({}, ["editors"]) == set()

    def test_no_claimed_names_grant_nothing(self):
        assert map_groups({"editors": "site-editors"}, []) == set()
