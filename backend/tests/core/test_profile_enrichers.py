"""Profile enrichers: the extension point the property map cannot be.

The map carries a scalar from a provider document to one of four fields. An
add-on whose behavior adds a list field can express nothing through it --
which is not a gap to be widened but a deliberate refusal, since ``_scalar``
exists to stop an OIDC ``address`` object being written into somebody's
location as a repr. ``TestAListReachesTheProfile`` is the case the whole
feature is for, and it asserts both halves: that the map still cannot, and
that an enricher can.

The enrichers here are registered per test and unregistered afterwards. A
utility left in the global registry changes every later test in the run, and
the failure surfaces somewhere else entirely.
"""

from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.enrichment import enrich_profile
from pas.plugins.identity.core.enrichment import ENRICHER_VALUES_KEY
from pas.plugins.identity.core.enrichment import memory_for
from pas.plugins.identity.core.interfaces import IProfileEnricher
from plone import api
from zope.annotation.interfaces import IAnnotations
from zope.component import getGlobalSiteManager
from zope.interface import implementer

import pytest


#: Distinguishes "return None" from "no result configured", which matters
#: because returning None is one of the cases under test.
UNSET = object()


@implementer(IProfileEnricher)
class Recorder:
    """An enricher that writes what it is told and remembers being called."""

    def __init__(self, field="social_links", value=None, result=UNSET, boom=False):
        self.field = field
        self.value = value
        self.result = result
        self.boom = boom
        self.calls = []

    def enrich(self, profile, claims, provider, memory):
        self.calls.append((profile.getId(), dict(claims), provider, memory))
        if self.boom:
            raise RuntimeError("this enricher is broken")
        if self.value is not None:
            setattr(profile, self.field, self.value)
        return [self.field] if self.result is UNSET else self.result


@pytest.fixture
def register():
    """Register named enrichers for one test and take them away after.

    :returns: A callable taking ``(name, enricher)``.
    """
    gsm = getGlobalSiteManager()
    registered = []

    def _register(name, enricher):
        gsm.registerUtility(enricher, IProfileEnricher, name=name)
        registered.append((name, enricher))
        return enricher

    yield _register

    for name, enricher in registered:
        gsm.unregisterUtility(enricher, IProfileEnricher, name=name)


@pytest.fixture
def profile(portal):
    """A Profile to enrich.

    :param portal: The Plone site.
    :returns: The Profile.
    """
    return api.content.create(
        container=portal["identity-profiles"],
        type=PROFILE_PORTAL_TYPE,
        id="dana",
        userid="dana",
        login="dana",
        fullname="Dana Scully",
        emails=("dana@example.com",),
    )


#: A GitHub `/user` payload, trimmed to the keys that matter here.
CLAIMS = {
    "fullname": "Dana Scully",
    "email": "dana@example.com",
    "raw": {
        "login": "dana",
        "twitter_username": "dscully",
        "blog": "https://example.com/dana",
    },
}


class TestNothingInstalled:
    """The default, and the one every existing site is in."""

    def test_no_enrichers_changes_nothing(self, profile):
        assert enrich_profile(profile, CLAIMS) == []

    def test_and_writes_no_annotation(self, profile):
        """A mapping is created on first use by an enricher, not by the run."""
        enrich_profile(profile, CLAIMS)

        assert ENRICHER_VALUES_KEY not in IAnnotations(profile)


class TestWhatAnEnricherIsHanded:
    @pytest.fixture(autouse=True)
    def _setup(self, profile, register) -> None:
        self.profile = profile
        self.enricher = register("test.recorder", Recorder(value=["x"]))

    def test_it_gets_the_profile_and_the_claims(self):
        enrich_profile(self.profile, CLAIMS)

        userid, claims, _provider, _memory = self.enricher.calls[0]
        assert userid == "dana"
        assert claims["fullname"] == "Dana Scully"

    def test_the_raw_payload_is_the_providers_own(self):
        """The reason the hook is worth having: the whole document, not the
        five claims the package normalizes out of it."""
        enrich_profile(self.profile, CLAIMS)

        _userid, claims, _provider, _memory = self.enricher.calls[0]
        assert claims["raw"]["twitter_username"] == "dscully"

    def test_the_memory_is_private_to_the_name(self):
        enrich_profile(self.profile, CLAIMS)
        _userid, _claims, _provider, memory = self.enricher.calls[0]
        memory["seen"] = 1

        assert dict(memory_for(self.profile, "test.recorder")) == {"seen": 1}
        assert dict(memory_for(self.profile, "test.other")) == {}

    def test_the_memory_survives_the_next_login(self):
        enrich_profile(self.profile, CLAIMS)
        self.enricher.calls[0][3]["seen"] = 1

        enrich_profile(self.profile, CLAIMS)

        assert self.enricher.calls[1][3]["seen"] == 1


