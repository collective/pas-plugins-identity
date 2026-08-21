"""Integration tests for ``@identity-callback`` (Gate 1, S1/I1/I3).

The provider's two network calls are stubbed; everything else is the real
thing -- the real flow manager, the real signed cookie, the real PAS plugin,
the real JWT plugin. What is asserted is what a Volto login actually needs:
a token, a stable userid, and a flat refusal for every S1 negative.
"""

from . import DEX_METADATA
from . import USERINFO
from .conftest import body
from authlib.integrations.requests_client import OAuth2Session
from pas.plugins.identity.core.flows import session as flow_session
from pas.plugins.identity.core.flows.session import COOKIE_NAME
from pas.plugins.identity.core.services.callback import IdentityCallback
from pas.plugins.identity.core.services.login import LoginProviders
from plone import api
from urllib.parse import parse_qs
from urllib.parse import urlparse

import pytest


class StubResponse:
    """The part of ``requests.Response`` the userinfo call touches."""

    def __init__(self, payload: dict) -> None:
        """Hold a canned payload.

        :param payload: What :meth:`json` returns.
        """
        self.payload = payload

    def raise_for_status(self) -> None:
        """Succeed: this stub only ever stands in for a healthy provider."""

    def json(self) -> dict:
        """Return the canned payload.

        :returns: The payload.
        """
        return dict(self.payload)


@pytest.fixture()
def stub_provider(monkeypatch):
    """Replace the provider's token and userinfo endpoints.

    :returns: Callable taking the userinfo payload to answer with.
    """

    def install(userinfo: dict | None = None):
        """Install the stub.

        :param userinfo: What the userinfo endpoint answers.
        """
        payload = USERINFO if userinfo is None else userinfo

        class StubSession(OAuth2Session):
            """authlib's client with the network calls short-circuited."""

            def fetch_token(self, url: str, **kwargs) -> dict:
                """Answer the token request.

                :param url: Ignored.
                :param kwargs: Ignored.
                :returns: A token with no ``id_token``, so the flow falls
                    back to userinfo.
                """
                return {"access_token": "at", "token_type": "Bearer"}

            def get(self, url: str, **kwargs) -> StubResponse:
                """Answer the userinfo request.

                :param url: Ignored.
                :param kwargs: Ignored.
                :returns: The canned response.
                """
                return StubResponse(payload)

        monkeypatch.setattr(flow_session, "OAuth2Session", StubSession, raising=False)
        from pas.plugins.identity.core import flows

        monkeypatch.setattr(flows, "OAuth2Session", StubSession)

    return install


def start_flow(portal, request_) -> str:
    """Start a real flow and hand the cookie back to the browser.

    :param portal: The Plone site.
    :param request_: The current request.
    :returns: The ``state`` the provider would echo back.
    """
    view = LoginProviders(portal, request_)
    view.publishTraverse(request_, "dex")
    result = view.reply()
    state = parse_qs(urlparse(result["authorize_url"]).query)["state"][0]
    request_.cookies[COOKIE_NAME] = request_.response.cookies[COOKIE_NAME]["value"]
    return state


def callback(portal, request_, **payload) -> dict:
    """POST to the callback service.

    :param portal: The Plone site.
    :param request_: The current request.
    :param payload: The JSON body.
    :returns: The service's reply.
    """
    body(request_, payload)
    return IdentityCallback(portal, request_).reply()


@pytest.fixture()
def flow(portal, request_, configured, stub_metadata, stub_provider):
    """Start a flow against a healthy Dex and return its state."""
    stub_metadata(DEX_METADATA)
    stub_provider()
    return start_flow(portal, request_)


