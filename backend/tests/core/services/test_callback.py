"""Integration tests for ``@identity-callback``.

The provider's two network calls are stubbed; everything else is the real
thing -- the real flow manager, the real signed cookie, the real PAS plugin,
the real JWT plugin. What is asserted is what a Volto login actually needs:
a token, a stable userid, and a flat refusal for every way a flow can fail.
"""

from .. import body
from . import DEX_METADATA
from . import DEX_PROVIDER
from . import USERINFO
from pas.plugins.identity.core.audit import AUTHENTICATED
from pas.plugins.identity.core.audit import FLOW_REFUSED
from pas.plugins.identity.core.audit import PAYLOAD_REJECTED
from pas.plugins.identity.core.audit import UNATTRIBUTED
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.flows.session import COOKIE_NAME
from pas.plugins.identity.core.services import jwt
from pas.plugins.identity.core.services.callback.post import IdentityCallback
from pas.plugins.identity.core.services.login.get import LoginProviders
from plone import api
from urllib.parse import parse_qs
from urllib.parse import urlparse

import pytest


class CallbackCase:
    """The pieces every group of these tests drives."""

    def start_flow(self) -> str:
        """Start a real flow and hand the cookie back to the browser.

        :returns: The ``state`` the provider would echo back.
        """
        view = LoginProviders(self.portal, self.request)
        view.publishTraverse(self.request, "dex")
        result = view.reply()
        state = parse_qs(urlparse(result["authorize_url"]).query)["state"][0]
        self.keep_cookie()
        return state

    def keep_cookie(self) -> None:
        """Carry the flow cookie the response set back onto the request."""
        self.request.cookies[COOKIE_NAME] = self.request.response.cookies[COOKIE_NAME][
            "value"
        ]

    def callback(self, **payload) -> dict:
        """POST to the callback service.

        :param payload: The JSON body.
        :returns: The service's reply.
        """
        body(self.request, payload)
        return IdentityCallback(self.portal, self.request).reply()

    def finish(self, state: str, code: str = "c") -> dict:
        """Complete the flow for a state.

        :param state: The state to send back.
        :param code: The authorization code to send back.
        :returns: The service's reply.
        """
        return self.callback(provider="dex", code=code, state=state)

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


class TestSuccessfulLogin(CallbackCase):
    @pytest.fixture(autouse=True)
    def _setup(
        self, portal, request_, configured, stub_metadata, stub_provider
    ) -> None:
        self.portal = portal
        self.request = request_
        stub_metadata(DEX_METADATA)
        stub_provider()
        self.flow = self.start_flow()

    def test_returns_a_token(self):
        """The whole point: Volto ends up holding a jwt_auth token."""
        assert self.finish(self.flow)["token"]

    def test_token_authenticates_as_the_new_user(self):
        """And the token names the userid the plugin minted."""
        result = self.finish(self.flow)

        acl_users = api.portal.get_tool("acl_users")
        userid = acl_users.jwt_auth._decode_token(result["token"])["sub"]
        assert acl_users.getUserById(userid) is not None

    def test_identity_is_stored(self):
        """The identity record is what makes the next login the same person."""
        self.finish(self.flow)

        assert self.plugin().store.userid_for("dex", USERINFO["sub"]) is not None

    def test_userid_is_a_uuid4_hex(self):
        """Nothing about the provider is derivable from the userid."""
        self.finish(self.flow)

        userid = self.plugin().store.userid_for("dex", USERINFO["sub"])
        assert len(userid) == 32
        assert USERINFO["sub"] not in userid

    def test_came_from_is_returned(self):
        """Volto needs somewhere to send the user next."""
        self.request.form["came_from"] = f"{self.portal.absolute_url()}/some/page"
        state = self.start_flow()

        assert self.finish(state)["came_from"].endswith("/some/page")

    def test_second_login_is_the_same_user(self):
        """A returning human keeps their userid."""
        self.finish(self.flow)
        userid = self.plugin().store.userid_for("dex", USERINFO["sub"])

        self.request.response.cookies.pop(COOKIE_NAME, None)
        self.request.cookies.pop(COOKIE_NAME, None)
        self.finish(self.start_flow(), code="c2")

        assert self.plugin().store.userid_for("dex", USERINFO["sub"]) == userid


