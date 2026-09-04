"""The provider's group map, applied through a real login.

The counterpart of :mod:`.test_propertymap_login`, and the tests worth reading
twice are the fencing ones.

Federated membership has a problem local membership does not: it has to be
*taken back*. A group revoked at the provider must stop granting anything
here, and nobody is going to notice that by hand. But a login that simply
overwrote the user's groups with what the provider said would also wipe every
group an administrator granted locally, and every group a *second* provider
granted -- silently, on the next sign-in.

So the identity record remembers what its own provider granted, and a login
adds what is newly granted and removes only what that same provider granted
before. Everything else is somebody else's to manage.
"""

from . import CLAIMS
from . import DEX_IDENTITY
from . import GITHUB_IDENTITY
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.pas import EXTRACTOR
from plone import api

import pytest


PROVIDER, SUBJECT = DEX_IDENTITY
OTHER_PROVIDER, OTHER_SUBJECT = GITHUB_IDENTITY

#: A second OIDC provider for the same human: another realm, or a partner
#: issuer. It shares the driver with the first and nothing else.
SECOND_IDENTITY = ("oidc-partner", "partner-sub-99")
SECOND_PROVIDER, SECOND_SUBJECT = SECOND_IDENTITY

#: The map every test below uses unless it says otherwise. Two provider-side
#: names, so a test can revoke one without emptying the claim.
GROUPMAP = {"editors": "site-editors", "staff": "site-staff"}


def with_groups(*names: str, claim: str = "groups") -> dict:
    """Return claims asserting group membership.

    :param names: Provider-side group names.
    :param claim: The raw claim to put them in.
    :returns: Claims for :meth:`TestGroupMapOnLogin.authenticate`.
    """
    return {**CLAIMS, "raw": {claim: list(names)}}


def configure(
    groupmap: dict[str, str] | None = None,
    config: dict | None = None,
    provider_id: str = PROVIDER,
    extra: list[ProviderConfig] | None = None,
) -> None:
    """Store a provider with a group map.

    :param groupmap: Provider group name to local group id.
    :param config: Driver settings, e.g. a different ``group_claim``.
    :param provider_id: Which provider to configure.
    :param extra: Further providers to store alongside it.
    """
    set_providers([
        ProviderConfig(
            provider_id=provider_id,
            driver_id="oidc-generic",
            title="Dex",
            config=config or {},
            groupmap=GROUPMAP if groupmap is None else groupmap,
        ),
        *(extra or []),
    ])