class TestSuccessfulLogin:
    def test_returns_a_token(self, portal, request_, flow):
        """The whole point: Volto ends up holding a jwt_auth token."""
        result = callback(portal, request_, provider="dex", code="c", state=flow)

        assert result["token"]

    def test_token_authenticates_as_the_new_user(self, portal, request_, flow):
        """And the token names the userid the plugin minted."""
        result = callback(portal, request_, provider="dex", code="c", state=flow)

        acl_users = api.portal.get_tool("acl_users")
        userid = acl_users.jwt_auth._decode_token(result["token"])["sub"]
        assert acl_users.getUserById(userid) is not None

    def test_identity_is_stored(self, portal, request_, flow):
        """The identity record is what makes the next login the same person."""
        callback(portal, request_, provider="dex", code="c", state=flow)

        plugin = api.portal.get_tool("acl_users")["identity"]
        assert plugin.store.userid_for("dex", USERINFO["sub"]) is not None

    def test_userid_is_a_uuid4_hex(self, portal, request_, flow):
        """D10/I1 -- nothing about the provider is derivable from the userid."""
        callback(portal, request_, provider="dex", code="c", state=flow)

        plugin = api.portal.get_tool("acl_users")["identity"]
        userid = plugin.store.userid_for("dex", USERINFO["sub"])
        assert len(userid) == 32
        assert USERINFO["sub"] not in userid

    def test_came_from_is_returned(
        self, portal, request_, configured, stub_metadata, stub_provider
    ):
        """Volto needs somewhere to send the user next."""
        stub_metadata(DEX_METADATA)
        stub_provider()
        request_.form["came_from"] = f"{portal.absolute_url()}/some/page"
        state = start_flow(portal, request_)

        result = callback(portal, request_, provider="dex", code="c", state=state)

        assert result["came_from"].endswith("/some/page")

    def test_second_login_is_the_same_user(
        self, portal, request_, configured, stub_metadata, stub_provider
    ):
        """I1 -- a returning human keeps their userid."""
        stub_metadata(DEX_METADATA)
        stub_provider()
        plugin = api.portal.get_tool("acl_users")["identity"]

        first = start_flow(portal, request_)
        callback(portal, request_, provider="dex", code="c", state=first)
        userid = plugin.store.userid_for("dex", USERINFO["sub"])

        request_.response.cookies.pop(COOKIE_NAME, None)
        request_.cookies.pop(COOKIE_NAME, None)
        second = start_flow(portal, request_)
        callback(portal, request_, provider="dex", code="c2", state=second)

        assert plugin.store.userid_for("dex", USERINFO["sub"]) == userid


class TestS1Negatives:
    """Every one of these must be refused, and read the same to the caller."""

    def test_unknown_state_is_refused(self, portal, request_, flow):
        """A forged state matches no attempt."""
        result = callback(
            portal, request_, provider="dex", code="c", state="not-a-real-state"
        )

        assert request_.response.getStatus() == 401
        assert result["error"]["type"] == "Authentication failed"

    def test_replayed_code_is_refused(self, portal, request_, flow):
        """The attempt is single-use, so the second callback finds nothing."""
        callback(portal, request_, provider="dex", code="c", state=flow)
        request_.cookies[COOKIE_NAME] = request_.response.cookies[COOKIE_NAME]["value"]

        callback(portal, request_, provider="dex", code="c", state=flow)

        assert request_.response.getStatus() == 401

    def test_callback_without_the_cookie_is_refused(self, portal, request_, flow):
        """S1 -- the callback is bound to the browser that started the flow.
        Someone else's browser has no attempt, whatever state they send."""
        request_.cookies.pop(COOKIE_NAME, None)

        callback(portal, request_, provider="dex", code="c", state=flow)

        assert request_.response.getStatus() == 401

    def test_state_from_another_provider_is_refused(
        self, portal, request_, flow, configured
    ):
        """A code issued for one provider is never redeemed at another."""
        from pas.plugins.identity.core.controlpanel import get_providers
        from pas.plugins.identity.core.controlpanel import ProviderConfig
        from pas.plugins.identity.core.controlpanel import set_providers

        other = ProviderConfig.deserialize({
            "id": "dex-two",
            "driver": "oidc-generic",
            "title": "Other",
            "enabled": True,
            "config": {"issuer": "http://dex:5556/dex", "client_id": "plone"},
        })
        set_providers([*get_providers(), other])

        callback(portal, request_, provider="dex-two", code="c", state=flow)

        assert request_.response.getStatus() == 401

    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"provider": "dex"},
            {"provider": "dex", "code": "c"},
            {"provider": "dex", "state": "s"},
            {"code": "c", "state": "s"},
            {"provider": "dex", "code": "", "state": "s"},
        ],
    )
    def test_incomplete_bodies_are_refused(self, portal, request_, payload: dict):
        """A callback without all three parts cannot be honoured."""
        result = callback(portal, request_, **payload)

        assert request_.response.getStatus() == 400
        assert result["error"]["type"] == "Missing parameters"

    @pytest.mark.parametrize("provider_id", ["nope", "github"])
    def test_unknown_and_disabled_provider_look_the_same(
        self, portal, request_, configured, provider_id: str
    ):
        """As with the listing, a disabled provider is not distinguishable."""
        result = callback(portal, request_, provider=provider_id, code="c", state="s")

        assert request_.response.getStatus() == 404
        assert result["error"]["type"] == "Unknown provider"