class TestProviderIsOptional(CallbackCase):
    """A provider redirects back with ``code`` and ``state`` and nothing else,
    so the frontend route the browser lands on has no way to know which
    provider it is talking to: it is a fresh page load and the query string is
    all it has. Requiring it in the body meant every browser login answered
    400 while every test that supplied it by hand passed."""

    @pytest.fixture(autouse=True)
    def _setup(
        self, portal, request_, configured, stub_metadata, stub_provider
    ) -> None:
        self.portal = portal
        self.request = request_
        stub_metadata(DEX_METADATA)
        stub_provider()
        self.flow = self.start_flow()

    def test_the_provider_comes_from_the_state(self):
        """The session minted the state against an attempt that records the
        provider, and the code is redeemed against that same attempt a moment
        later."""
        result = self.callback(code="c", state=self.flow)

        assert self.status() == 200
        assert result["token"]

    def test_an_empty_provider_is_the_same_as_none(self):
        """Which is what the frontend sends: it reads the parameter off the
        query string and defaults it to the empty string."""
        result = self.callback(provider="", code="c", state=self.flow)

        assert self.status() == 200
        assert result["token"]

    def test_a_supplied_provider_is_still_honoured(self):
        """Callers that do know keep working, and a mismatched one is still
        refused by the exchange."""
        result = self.callback(provider="dex", code="c", state=self.flow)

        assert self.status() == 200
        assert result["token"]

    def test_an_unusable_state_is_refused_as_authentication(self):
        """Not as a missing parameter, and not as an unknown provider: the
        state is the thing that failed, and it reads like every other state
        failure."""
        result = self.callback(code="c", state="never-issued")

        assert self.status() == 401
        assert result["error"]["type"] == "Authentication failed"

    def test_deriving_the_provider_does_not_consume_the_state(self):
        """``peek`` must leave the attempt where ``pop`` will find it, or the
        exchange a line later fails on the state it just read."""
        assert self.callback(code="c", state=self.flow)["token"]

    def test_the_state_is_still_single_use(self):
        """And having been read twice in one request must not make it
        replayable. ``keep_cookie`` carries the rewritten session forward, as
        a browser would; without it the second request still holds the
        pre-redemption session and the assertion tests the harness."""
        self.callback(code="c", state=self.flow)
        self.keep_cookie()

        self.callback(code="c", state=self.flow)

        assert self.status() == 401


class TestRefusals(CallbackCase):
    """Every one of these must be refused, and read the same to the caller."""

    @pytest.fixture(autouse=True)
    def _setup(
        self, portal, request_, configured, stub_metadata, stub_provider
    ) -> None:
        self.portal = portal
        self.request = request_
        stub_metadata(DEX_METADATA)
        stub_provider()
        self.flow = self.start_flow()

    def test_unknown_state_is_refused(self):
        """A forged state matches no attempt."""
        result = self.finish("not-a-real-state")

        assert self.status() == 401
        assert result["error"]["type"] == "Authentication failed"

    def test_replayed_code_is_refused(self):
        """The attempt is single-use, so the second callback finds nothing."""
        self.finish(self.flow)
        self.keep_cookie()

        self.finish(self.flow)

        assert self.status() == 401

    def test_callback_without_the_cookie_is_refused(self):
        """The callback is bound to the browser that started the flow.
        Someone else's browser has no attempt, whatever state they send."""
        self.request.cookies.pop(COOKIE_NAME, None)

        self.finish(self.flow)

        assert self.status() == 401

    def test_state_from_another_provider_is_refused(self):
        """A code issued for one provider is never redeemed at another."""
        other = ProviderConfig.deserialize({
            "id": "dex-two",
            "driver": "oidc-generic",
            "title": "Other",
            "enabled": True,
            "config": {"issuer": "http://dex:5556/dex", "client_id": "plone"},
        })
        set_providers([*get_providers(), other])

        self.callback(provider="dex-two", code="c", state=self.flow)

        assert self.status() == 401

    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"provider": "dex"},
            {"provider": "dex", "code": "c"},
            {"provider": "dex", "state": "s"},
            {"provider": "dex", "code": "", "state": "s"},
            {"code": "c"},
            {"state": "s"},
        ],
    )
    def test_incomplete_bodies_are_refused(self, payload: dict):
        """A callback without a code and a state cannot be honoured.

        ``provider`` is not in that list: see
        :meth:`TestProviderIsOptional.test_the_provider_comes_from_the_state`.
        """
        result = self.callback(**payload)

        assert self.status() == 400
        assert result["error"]["type"] == "Missing parameters"

    @pytest.mark.parametrize("provider_id", ["nope", "github"])
    def test_unknown_and_disabled_provider_look_the_same(self, provider_id: str):
        """As with the listing, a disabled provider is not distinguishable."""
        result = self.callback(provider=provider_id, code="c", state="s")

        assert self.status() == 404
        assert result["error"]["type"] == "Unknown provider"


