"""Which Profile fields a provider fills, and from which claims.

The map used to be a two-entry constant -- ``fullname`` and ``email`` -- while
the control panel offered a per-provider property map that reached the Plone
user and stopped there. With a Profile in the picture the Plone user
is served *from* the Profile, so a mapped field that never landed on the
Profile was a field the site could not show: configured, applied, and
invisible.

The map is now the same one in both places. What is *not* shared is the
ownership rule -- a provider writes a field only while it still holds the
value it last wrote -- which lives here because it needs somewhere to remember
what that was, and a Profile has annotations while a property sheet does not.
"""

from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.subscribers import claim_fields
from pas.plugins.identity.core.subscribers import DEFAULT_CLAIM_FIELDS
from pas.plugins.identity.core.subscribers import sync_claims
from plone import api

import pytest


#: A GitHub-shaped payload: the normalized claims this package derives, with
#: the provider's own document under ``raw``.
CLAIMS = {
    "fullname": "Alice Example",
    "email": "alice@example.com",
    "username": "alice",
    "picture_url": "https://example.org/alice.png",
    "raw": {
        "bio": "Writes Python for a living.",
        "blog": "https://alice.example.org",
        "location": "Berlin",
        "address": {"formatted": "Unter den Linden 1"},
        "company": "Example GmbH",
    },
}


@pytest.fixture
def provider():
    """Return a factory registering one provider with a property map.

    :returns: Callable taking a property map.
    """

    def factory(propertymap: dict[str, str]) -> None:
        set_providers([
            ProviderConfig(
                provider_id="github",
                driver_id="github",
                title="GitHub",
                propertymap=propertymap,
            )
        ])

    return factory


@pytest.fixture
def profile(portal):
    """Return an empty Profile for alice.

    :param portal: The Plone site.
    :returns: The Profile.
    """
    return api.content.create(
        container=portal["identity-profiles"],
        type=PROFILE_PORTAL_TYPE,
        id="alice",
        userid="alice",
        login="alice@example.com",
    )


class TestTheMapIsTheProvidersOwn:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_an_unmapped_provider_gets_the_default(self):
        """Enough to make an account identifiable, which is what a provider
        nobody has configured owes the site."""
        assert claim_fields("nonexistent") == DEFAULT_CLAIM_FIELDS

    def test_a_mapped_provider_gets_its_map(self, provider):
        provider({"bio": "description", "location": "location"})

        assert claim_fields("github") == {
            "bio": "description",
            "location": "location",
        }

    def test_a_field_no_provider_may_write_is_dropped(self, provider):
        """``login`` is half of the enumeration index and ``group_ids`` is
        group membership. Dropped rather than refused: the map is typed in a
        control panel, and a typo there must not fail a login."""
        provider({"username": "login", "company": "group_ids", "bio": "description"})

        assert claim_fields("github") == {"bio": "description"}


class TestClaimsReachTheProfile:
    @pytest.fixture(autouse=True)
    def _setup(self, profile, provider) -> None:
        self.profile = profile
        self.provider = provider

    def test_a_mapped_field_is_written(self, provider):
        provider({"bio": "description"})

        sync_claims(self.profile, CLAIMS, "github")

        assert self.profile.description == "Writes Python for a living."

    def test_a_claim_is_read_from_the_raw_payload(self, provider):
        """``blog`` is GitHub's, not one this package normalizes. Reaching it
        is the reason the map is addressed by claim rather than by the
        normalized names."""
        provider({"blog": "home_page"})

        sync_claims(self.profile, CLAIMS, "github")

        assert self.profile.home_page == "https://alice.example.org"

    def test_a_dotted_path_reaches_into_an_object(self, provider):
        """What the flat map buys over authomatic's nested one."""
        provider({"address.formatted": "location"})

        sync_claims(self.profile, CLAIMS, "github")

        assert self.profile.location == "Unter den Linden 1"

    def test_a_path_landing_on_an_object_writes_nothing(self, provider):
        """Rather than putting ``{'formatted': ...}`` in somebody's
        location."""
        provider({"address": "location"})

        sync_claims(self.profile, CLAIMS, "github")

        assert not self.profile.location

    def test_the_whole_map_is_applied_in_one_login(self, provider):
        provider({
            "fullname": "fullname",
            "bio": "description",
            "blog": "home_page",
            "location": "location",
        })

        changed = sync_claims(self.profile, CLAIMS, "github")

        assert sorted(changed) == [
            "description",
            "fullname",
            "home_page",
            "location",
        ]

    def test_a_map_naming_the_address_is_ignored_here(self, provider):
        """``email`` is derived from the address list, so a single-value
        write of it would move an address to the front of a list its owner
        arranged. The addresses have their own path --
        :func:`~pas.plugins.identity.core.subscribers.sync_addresses` -- and
        the same map is still honoured against the Plone user."""
        provider({"fullname": "fullname", "email": "email"})

        assert sync_claims(self.profile, CLAIMS, "github") == ["fullname"]


class TestTheOwnershipRuleStillHolds:
    """Extending the map must not extend what a provider may overwrite."""

    @pytest.fixture(autouse=True)
    def _setup(self, profile, provider) -> None:
        self.profile = profile
        provider({"bio": "description", "location": "location"})

    def test_an_edited_field_is_left_alone(self):
        sync_claims(self.profile, CLAIMS, "github")
        self.profile.description = "Something the user typed."

        sync_claims(self.profile, CLAIMS, "github")

        assert self.profile.description == "Something the user typed."

    def test_a_cleared_field_stays_cleared(self):
        """Clearing a field is an edit, and a value that reappears at the
        next login is indistinguishable from a bug."""
        sync_claims(self.profile, CLAIMS, "github")
        self.profile.location = ""

        sync_claims(self.profile, CLAIMS, "github")

        assert not self.profile.location

    def test_a_changed_claim_still_refreshes(self):
        """The half that has to keep working: a provider is the source of
        truth for a field nobody has touched."""
        sync_claims(self.profile, CLAIMS, "github")
        moved = {**CLAIMS, "raw": {**CLAIMS["raw"], "location": "Lisbon"}}

        sync_claims(self.profile, moved, "github")

        assert self.profile.location == "Lisbon"