class GroupMapCase:
    """The harness both groups of these tests drive.

    A base with no tests of its own, like ``CallbackCase`` next door: a test
    class that inherits from another *test* class re-runs every one of its
    tests under the second name, which is duplicated runtime and a test count
    that no longer means anything.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin) -> None:
        self.portal = portal
        self.plugin = plugin
        for name in ("site-editors", "site-staff", "granted-by-hand"):
            api.group.create(groupname=name)

    def authenticate(self, claims=None, identity=DEX_IDENTITY) -> str:
        """Run a login and return the userid it resolved to.

        :param claims: Claims to authenticate with.
        :param identity: The ``(provider, subject)`` signing in.
        :returns: The Plone userid.
        """
        provider, subject = identity
        userid, _ = self.plugin.authenticateCredentials({
            "extractor": EXTRACTOR,
            "provider": provider,
            "subject": subject,
            "claims": CLAIMS if claims is None else claims,
        })
        return userid

    def groups_of(self, userid: str) -> set[str]:
        """Return the group ids a user is in, minus the virtual one.

        :param userid: The Plone userid.
        :returns: Group ids.
        """
        return {group.id for group in api.group.get_groups(username=userid)} - {
            "AuthenticatedUsers"
        }

    def granted_by(self, provider: str, subject: str) -> tuple[str, ...]:
        """Return what one provider recorded as its own grant.

        :param provider: Provider id.
        :param subject: Provider-side subject.
        :returns: Local group ids.
        """
        return self.plugin.store.get(provider, subject).groups


class TestGroupMapOnLogin(GroupMapCase):
    # -- the feature ----------------------------------------------------

    def test_a_mapped_claim_grants_the_local_group(self):
        configure()

        assert self.groups_of(self.authenticate(with_groups("editors"))) == {
            "site-editors"
        }

    def test_an_unmapped_claim_grants_nothing(self):
        """And does not create a group named after the provider's."""
        configure()

        userid = self.authenticate(with_groups("wheel"))

        assert self.groups_of(userid) == set()
        assert api.group.get(groupname="wheel") is None

    def test_the_claim_can_be_configured(self):
        """Keycloak puts them under `realm_access.roles`."""
        configure(config={"group_claim": "realm_access.roles"})
        claims = {**CLAIMS, "raw": {"realm_access": {"roles": ["editors"]}}}

        assert self.groups_of(self.authenticate(claims)) == {"site-editors"}

    def test_the_grant_is_recorded_against_the_identity(self):
        """Which is what makes taking it back possible later."""
        configure()
        self.authenticate(with_groups("editors"))

        assert self.granted_by(PROVIDER, SUBJECT) == ("site-editors",)

    # -- revocation ------------------------------------------------------

    def test_a_revoked_claim_takes_the_group_away(self):
        """The reason this runs on every login and not only the first."""
        configure()
        userid = self.authenticate(with_groups("editors", "staff"))
        assert self.groups_of(userid) == {"site-editors", "site-staff"}

        self.authenticate(with_groups("editors"))

        assert self.groups_of(userid) == {"site-editors"}
        assert self.granted_by(PROVIDER, SUBJECT) == ("site-editors",)

    def test_dropping_the_claim_entirely_takes_everything_back(self):
        configure()
        userid = self.authenticate(with_groups("editors"))

        self.authenticate(CLAIMS)

        assert self.groups_of(userid) == set()
        assert self.granted_by(PROVIDER, SUBJECT) == ()

    # -- the fence -------------------------------------------------------

    def test_a_locally_granted_group_survives_a_login(self):
        """The whole point of recording the grant.

        An administrator put somebody in a group by hand. A provider that
        never granted it has no business taking it away.
        """
        configure()
        userid = self.authenticate(with_groups("editors"))
        api.group.add_user(groupname="granted-by-hand", username=userid)

        self.authenticate(with_groups("editors"))

        assert self.groups_of(userid) == {"site-editors", "granted-by-hand"}

    def test_a_locally_granted_group_survives_a_revocation(self):
        """Even on the login that strips the provider's own grant."""
        configure()
        userid = self.authenticate(with_groups("editors"))
        api.group.add_user(groupname="granted-by-hand", username=userid)

        self.authenticate(CLAIMS)

        assert self.groups_of(userid) == {"granted-by-hand"}

    def test_another_providers_grant_is_not_touched(self):
        """Two providers linked to one user, one group each.

        Each keeps its own record, so neither can revoke the other's. Two
        OIDC providers rather than one of each kind, because that is the
        case the design is actually for: two realms, or a staff issuer and a
        partner issuer, both `oidc-generic` and sharing nothing else.
        """
        configure(
            extra=[
                ProviderConfig(
                    provider_id=SECOND_PROVIDER,
                    driver_id="oidc-generic",
                    groupmap={"staff": "site-staff"},
                )
            ]
        )
        userid = self.authenticate(with_groups("editors"))
        # Linking is explicit: a second provider asserting the same address
        # does not adopt an account, which is the whole of this package's
        # auto-linking discipline.
        self.plugin.link(userid, SECOND_PROVIDER, SECOND_SUBJECT, CLAIMS)
        self.authenticate(with_groups("staff"), identity=SECOND_IDENTITY)
        assert self.groups_of(userid) == {"site-editors", "site-staff"}

        # Dex revokes its own. The other provider's grant is none of its
        # business.
        self.authenticate(CLAIMS)

        assert self.groups_of(userid) == {"site-staff"}
        assert self.granted_by(SECOND_PROVIDER, SECOND_SUBJECT) == ("site-staff",)

    def test_a_driver_that_declares_no_group_claim_grants_nothing(self):
        """A map stored against a provider whose driver has no groups -- by an
        import, or because the driver was swapped -- grants nothing rather
        than guessing at a claim name."""
        set_providers([
            ProviderConfig(
                provider_id=OTHER_PROVIDER,
                driver_id="github",
                groupmap={"editors": "site-editors"},
            )
        ])

        userid = self.authenticate(with_groups("editors"), identity=GITHUB_IDENTITY)

        assert self.groups_of(userid) == set()

    # -- the cases that must do nothing ----------------------------------

    def test_a_provider_with_no_map_touches_no_membership(self):
        """Not even to strip. An operator clearing a map is at least as likely
        to be rewriting it, and silently stripping every group it had granted
        on the next login is not a thing to do without being asked."""
        configure()
        userid = self.authenticate(with_groups("editors"))

        configure(groupmap={})
        self.authenticate(CLAIMS)

        assert self.groups_of(userid) == {"site-editors"}

    def test_a_group_missing_from_the_site_is_skipped(self):
        """A map is edited by hand, and a typo in it must not mint a group."""
        configure(groupmap={"editors": "typo-not-a-group"})

        userid = self.authenticate(with_groups("editors"))

        assert self.groups_of(userid) == set()
        assert api.group.get(groupname="typo-not-a-group") is None

    def test_a_group_missing_from_the_site_is_not_recorded_as_granted(self):
        """Otherwise the next login would try to take away something that was
        never given."""
        configure(groupmap={"editors": "typo-not-a-group"})
        self.authenticate(with_groups("editors"))

        assert self.granted_by(PROVIDER, SUBJECT) == ()

    def test_an_unchanged_claim_is_idempotent(self):
        configure()
        userid = self.authenticate(with_groups("editors"))

        self.authenticate(with_groups("editors"))

        assert self.groups_of(userid) == {"site-editors"}
        assert self.granted_by(PROVIDER, SUBJECT) == ("site-editors",)


