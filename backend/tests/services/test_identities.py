"""Integration tests for ``@identities`` (Gate 2, S1/S3/S4/I3)."""

from . import DEX_METADATA
from . import USERINFO
from .conftest import body
from pas.plugins.identity.core.audit import LINK_COLLISION
from pas.plugins.identity.core.audit import LINK_REFUSED
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.events import IIdentityLinked
from pas.plugins.identity.core.events import IIdentityUnlinked
from pas.plugins.identity.core.flows.session import COOKIE_NAME
from pas.plugins.identity.core.services.callback import IdentityCallback
from pas.plugins.identity.core.services.identities import IdentitiesDelete
from pas.plugins.identity.core.services.identities import IdentitiesGet
from pas.plugins.identity.core.services.identities import IdentitiesPost
from plone import api
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import TEST_USER_NAME
from urllib.parse import parse_qs
from urllib.parse import urlparse
from zope.component import adapter
from zope.component import getGlobalSiteManager
from zope.interface import Interface

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
        "scope": "openid email profile",
    },
}

#: What the second provider's userinfo answers -- a different subject, the
#: same human.
SECOND_USERINFO = {**USERINFO, "sub": "CgVlcmljbxIGc2Vjb25k"}


@pytest.fixture()
def two_providers(portal, configured):
    """Add a second enabled provider alongside the Dex fixture."""
    set_providers([*get_providers(), ProviderConfig.deserialize(SECOND_PROVIDER)])


@pytest.fixture()
def member(portal):
    """Create and log in an ordinary Plone member."""
    with api.env.adopt_roles(["Manager"]):
        user = api.user.create(
            email="member@plone.org",
            username="member",
            password="s3cr3t-member",
        )
    login(portal, "member")
    return user.getId()


@pytest.fixture()
def recorded_events():
    """Record every event fired during a test."""
    events = []

    @adapter(Interface)
    def recorder(event):
        events.append(event)

    gsm = getGlobalSiteManager()
    gsm.registerHandler(recorder)
    yield events
    gsm.unregisterHandler(recorder)


def listing(portal, request_) -> dict:
    """GET the caller's identities.

    :param portal: The Plone site.
    :param request_: The current request.
    :returns: The service's reply.
    """
    return IdentitiesGet(portal, request_).reply()


def start_link(portal, request_, **payload) -> dict:
    """POST a linking-flow start.

    :param portal: The Plone site.
    :param request_: The current request.
    :param payload: The JSON body.
    :returns: The service's reply.
    """
    body(request_, payload)
    return IdentitiesPost(portal, request_).reply()


def unlink(portal, request_, *segments) -> dict:
    """DELETE one identity.

    :param portal: The Plone site.
    :param request_: The current request.
    :param segments: Path segments after ``@identities``.
    :returns: The service's reply.
    """
    view = IdentitiesDelete(portal, request_)
    for segment in segments:
        view.publishTraverse(request_, segment)
    return view.reply()


class TestListing:
    def test_anonymous_is_refused(self, portal, request_, configured):
        """These are *your* identities; there is no anonymous answer."""
        logout()

        result = listing(portal, request_)

        assert request_.response.getStatus() == 401
        assert result["error"]["type"] == "Not authenticated"

    def test_empty_for_a_password_user(self, portal, request_, member, configured):
        """A member who never used a provider has nothing linked."""
        assert listing(portal, request_)["items"] == []

    def test_lists_a_linked_identity(self, portal, request_, member, configured):
        """What was linked comes back, with its provider's label."""
        api.portal.get_tool("acl_users")["identity"].link(
            member, "dex", USERINFO["sub"], {}
        )

        item = listing(portal, request_)["items"][0]

        assert item["provider"] == "dex"
        assert item["subject"] == USERINFO["sub"]
        assert item["title"] == "Dex"
        assert item["@id"].endswith(f"/@identities/dex/{USERINFO['sub']}")

    def test_reports_whether_unlinking_is_safe(
        self, portal, request_, member, configured
    ):
        """S4 surfaced, so the UI can grey the button out rather than let the
        user discover the refusal by pressing it."""
        plugin = api.portal.get_tool("acl_users")["identity"]
        plugin.link(member, "dex", USERINFO["sub"], {})

        # A member with a real password can always unlink.
        assert listing(portal, request_)["items"][0]["can_unlink"] is True

    def test_shows_only_your_own(self, portal, request_, member, configured):
        """Somebody else's identity is not yours to see."""
        api.portal.get_tool("acl_users")["identity"].link(
            "another-userid", "dex", "someone-elses-subject", {}
        )

        assert listing(portal, request_)["items"] == []