class TestAListReachesTheProfile:
    """The case the feature exists for.

    ``plonegovbr.socialmedia`` adds a list field through a behavior, and the
    data for it is in a GitHub payload that needs processing first.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, profile, register) -> None:
        self.profile = profile

        @implementer(IProfileEnricher)
        class SocialLinks:
            def enrich(self, profile, claims, provider, memory):
                raw = claims.get("raw") or {}
                links = []
                if handle := raw.get("twitter_username"):
                    links.append(f"https://twitter.com/{handle}")
                if blog := raw.get("blog"):
                    links.append(blog)
                if not links or memory.get("written") == links:
                    return []
                profile.social_links = links
                memory["written"] = list(links)
                return ["social_links"]

        register("test.social", SocialLinks())

    def test_the_property_map_cannot_carry_it(self):
        """The premise. ``_scalar`` reads a list as an absent claim, so no
        map and no payload shape gets a list onto a field."""
        from pas.plugins.identity.core.subscribers import _scalar

        assert _scalar(["https://twitter.com/dscully"]) == ""

    def test_the_enricher_can(self):
        changed = enrich_profile(self.profile, CLAIMS)

        assert changed == ["social_links"]
        assert self.profile.social_links == [
            "https://twitter.com/dscully",
            "https://example.com/dana",
        ]

    def test_a_second_login_writes_nothing_new(self):
        """What the private memory is for. Without it every login reasserts
        the list, and an entry the user deleted comes back for ever."""
        enrich_profile(self.profile, CLAIMS)

        assert enrich_profile(self.profile, CLAIMS) == []

    def test_an_empty_payload_is_survivable(self):
        """A magic-link confirmation and an address verification both fire
        with `raw` empty."""
        assert enrich_profile(self.profile, {"raw": {}}) == []


class TestOneBrokenEnricherDoesNotBreakTheLogin:
    """The rule the enrichment fetch already follows: an add-on that fails
    must not lock the site's users out, including whoever would remove it."""

    @pytest.fixture(autouse=True)
    def _setup(self, profile, register) -> None:
        self.profile = profile
        self.broken = register("test.a-broken", Recorder(boom=True))
        self.working = register(
            "test.b-working", Recorder(field="fullname", value="Dana K. Scully")
        )

    def test_the_run_survives_it(self):
        assert enrich_profile(self.profile, CLAIMS) == ["fullname"]

    def test_and_the_others_still_run(self):
        enrich_profile(self.profile, CLAIMS)

        assert self.profile.fullname == "Dana K. Scully"


class TestTheReturnValue:
    """It decides whether a modification event fires, so a careless one must
    not raise inside somebody's login."""

    @pytest.fixture(autouse=True)
    def _setup(self, profile, register) -> None:
        self.profile = profile

    @pytest.mark.parametrize(
        "result,expected",
        [
            (None, []),
            ([], []),
            (["a", "b"], ["a", "b"]),
            (("a",), ["a"]),
            # A bare field name is not a list of its characters.
            ("fullname", []),
            (42, []),
        ],
    )
    def test_it_is_read_defensively(self, register, result, expected):
        register("test.returns", Recorder(value=None, result=result))

        assert enrich_profile(self.profile, CLAIMS) == expected


class TestOrdering:
    @pytest.fixture(autouse=True)
    def _setup(self, profile, register) -> None:
        self.profile = profile
        self.order = []

        @implementer(IProfileEnricher)
        class Noting:
            def __init__(self, label, order):
                self.label = label
                self.order = order

            def enrich(self, profile, claims, provider, memory):
                self.order.append(self.label)
                return []

        register("test.zebra", Noting("zebra", self.order))
        register("test.alpha", Noting("alpha", self.order))

    def test_they_run_in_name_order(self):
        """A weak guarantee, deliberately: it makes a run reproducible without
        implying that enrichers may depend on each other."""
        enrich_profile(self.profile, CLAIMS)

        assert self.order == ["alpha", "zebra"]