class TestTheProviderMayBeDeniedGroupMembership(GroupMapCase):
    """``sync_groups`` off: sign in with the provider, decide groups here.

    A site may trust a provider to say *who somebody is* without trusting it
    to say *what they may do*, and group membership is usually what grants
    permissions. Today the only way to express that is to stop offering the
    provider.

    The switch defaults on, unlike every other one on that form, because it
    names behaviour that already exists: defaulting it off would stop group
    federation on every site that has it configured, silently, at the next
    login. That is what the first two tests here are for.
    """

    def test_the_field_defaults_on(self):
        """Asserted on the stored config rather than inferred from behaviour.

        Storing a provider and reading it back composes its config from the
        current schema, so every field's default is seeded -- which means a
        provider that never mentions this switch still carries it, and the
        shipped default is the only thing deciding what it says.
        """
        from pas.plugins.identity.core.controlpanel import get_provider

        configure()

        assert get_provider(PROVIDER).config["sync_groups"] is True

    def test_it_syncs_by_default(self):
        """And that default is the behaviour that already existed: switching
        this on was not allowed to require an edit to every site."""
        configure()

        assert self.groups_of(self.authenticate(with_groups("editors"))) == {
            "site-editors"
        }

    def test_switching_it_on_explicitly_syncs_too(self):
        configure(config={"sync_groups": True})

        assert self.groups_of(self.authenticate(with_groups("editors"))) == {
            "site-editors"
        }

    def test_switched_off_the_claim_grants_nothing(self):
        configure(config={"sync_groups": False})

        assert self.groups_of(self.authenticate(with_groups("editors"))) == set()

    def test_the_login_still_works(self):
        """The whole point: the provider is kept for signing in."""
        configure(config={"sync_groups": False})

        assert self.authenticate(with_groups("editors"))

    def test_nothing_is_recorded_as_granted(self):
        """So switching it back on later grants from a clean slate rather
        than trying to take away something never given."""
        configure(config={"sync_groups": False})

        self.authenticate(with_groups("editors"))

        assert self.granted_by(PROVIDER, SUBJECT) == ()

    def test_groups_granted_before_it_was_switched_off_stay(self):
        """Withdrawing them is a separate decision, and one nobody makes by
        editing a checkbox. Same rule as clearing the map."""
        configure()
        userid = self.authenticate(with_groups("editors"))
        assert self.groups_of(userid) == {"site-editors"}

        configure(config={"sync_groups": False})
        self.authenticate(with_groups())

        assert self.groups_of(userid) == {"site-editors"}

    def test_a_local_grant_is_untouched(self):
        """It was never this provider's to take, switch or no switch."""
        configure(config={"sync_groups": False})
        userid = self.authenticate(with_groups("editors"))
        api.group.add_user(groupname="granted-by-hand", username=userid)

        self.authenticate(with_groups("editors"))

        assert self.groups_of(userid) == {"granted-by-hand"}

    def test_a_second_provider_still_syncs(self):
        """The switch is per-provider: one refused is not all refused."""
        configure(
            config={"sync_groups": False},
            extra=[
                ProviderConfig(
                    provider_id=SECOND_PROVIDER,
                    driver_id="oidc-generic",
                    title="Partner",
                    groupmap=GROUPMAP,
                )
            ],
        )

        self.authenticate(with_groups("editors"))
        userid = self.authenticate(with_groups("staff"), identity=SECOND_IDENTITY)

        assert self.groups_of(userid) == {"site-staff"}