class TestProviderPayload:
    def test_payload_without_a_subject_is_refused(
        self, portal, request_, configured, stub_metadata, stub_provider
    ):
        """A provider that identifies nobody cannot log anybody in."""
        stub_metadata(DEX_METADATA)
        stub_provider({"email": "erico@plone.org"})
        state = start_flow(portal, request_)

        result = callback(portal, request_, provider="dex", code="c", state=state)

        assert request_.response.getStatus() == 502
        assert result["error"]["type"] == "Provider payload rejected"


class TestExistingIdentity:
    """A login never collides: an identity already in the store resolves to
    whoever owns it. Collisions are a *linking* concern (I3/S3, Gate 2)."""

    def test_logs_in_as_the_existing_owner(self, portal, request_, flow):
        """The identity's owner is who gets the token -- no second account."""
        with api.env.adopt_roles(["Manager"]):
            member = api.user.create(
                email="owner@plone.org",
                username="owner",
                password="s3cr3t-owner",
            )
        owner = member.getId()
        acl_users = api.portal.get_tool("acl_users")
        acl_users["identity"].store.add("dex", USERINFO["sub"], owner, {})

        result = callback(portal, request_, provider="dex", code="c", state=flow)

        assert acl_users.jwt_auth._decode_token(result["token"])["sub"] == owner

    def test_mints_no_second_userid(self, portal, request_, flow):
        """I1 -- and the store still holds exactly the one identity."""
        with api.env.adopt_roles(["Manager"]):
            member = api.user.create(
                email="owner2@plone.org",
                username="owner2",
                password="s3cr3t-owner",
            )
        owner = member.getId()
        plugin = api.portal.get_tool("acl_users")["identity"]
        plugin.store.add("dex", USERINFO["sub"], owner, {})

        callback(portal, request_, provider="dex", code="c", state=flow)

        assert plugin.store.userid_for("dex", USERINFO["sub"]) == owner
        assert len(plugin.store.identities_for(owner)) == 1


class TestMisconfiguredSite:
    def test_no_jwt_plugin_is_a_501(self, portal, request_, flow, monkeypatch):
        """Without a JWT plugin no Volto login could work by any route, so
        the caller is owed a clear "not implemented here", not a traceback."""
        from pas.plugins.identity.core.services import callback as module

        monkeypatch.setattr(module, "JWT_PLUGIN_META_TYPE", "No Such Plugin")

        result = callback(portal, request_, provider="dex", code="c", state=flow)

        assert request_.response.getStatus() == 501
        assert "JWT authentication plugin" in result["error"]["message"]