class TestItRunsInTheLoginPath:
    """Registration and the runner both work and neither proves the hook is
    reached. Only driving the event does."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, register, acl_users) -> None:
        self.portal = portal
        self.enricher = register("test.login", Recorder(value=["seen"]))

    def test_a_federated_login_reaches_it(self):
        from pas.plugins.identity.core.events import ExternalIdentityAuthenticated
        from zope.event import notify

        api.user.create(
            email="dana@example.com",
            username="dana",
            password="dana-placeholder-password",
        )

        notify(
            ExternalIdentityAuthenticated(
                userid="dana",
                provider="github",
                subject="12345",
                claims=CLAIMS,
                is_new_user=False,
                is_new_identity=False,
            )
        )

        assert self.enricher.calls, "the login path never called the enricher"
        assert self.portal["identity-profiles"]["dana"].social_links == ["seen"]


class TestTheProviderIsHandedOver:
    """Without it an enricher has to sniff the payload for a key it hopes
    means something, which is how one fires on the wrong login."""

    @pytest.fixture(autouse=True)
    def _setup(self, profile, register) -> None:
        self.profile = profile
        self.enricher = register("test.provider", Recorder(value=["x"]))

    def test_it_is_none_when_there_is_no_provider(self):
        """A magic-link confirmation and an address verification both get
        here with nothing to attribute the claims to."""
        enrich_profile(self.profile, CLAIMS)

        _userid, _claims, provider, _memory = self.enricher.calls[0]
        assert provider is None

    def test_it_carries_the_driver_and_the_provider(self):
        from pas.plugins.identity.core.controlpanel import ProviderConfig

        config = ProviderConfig(provider_id="github-enterprise", driver_id="github")

        enrich_profile(self.profile, CLAIMS, config)

        _userid, _claims, provider, _memory = self.enricher.calls[0]
        assert provider.driver_id == "github"
        assert provider.provider_id == "github-enterprise"


class TestTwoDriversDoNotCrossFire:
    """The reason the provider is passed at all.

    A site running Google and GitHub has two payload shapes reaching the same
    enrichers. Each keys on ``driver_id`` and does nothing for the other, and
    neither has to guess from the keys it happens to find.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, profile, register) -> None:
        self.profile = profile
        self.ran = []

        @implementer(IProfileEnricher)
        class ForDriver:
            def __init__(self, driver_id, ran):
                self.driver_id = driver_id
                self.ran = ran

            def enrich(self, profile, claims, provider, memory):
                if provider is None or provider.driver_id != self.driver_id:
                    return []
                self.ran.append(self.driver_id)
                return []

        register("test.for-github", ForDriver("github", self.ran))
        register("test.for-google", ForDriver("google", self.ran))

    def _provider(self, driver_id):
        from pas.plugins.identity.core.controlpanel import ProviderConfig

        return ProviderConfig(provider_id=driver_id, driver_id=driver_id)

    def test_only_the_matching_one_runs(self):
        enrich_profile(self.profile, CLAIMS, self._provider("github"))

        assert self.ran == ["github"]

    def test_the_other_provider_runs_the_other_one(self):
        enrich_profile(self.profile, CLAIMS, self._provider("google"))

        assert self.ran == ["google"]

    def test_neither_runs_without_a_provider(self):
        enrich_profile(self.profile, CLAIMS, None)

        assert self.ran == []