class TestStartLinking:
    def test_anonymous_cannot_start(self, portal, request_, two_providers):
        """S1 -- a linking flow may not even be *started* anonymously."""
        logout()

        result = start_link(portal, request_, provider="dex-second")

        assert request_.response.getStatus() == 401
        assert result["error"]["type"] == "Not authenticated"

    def test_returns_an_authorize_url(
        self, portal, request_, member, two_providers, stub_metadata
    ):
        """The caller gets somewhere to send the browser."""
        stub_metadata(DEX_METADATA)

        result = start_link(portal, request_, provider="dex-second")

        assert result["authorize_url"].startswith("http://dex:5556/dex/auth")

    def test_attempt_remembers_whose_account(
        self, portal, request_, member, two_providers, stub_metadata
    ):
        """S1 -- the attempt records who it is linking to."""
        from pas.plugins.identity.core.flows import SESSION_KEY
        from pas.plugins.identity.core.flows.session import decode

        stub_metadata(DEX_METADATA)

        start_link(portal, request_, provider="dex-second")

        stored = decode(request_.response.cookies[COOKIE_NAME]["value"])
        attempt = next(iter(stored[SESSION_KEY].values()))
        assert attempt["link_for"] == member

    def test_provider_is_required(self, portal, request_, member, two_providers):
        """A link to nothing in particular is not a request."""
        start_link(portal, request_)

        assert request_.response.getStatus() == 400

    def test_unknown_provider_is_refused(self, portal, request_, member, two_providers):
        """As everywhere else, unknown and disabled read the same."""
        result = start_link(portal, request_, provider="nope")

        assert request_.response.getStatus() == 404
        assert result["error"]["type"] == "Unknown provider"

    def test_unreachable_provider_is_a_bad_gateway(
        self, portal, request_, member, two_providers, stub_metadata
    ):
        """A provider that is down is the provider's fault, not the caller's,
        and the user should be told to try again rather than shown a stack."""
        from pas.plugins.identity.core.interfaces import FlowError

        stub_metadata(FlowError("dex-second: could not fetch discovery"))

        result = start_link(portal, request_, provider="dex-second")

        assert request_.response.getStatus() == 502
        assert result["error"]["type"] == "Provider unavailable"


class TestUnlinking:
    @pytest.fixture()
    def linked(self, portal, member, configured):
        """Link one identity to the logged-in member."""
        api.portal.get_tool("acl_users")["identity"].link(
            member, "dex", USERINFO["sub"], {}
        )
        return member

    def test_anonymous_is_refused(self, portal, request_, configured):
        """Unlinking is an authenticated act."""
        logout()

        unlink(portal, request_, "dex", USERINFO["sub"])

        assert request_.response.getStatus() == 401

    def test_unlink_succeeds(self, portal, request_, linked):
        """The identity is gone from the store."""
        unlink(portal, request_, "dex", USERINFO["sub"])

        plugin = api.portal.get_tool("acl_users")["identity"]
        assert plugin.store.userid_for("dex", USERINFO["sub"]) is None

    def test_unlink_fires_the_event(self, portal, request_, linked, recorded_events):
        """Subscribers -- the audit log among them -- need to hear about it."""
        unlink(portal, request_, "dex", USERINFO["sub"])

        unlinked = [e for e in recorded_events if IIdentityUnlinked.providedBy(e)]
        assert len(unlinked) == 1
        assert unlinked[0].provider == "dex"
        assert unlinked[0].subject == USERINFO["sub"]

    def test_someone_elses_identity_is_not_found(self, portal, request_, member):
        """Whose account an identity belongs to is not worth probing for, so
        this reads exactly like an identity that does not exist."""
        api.portal.get_tool("acl_users")["identity"].link(
            "another-userid", "dex", "not-yours", {}
        )

        unlink(portal, request_, "dex", "not-yours")

        assert request_.response.getStatus() == 404

    def test_unknown_identity_is_not_found(self, portal, request_, member):
        """And so does one nobody ever linked."""
        unlink(portal, request_, "dex", "never-linked")

        assert request_.response.getStatus() == 404

    def test_incomplete_path_is_refused(self, portal, request_, linked):
        """``@identities/dex`` does not name an identity."""
        unlink(portal, request_, "dex")

        assert request_.response.getStatus() == 400

    def test_last_identity_is_refused(self, portal, request_, configured):
        """S4 -- unlinking the last way in would lock the user out."""
        plugin = api.portal.get_tool("acl_users")["identity"]
        userid, _ = plugin.authenticateCredentials({
            "extractor": "pas.plugins.identity",
            "provider": "dex",
            "subject": USERINFO["sub"],
            "claims": {},
        })
        login(portal, TEST_USER_NAME)
        # Become that externally-created user for the duration of the call.
        with api.env.adopt_user(username=userid):
            result = unlink(portal, request_, "dex", USERINFO["sub"])

        assert request_.response.getStatus() == 409
        assert result["error"]["type"] == "Would lock you out"
        assert plugin.store.userid_for("dex", USERINFO["sub"]) == userid