class TestProviderPayload(CallbackCase):
    @pytest.fixture(autouse=True)
    def _setup(
        self, portal, request_, configured, stub_metadata, stub_provider
    ) -> None:
        self.portal = portal
        self.request = request_
        stub_metadata(DEX_METADATA)
        stub_provider({"email": "erico@plone.org"})

    def test_payload_without_a_subject_is_refused(self):
        """A provider that identifies nobody cannot log anybody in."""
        result = self.finish(self.start_flow())

        assert self.status() == 502
        assert result["error"]["type"] == "Provider payload rejected"


class TestExistingIdentity(CallbackCase):
    """A login never collides: an identity already in the store resolves to
    whoever owns it. Collisions are a *linking* concern."""

    @pytest.fixture(autouse=True)
    def _setup(
        self, portal, request_, configured, stub_metadata, stub_provider
    ) -> None:
        self.portal = portal
        self.request = request_
        stub_metadata(DEX_METADATA)
        stub_provider()
        self.flow = self.start_flow()
        member = api.user.create(
            email="owner@plone.org",
            username="owner",
            password="s3cr3t-owner",
        )
        self.owner = member.getId()
        self.plugin().store.add("dex", USERINFO["sub"], self.owner, {})

    def test_logs_in_as_the_existing_owner(self):
        """The identity's owner is who gets the token -- no second account."""
        result = self.finish(self.flow)

        acl_users = api.portal.get_tool("acl_users")
        assert acl_users.jwt_auth._decode_token(result["token"])["sub"] == self.owner

    def test_mints_no_second_userid(self):
        """And the store still holds exactly the one identity."""
        self.finish(self.flow)

        assert self.plugin().store.userid_for("dex", USERINFO["sub"]) == self.owner
        assert len(self.plugin().store.identities_for(self.owner)) == 1


class TestMisconfiguredSite(CallbackCase):
    @pytest.fixture(autouse=True)
    def _setup(
        self, portal, request_, configured, stub_metadata, stub_provider, monkeypatch
    ) -> None:
        self.portal = portal
        self.request = request_
        stub_metadata(DEX_METADATA)
        stub_provider()
        self.flow = self.start_flow()
        monkeypatch.setattr(jwt, "JWT_PLUGIN_META_TYPE", "No Such Plugin")

    def test_no_jwt_plugin_is_a_501(self):
        """Without a JWT plugin no Volto login could work by any route, so
        the caller is owed a clear "not implemented here", not a traceback."""
        result = self.finish(self.flow)

        assert self.status() == 501
        assert "JWT authentication plugin" in result["error"]["message"]