class TestTheLoginPathResolvesTheProvider:
    """``_handle`` is handed a provider *id*; the enricher needs the config."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, register, acl_users) -> None:
        self.portal = portal
        self.enricher = register("test.resolve", Recorder(value=["seen"]))
        from pas.plugins.identity.core.controlpanel import ProviderConfig
        from pas.plugins.identity.core.controlpanel import set_providers

        set_providers([ProviderConfig(provider_id="gh", driver_id="github")])

    def test_a_login_hands_over_the_configured_provider(self):
        from pas.plugins.identity.core.events import ExternalIdentityAuthenticated
        from zope.event import notify

        api.user.create(
            email="dana@example.com",
            username="dana",
            password="dana-placeholder-password",
        )

        notify(
            ExternalIdentityAuthenticated(
                userid="dana",
                provider="gh",
                subject="12345",
                claims=CLAIMS,
                is_new_user=False,
                is_new_identity=False,
            )
        )

        _userid, _claims, provider, _memory = self.enricher.calls[0]
        assert provider is not None, "the login path passed no provider"
        assert provider.driver_id == "github"


class TestTwoEnrichersOnOneField:
    """Documented as a collision, resolved by name order, and warned about.

    Not prevented: the runner cannot know whether two add-ons writing one
    field is a mistake or a deliberate layering. What it can do is say so, so
    that a value which keeps changing between logins is traceable to the two
    things fighting over it.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, profile, register) -> None:
        self.profile = profile
        register("test.a-first", Recorder(field="fullname", value="First Writer"))
        register("test.b-second", Recorder(field="fullname", value="Second Writer"))

    def test_both_are_reported(self):
        assert enrich_profile(self.profile, CLAIMS) == ["fullname", "fullname"]

    def test_the_later_name_wins(self):
        enrich_profile(self.profile, CLAIMS)

        assert self.profile.fullname == "Second Writer"

    def test_the_collision_is_logged(self, caplog):
        import logging

        with caplog.at_level(logging.WARNING):
            enrich_profile(self.profile, CLAIMS)

        assert "both wrote" in caplog.text
        assert "test.a-first" in caplog.text
        assert "test.b-second" in caplog.text


class TestTheDocumentedDispatchPattern:
    """The example in ``docs/how-to-guides/write-a-profile-enricher.md``.

    Shipped code that nobody runs is a claim rather than an example, and this
    one has two edges worth holding still: ``getattr`` needs its default, or a
    driver with no handler raises on every login, and a handler returns field
    names rather than the memory it just wrote to.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, profile, register) -> None:
        self.profile = profile

        @implementer(IProfileEnricher)
        class SocialLinks:
            def enrich(self, profile, claims, provider, memory):
                if provider is None:
                    return []
                handler = getattr(self, f"enrich_{provider.driver_id}", None)
                if handler is None:
                    return []
                return handler(profile, claims, memory)

            def enrich_github(self, profile, claims, memory):
                raw = claims.get("raw") or {}
                links = []
                if handle := raw.get("twitter_username"):
                    links.append(f"https://twitter.com/{handle}")
                if blog := raw.get("blog"):
                    links.append(blog)
                if not links or memory.get("written") == links:
                    return []
                profile.social_links = links
                memory["written"] = list(links)
                return ["social_links"]

        register("test.dispatch", SocialLinks())

    def _provider(self, driver_id):
        from pas.plugins.identity.core.controlpanel import ProviderConfig

        return ProviderConfig(provider_id=driver_id, driver_id=driver_id)

    def test_the_handled_driver_is_dispatched_to(self):
        changed = enrich_profile(self.profile, CLAIMS, self._provider("github"))

        assert changed == ["social_links"]
        assert self.profile.social_links == [
            "https://twitter.com/dscully",
            "https://example.com/dana",
        ]

    def test_an_unhandled_driver_does_nothing_and_does_not_raise(self):
        """Without the third argument to ``getattr`` this is an AttributeError
        on every Google login, caught by the runner and logged for ever."""
        assert enrich_profile(self.profile, CLAIMS, self._provider("google")) == []

    def test_and_nothing_is_logged_for_it(self, caplog):
        """The point of the default: not handling a driver is not a failure."""
        import logging

        with caplog.at_level(logging.WARNING):
            enrich_profile(self.profile, CLAIMS, self._provider("google"))

        assert caplog.text == ""

    def test_no_provider_dispatches_nowhere(self):
        assert enrich_profile(self.profile, CLAIMS, None) == []

    def test_the_handler_reports_the_field_not_the_memory(self):
        """Returning ``memory`` reads as a changed field called `written`."""
        changed = enrich_profile(self.profile, CLAIMS, self._provider("github"))

        assert changed == ["social_links"]
        assert "written" not in changed