class TestLinkingCallback:
    """Completing a linking flow (S1/S3/I3), through the real callback."""

    @pytest.fixture()
    def flow(
        self, portal, request_, member, two_providers, stub_metadata, stub_provider
    ):
        """Start a linking flow as the member and return its state."""
        stub_metadata(DEX_METADATA)
        stub_provider(SECOND_USERINFO)
        result = start_link(portal, request_, provider="dex-second")
        request_.cookies[COOKIE_NAME] = request_.response.cookies[COOKIE_NAME]["value"]
        return parse_qs(urlparse(result["authorize_url"]).query)["state"][0]

    def callback(self, portal, request_, state: str) -> dict:
        """POST the provider's answer back.

        :param portal: The Plone site.
        :param request_: The current request.
        :param state: The state to send.
        :returns: The service's reply.
        """
        body(request_, {"provider": "dex-second", "code": "c", "state": state})
        return IdentityCallback(portal, request_).reply()

    def test_link_succeeds(self, portal, request_, member, flow):
        """Both identities now resolve to the one userid."""
        result = self.callback(portal, request_, flow)

        assert result["linked"]["provider"] == "dex-second"
        plugin = api.portal.get_tool("acl_users")["identity"]
        assert plugin.store.userid_for("dex-second", SECOND_USERINFO["sub"]) == member

    def test_link_fires_the_event(
        self, portal, request_, member, flow, recorded_events
    ):
        """``IdentityLinked`` carries the userid, provider and subject."""
        self.callback(portal, request_, flow)

        linked = [e for e in recorded_events if IIdentityLinked.providedBy(e)]
        assert len(linked) == 1
        assert linked[0].userid == member
        assert linked[0].provider == "dex-second"
        assert linked[0].subject == SECOND_USERINFO["sub"]

    def test_no_second_account_is_created(self, portal, request_, member, flow):
        """Linking must not mint a userid -- that is the whole point."""
        self.callback(portal, request_, flow)

        plugin = api.portal.get_tool("acl_users")["identity"]
        assert len(plugin.store.identities_for(member)) == 1
        assert plugin.store.userid_for("dex-second", SECOND_USERINFO["sub"]) == member

    def test_anonymous_completion_is_refused(self, portal, request_, flow, log):
        """S1 -- a linking flow must be completed by the session that started
        it. An attacker who gets a victim to finish theirs would otherwise
        attach their own provider account to the victim's login."""
        logout()

        result = self.callback(portal, request_, flow)

        assert request_.response.getStatus() == 403
        assert result["error"]["type"] == "Link refused"
        assert log.entries()[0].event == LINK_REFUSED

    def test_completion_by_another_user_is_refused(self, portal, request_, flow, log):
        """Same rule when somebody is logged in, just not the right somebody."""
        login(portal, TEST_USER_NAME)

        self.callback(portal, request_, flow)

        assert request_.response.getStatus() == 403
        assert log.entries()[0].event == LINK_REFUSED

    def test_collision_is_a_hard_error(self, portal, request_, member, flow, log):
        """I3/S3 -- an identity owned by someone else is never re-pointed."""
        plugin = api.portal.get_tool("acl_users")["identity"]
        plugin.store.add("dex-second", SECOND_USERINFO["sub"], "someone-else", {})

        result = self.callback(portal, request_, flow)

        assert request_.response.getStatus() == 409
        assert result["error"]["type"] == "Identity already linked"
        assert plugin.store.userid_for("dex-second", SECOND_USERINFO["sub"]) == (
            "someone-else"
        )

    def test_collision_is_audited(self, portal, request_, member, flow, log):
        """S3 -- and it leaves a trace naming the subject that collided."""
        plugin = api.portal.get_tool("acl_users")["identity"]
        plugin.store.add("dex-second", SECOND_USERINFO["sub"], "someone-else", {})

        self.callback(portal, request_, flow)

        entry = log.entries()[0]
        assert entry.event == LINK_COLLISION
        assert entry.success is False
        assert entry.detail["subject"] == SECOND_USERINFO["sub"]
