"""Integration tests for ``@identities``."""

from .. import body
from . import DEX_METADATA
from . import USERINFO
from pas.plugins.identity.core.audit import LINK_COLLISION
from pas.plugins.identity.core.audit import LINK_REFUSED
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.events import IIdentityLinked
from pas.plugins.identity.core.events import IIdentityUnlinked
from pas.plugins.identity.core.flows import SESSION_KEY
from pas.plugins.identity.core.flows.session import COOKIE_NAME
from pas.plugins.identity.core.flows.session import decode
from pas.plugins.identity.core.interfaces import FlowError
from pas.plugins.identity.core.services.callback.post import IdentityCallback
from pas.plugins.identity.core.services.identities.delete import IdentitiesDelete
from pas.plugins.identity.core.services.identities.get import IdentitiesGet
from pas.plugins.identity.core.services.identities.post import IdentitiesPost
from plone import api
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import TEST_USER_NAME
from urllib.parse import parse_qs
from urllib.parse import urlparse

import pytest


#: A second provider, so there is something to link *to*.
SECOND_PROVIDER = {
    "id": "dex-second",
    "driver": "oidc-generic",
    "title": "Dex (second)",
    "enabled": True,
    "config": {
        "issuer": "http://dex:5556/dex",
        "client_id": "plone-second",
        "client_secret": "plone-second-secret",
        "scope": ["openid", "email", "profile"],
    },
}

#: What the second provider's userinfo answers -- a different subject, the
#: same human.
SECOND_USERINFO = {**USERINFO, "sub": "CgVlcmljbxIGc2Vjb25k"}


@pytest.fixture
def two_providers(portal, configured):
    """Add a second enabled provider alongside the Dex fixture.

    :param portal: The Plone site.
    :param configured: The base provider configuration.
    """
    set_providers([*get_providers(), ProviderConfig.deserialize(SECOND_PROVIDER)])


class IdentitiesCase:
    """The three shapes of the service, driven directly."""

    def listing(self) -> dict:
        """GET the caller's identities.

        :returns: The service's reply.
        """
        return IdentitiesGet(self.portal, self.request).reply()

    def start_link(self, **payload) -> dict:
        """POST a linking-flow start.

        :param payload: The JSON body.
        :returns: The service's reply.
        """
        body(self.request, payload)
        return IdentitiesPost(self.portal, self.request).reply()

    def unlink(self, *segments) -> dict:
        """DELETE one identity.

        :param segments: Path segments after ``@identities``.
        :returns: The service's reply.
        """
        view = IdentitiesDelete(self.portal, self.request)
        for segment in segments:
            view.publishTraverse(self.request, segment)
        return view.reply()

    def status(self) -> int:
        """Return the status the service answered with.

        :returns: The HTTP status.
        """
        return self.request.response.getStatus()

    def plugin(self):
        """Return the identity plugin.

        :returns: The plugin.
        """
        return api.portal.get_tool("acl_users")["identity"]