class TestAuditTrail(CallbackCase):
    """Every refused callback leaves an audit entry. A refusal nobody can
    see afterwards is how a credential-stuffing run goes unnoticed.
    """

    @pytest.fixture(autouse=True)
    def _setup(
        self, portal, request_, configured, stub_metadata, stub_provider, log
    ) -> None:
        self.portal = portal
        self.request = request_
        self.log = log
        self.stub_provider = stub_provider
        self.stub_metadata = stub_metadata
        stub_metadata(DEX_METADATA)
        stub_provider()
        self.flow = self.start_flow()

    def test_successful_login_is_recorded(self):
        """The happy path is audited too, against the userid it resolved."""
        self.finish(self.flow)

        entries = self.log.entries()
        assert [entry.event for entry in entries] == [AUTHENTICATED]
        assert entries[0].success is True

    def test_unknown_state_is_recorded(self):
        """And the entry says which precondition failed."""
        self.finish("forged")

        entry = self.log.entries()[0]
        assert entry.event == FLOW_REFUSED
        assert entry.success is False
        assert entry.provider == "dex"
        assert "state" in entry.detail["reason"].lower()

    def test_replayed_code_is_recorded(self):
        """Two attempts, two entries: one success and one refusal."""
        self.finish(self.flow)
        self.keep_cookie()
        self.finish(self.flow)

        assert sorted(entry.event for entry in self.log.entries()) == [
            AUTHENTICATED,
            FLOW_REFUSED,
        ]

    def test_refusals_are_unattributed(self):
        """A refused callback has no userid -- that is what refused means --
        so it lands in the bucket an operator investigating an attack reads."""
        self.finish("forged")

        assert len(self.log.entries(UNATTRIBUTED)) == 1

    def test_unusable_payload_is_recorded(self):
        """A provider that identifies nobody is worth a distinct entry."""
        self.stub_provider({"email": "erico@plone.org"})
        state = self.start_flow()

        self.finish(state)

        assert self.log.entries()[0].event == PAYLOAD_REJECTED

    def test_no_credentials_are_recorded(self):
        """The code, the token and the verifier never reach the log."""
        self.finish(self.flow, code="super-secret-code")
        self.keep_cookie()
        self.finish(self.flow, code="super-secret-code")

        rendered = str([entry.serialize() for entry in self.log.entries()])
        assert "super-secret-code" not in rendered
        assert "at" not in rendered.split("'detail'")[0]

    def test_no_ip_recorded_by_default(self):
        """Privacy default is off, including on the failure path."""
        self.finish("forged")

        assert "ip" not in self.log.entries()[0].detail


class TestAProviderThatSendsStringBooleans(CallbackCase):
    """``email_verified`` arriving as the string ``"true"``.

    Only a literal boolean satisfies the link-by-email gate, so against such a
    provider every address is silently unverified -- automatic linking never
    fires and nothing says why. The repair is per-provider and off by default,
    which is what the first test here is about: the strict reading has to stay
    the strict reading for everybody who did not ask.
    """

    @pytest.fixture(autouse=True)
    def _setup(
        self, portal, request_, configured, stub_metadata, stub_provider
    ) -> None:
        self.portal = portal
        self.request = request_
        self.stub_provider = stub_provider
        stub_metadata(DEX_METADATA)

    def sign_in(self, accept_strings: bool, verified: object = "true") -> dict:
        """Complete a login against a provider sending a string flag.

        :param accept_strings: Whether the provider is configured to have its
            verification flags read as text.
        :param verified: What the provider sends as ``email_verified``.
        :returns: The stored claims for the identity that signed in.
        """
        provider = ProviderConfig.deserialize(DEX_PROVIDER)
        provider.config["accept_string_booleans"] = accept_strings
        set_providers([provider])
        self.stub_provider({**USERINFO, "email_verified": verified})
        state = self.start_flow()
        self.finish(state)
        record = self.plugin()._store.get("dex", USERINFO["sub"])
        return dict(record.claims)

    def test_off_by_default_the_string_is_not_verified(self):
        """The behaviour the issue is about, asserted so the repair cannot be
        mistaken for having always been there."""
        assert self.sign_in(accept_strings=False)["email_verified"] is False

    def test_the_setting_makes_the_string_count(self):
        assert self.sign_in(accept_strings=True)["email_verified"] is True

    def test_the_string_false_still_does_not_count(self):
        """Repair reads both directions. One that only ever said True would be
        a switch that grants verification rather than one that reads it."""
        claims = self.sign_in(accept_strings=True, verified="false")

        assert claims["email_verified"] is False

    def test_the_reported_address_is_verified_too(self):
        """``emails`` is derived from the same flag, so repairing one and not
        the other would record an address as unchecked on the account while
        the claim beside it said otherwise."""
        claims = self.sign_in(accept_strings=True)

        assert claims["emails"][0]["verified"] is True

    def test_raw_still_says_what_the_provider_said(self):
        """The string is the evidence an operator diagnosing this provider
        needs, and ``raw`` is documented as the provider's own words."""
        claims = self.sign_in(accept_strings=True)

        assert claims["raw"]["email_verified"] == "true"

    def test_a_value_nobody_can_read_is_still_refused(self):
        """The repair reads two spellings and guesses at nothing: ``"1"``
        granting a verified address would be this feature causing the bug it
        exists to fix."""
        claims = self.sign_in(accept_strings=True, verified="1")

        assert claims["email_verified"] is False