class TestListing(IdentitiesCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, member, configured) -> None:
        self.portal = portal
        self.request = request_
        self.member = member

    def test_anonymous_is_refused(self):
        """These are *your* identities; there is no anonymous answer."""
        logout()

        result = self.listing()

        assert self.status() == 401
        assert result["error"]["type"] == "Not authenticated"

    def test_empty_for_a_password_user(self):
        """A member who never used a provider has nothing linked."""
        assert self.listing()["items"] == []

    def test_lists_a_linked_identity(self):
        """What was linked comes back, with its provider's label."""
        self.plugin().link(self.member, "dex", USERINFO["sub"], {})

        item = self.listing()["items"][0]

        assert item["provider"] == "dex"
        assert item["subject"] == USERINFO["sub"]
        assert item["title"] == "Dex"
        assert item["@id"].endswith(f"/@identities/dex/{USERINFO['sub']}")

    def test_reports_whether_unlinking_is_safe(self):
        """The lockout guard is surfaced, so the UI can grey the button out
        rather than let the user discover the refusal by pressing it."""
        self.plugin().link(self.member, "dex", USERINFO["sub"], {})

        # A member with a real password can always unlink.
        assert self.listing()["items"][0]["can_unlink"] is True

    def test_offers_the_login_providers_component(self):
        """Unexpanded, a caller still learns where to look."""
        result = self.listing()

        component = result["@components"]["login-providers"]
        assert component["@id"].endswith("/@login-providers")
        assert "items" not in component

    def test_expands_the_login_providers(self):
        """The page lists what is linked *and* what could be linked next, so
        asking for both in one request is the whole point of the component."""
        self.request.form["expand"] = "login-providers"

        component = self.listing()["@components"]["login-providers"]

        assert [item["id"] for item in component["items"]] == ["dex"]

    def test_the_expansion_is_the_endpoint_s_own_answer(self):
        """Two renderings of the same buttons must not be able to differ."""
        from pas.plugins.identity.core.services.login import provider_listing

        self.request.form["expand"] = "login-providers"

        assert self.listing()["@components"]["login-providers"] == provider_listing(
            self.portal
        )

    def test_shows_only_your_own(self):
        """Somebody else's identity is not yours to see."""
        self.plugin().link("another-userid", "dex", "someone-elses-subject", {})

        assert self.listing()["items"] == []


class TestAvailableProviders(IdentitiesCase):
    """``available`` is what this caller could still attach to their account.

    Availability rather than login visibility: a provider an operator has
    taken off the login screen is still one an existing user may link.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, member, configured) -> None:
        self.portal = portal
        self.request = request_
        self.member = member

    def _ids(self) -> list[str]:
        """Return the ids offered to this caller.

        :returns: Provider ids.
        """
        return [item["id"] for item in self.listing()["available"]]

    def test_offers_an_unlinked_provider(self):
        """The ordinary case."""
        assert "dex" in self._ids()

    def test_does_not_offer_one_already_linked(self):
        """Offering it again is offering something that cannot succeed: the
        store is keyed on provider and subject, and this user already has a
        subject there."""
        self.plugin().link(self.member, "dex", USERINFO["sub"], {})

        assert "dex" not in self._ids()

    def test_offers_a_provider_hidden_from_the_login_screen(self):
        """The point of ``show_in_login`` being its own setting."""
        set_providers([
            *get_providers(),
            ProviderConfig.deserialize({**SECOND_PROVIDER, "show_in_login": False}),
        ])

        assert "dex-second" in self._ids()

    def test_does_not_offer_a_disabled_provider(self):
        """Disabled means unusable, not merely unadvertised."""
        set_providers([
            *get_providers(),
            ProviderConfig.deserialize({**SECOND_PROVIDER, "enabled": False}),
        ])

        assert "dex-second" not in self._ids()

    def test_does_not_offer_the_email_provider(self):
        """Magic link takes no form here: the addresses this site will verify
        are the ones on your profile, not one typed into a box."""
        from . import EMAIL_PROVIDER_RECORD

        set_providers([
            *get_providers(),
            ProviderConfig.deserialize(EMAIL_PROVIDER_RECORD),
        ])

        assert "email" not in self._ids()

    def test_a_linked_email_identity_is_still_listed(self):
        """Seeing what is attached to your account is a different question
        from being offered another one."""
        from . import ADDRESS
        from . import EMAIL_PROVIDER_RECORD

        set_providers([
            *get_providers(),
            ProviderConfig.deserialize(EMAIL_PROVIDER_RECORD),
        ])
        self.plugin().link(self.member, "email", ADDRESS, {})

        assert "email" in [item["provider"] for item in self.listing()["items"]]

    def test_an_entry_carries_the_style(self):
        """The identities page draws the same buttons the login page does."""
        item = next(i for i in self.listing()["available"] if i["id"] == "dex")

        assert set(item) >= {"icon", "background_color", "foreground_color"}


class TestStartLinking(IdentitiesCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, member, two_providers, stub_metadata) -> None:
        self.portal = portal
        self.request = request_
        self.member = member
        self.stub_metadata = stub_metadata

    def test_anonymous_cannot_start(self):
        """A linking flow may not even be *started* anonymously."""
        logout()

        result = self.start_link(provider="dex-second")

        assert self.status() == 401
        assert result["error"]["type"] == "Not authenticated"

    def test_returns_an_authorize_url(self):
        """The caller gets somewhere to send the browser."""
        self.stub_metadata(DEX_METADATA)

        result = self.start_link(provider="dex-second")

        assert result["authorize_url"].startswith("http://dex:5556/dex/auth")

    def test_attempt_remembers_whose_account(self):
        """The attempt records who it is linking to."""
        self.stub_metadata(DEX_METADATA)

        self.start_link(provider="dex-second")

        stored = decode(self.request.response.cookies[COOKIE_NAME]["value"])
        attempt = next(iter(stored[SESSION_KEY].values()))
        assert attempt["link_for"] == self.member

    def test_provider_is_required(self):
        """A link to nothing in particular is not a request."""
        self.start_link()

        assert self.status() == 400

    def test_unknown_provider_is_refused(self):
        """As everywhere else, unknown and disabled read the same."""
        result = self.start_link(provider="nope")

        assert self.status() == 404
        assert result["error"]["type"] == "Unknown provider"

    def test_unreachable_provider_is_a_bad_gateway(self):
        """A provider that is down is the provider's fault, not the caller's,
        and the user should be told to try again rather than shown a stack."""
        self.stub_metadata(FlowError("dex-second: could not fetch discovery"))

        result = self.start_link(provider="dex-second")

        assert self.status() == 502
        assert result["error"]["type"] == "Provider unavailable"


class TestUnlinking(IdentitiesCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, member, configured, recorded_events) -> None:
        self.portal = portal
        self.request = request_
        self.member = member
        self.recorded_events = recorded_events

    def link_one(self) -> None:
        """Link one identity to the logged-in member."""
        self.plugin().link(self.member, "dex", USERINFO["sub"], {})

    def test_anonymous_is_refused(self):
        """Unlinking is an authenticated act."""
        logout()

        self.unlink("dex", USERINFO["sub"])

        assert self.status() == 401

    def test_unlink_succeeds(self):
        """The identity is gone from the store."""
        self.link_one()

        self.unlink("dex", USERINFO["sub"])

        assert self.plugin().store.userid_for("dex", USERINFO["sub"]) is None

    def test_unlink_fires_the_event(self):
        """Subscribers -- the audit log among them -- need to hear about it."""
        self.link_one()

        self.unlink("dex", USERINFO["sub"])

        unlinked = [e for e in self.recorded_events if IIdentityUnlinked.providedBy(e)]
        assert len(unlinked) == 1
        assert unlinked[0].provider == "dex"
        assert unlinked[0].subject == USERINFO["sub"]

    def test_someone_elses_identity_is_not_found(self):
        """Whose account an identity belongs to is not worth probing for, so
        this reads exactly like an identity that does not exist."""
        self.plugin().link("another-userid", "dex", "not-yours", {})

        self.unlink("dex", "not-yours")

        assert self.status() == 404

    def test_unknown_identity_is_not_found(self):
        """And so does one nobody ever linked."""
        self.unlink("dex", "never-linked")

        assert self.status() == 404

    def test_incomplete_path_is_refused(self):
        """``@identities/dex`` does not name an identity."""
        self.link_one()

        self.unlink("dex")

        assert self.status() == 400

    def test_last_identity_is_refused(self):
        """Unlinking the last way in would lock the user out."""
        plugin = self.plugin()
        userid, _ = plugin.authenticateCredentials({
            "extractor": "pas.plugins.identity",
            "provider": "dex",
            "subject": USERINFO["sub"],
            "claims": {},
        })
        login(self.portal, TEST_USER_NAME)
        # Become that externally-created user for the duration of the call.
        with api.env.adopt_user(username=userid):
            result = self.unlink("dex", USERINFO["sub"])

        assert self.status() == 409
        assert result["error"]["type"] == "Would lock you out"
        assert plugin.store.userid_for("dex", USERINFO["sub"]) == userid


class TestLinkingCallback(IdentitiesCase):
    """Completing a linking flow, through the real callback."""

    @pytest.fixture(autouse=True)
    def _setup(
        self,
        portal,
        request_,
        member,
        two_providers,
        stub_metadata,
        stub_provider,
        recorded_events,
        log,
    ) -> None:
        self.portal = portal
        self.request = request_
        self.member = member
        self.recorded_events = recorded_events
        self.log = log
        stub_metadata(DEX_METADATA)
        stub_provider(SECOND_USERINFO)
        result = self.start_link(provider="dex-second")
        request_.cookies[COOKIE_NAME] = request_.response.cookies[COOKIE_NAME]["value"]
        self.flow = parse_qs(urlparse(result["authorize_url"]).query)["state"][0]

    def callback(self, state: str) -> dict:
        """POST the provider's answer back.

        :param state: The state to send.
        :returns: The service's reply.
        """
        body(self.request, {"provider": "dex-second", "code": "c", "state": state})
        return IdentityCallback(self.portal, self.request).reply()

    def test_link_succeeds(self):
        """Both identities now resolve to the one userid."""
        result = self.callback(self.flow)

        assert result["linked"]["provider"] == "dex-second"
        assert (
            self.plugin().store.userid_for("dex-second", SECOND_USERINFO["sub"])
            == self.member
        )

    def test_link_fires_the_event(self):
        """``IdentityLinked`` carries the userid, provider and subject."""
        self.callback(self.flow)

        linked = [e for e in self.recorded_events if IIdentityLinked.providedBy(e)]
        assert len(linked) == 1
        assert linked[0].userid == self.member
        assert linked[0].provider == "dex-second"
        assert linked[0].subject == SECOND_USERINFO["sub"]

    def test_no_second_account_is_created(self):
        """Linking must not mint a userid -- that is the whole point."""
        self.callback(self.flow)

        plugin = self.plugin()
        assert len(plugin.store.identities_for(self.member)) == 1
        assert (
            plugin.store.userid_for("dex-second", SECOND_USERINFO["sub"]) == self.member
        )

    def test_anonymous_completion_is_refused(self):
        """A linking flow must be completed by the session that started
        it. An attacker who gets a victim to finish theirs would otherwise
        attach their own provider account to the victim's login."""
        logout()

        result = self.callback(self.flow)

        assert self.status() == 403
        assert result["error"]["type"] == "Link refused"
        assert self.log.entries()[0].event == LINK_REFUSED

    def test_completion_by_another_user_is_refused(self):
        """Same rule when somebody is logged in, just not the right somebody."""
        login(self.portal, TEST_USER_NAME)

        self.callback(self.flow)

        assert self.status() == 403
        assert self.log.entries()[0].event == LINK_REFUSED

    def test_collision_is_a_hard_error(self):
        """An identity owned by someone else is never re-pointed."""
        plugin = self.plugin()
        plugin.store.add("dex-second", SECOND_USERINFO["sub"], "someone-else", {})

        result = self.callback(self.flow)

        assert self.status() == 409
        assert result["error"]["type"] == "Identity already linked"
        assert plugin.store.userid_for("dex-second", SECOND_USERINFO["sub"]) == (
            "someone-else"
        )

    def test_collision_is_audited(self):
        """And it leaves a trace naming the subject that collided."""
        self.plugin().store.add(
            "dex-second", SECOND_USERINFO["sub"], "someone-else", {}
        )

        self.callback(self.flow)

        entry = self.log.entries()[0]
        assert entry.event == LINK_COLLISION
        assert entry.success is False
        assert entry.detail["subject"] == SECOND_USERINFO["sub"]
