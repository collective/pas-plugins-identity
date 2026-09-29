"""The Volto-session plugin, and the narrowness that makes it acceptable.

``plone.restapi`` deliberately does not read the ``auth_token`` cookie: a
bearer credential the browser attaches on its own turns every browser view
into a CSRF target. This plugin reads it for exactly one view, so most of
these tests are about the requests it must *not* answer.
"""

from .. import PROFILE_ID
from pas.plugins.identity.server.setuphandlers import install_session_plugin
from pas.plugins.identity.server.setuphandlers import uninstall_session_plugin
from pas.plugins.identity.server.utils.session import COOKIE_NAME
from pas.plugins.identity.server.utils.session import IdentityAuthorizeSessionPlugin
from pas.plugins.identity.server.utils.session import PLUGIN_ID
from plone import api

import base64
import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])

#: A browser-facing URL for the authorization endpoint.
AUTHORIZE_URL = "http://id.example.org/@@oauth-authorize"


class SessionCase:
    def request_for(self, url: str, token: str = "", auth: str = "") -> object:
        """Build a request as the publisher would present it.

        :param url: The browser-facing URL.
        :param token: Value for the Volto session cookie, if any.
        :param auth: Value for ``request._auth``, if any.
        :returns: The prepared request.
        """
        request = self.portal.REQUEST
        request.cookies.clear()
        request["ACTUAL_URL"] = url
        request._auth = auth or None
        if token:
            request.cookies[COOKIE_NAME] = token
        return request

    def token_for(self, userid: str) -> str:
        """Mint a Volto session token the way ``@login`` does.

        :param userid: The user to mint it for.
        :returns: A ``jwt_auth`` token.
        """
        return api.portal.get_tool("acl_users").jwt_auth.create_token(userid)


class TestScope(SessionCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.plugin = portal.acl_users[PLUGIN_ID]

    def test_the_authorization_endpoint_is_read(self):
        """The one view this exists for."""
        request = self.request_for(AUTHORIZE_URL, token="a-token")

        assert self.plugin.extractCredentials(request)["token"] == "a-token"

    @pytest.mark.parametrize(
        "url",
        [
            "http://id.example.org",
            "http://id.example.org/some-document",
            "http://id.example.org/@@oauth-userinfo",
            "http://id.example.org/@@oauth-token",
            "http://id.example.org/++api++/@users",
            "http://id.example.org/manage_main",
        ],
    )
    def test_every_other_view_is_left_alone(self, url: str):
        """Including the package's own other endpoints. This is the whole
        argument for the plugin being acceptable at all: everywhere else the
        site behaves exactly as plone.restapi left it."""
        request = self.request_for(url, token="a-token")

        assert self.plugin.extractCredentials(request) == {}

    def test_no_cookie_is_nothing_to_do(self):
        request = self.request_for(AUTHORIZE_URL)

        assert self.plugin.extractCredentials(request) == {}

    def test_an_empty_cookie_is_nothing_to_do(self):
        request = self.request_for(AUTHORIZE_URL, token="")

        assert self.plugin.extractCredentials(request) == {}

    @pytest.mark.parametrize("scheme", ["Bearer", "bearer", "BEARER"])
    def test_a_bearer_header_outranks_the_cookie(self, scheme: str):
        """The header is the credential the caller chose to present. A stale
        cookie must not decide a request that named a different principal.
        The scheme is matched as plone.restapi matches it."""
        request = self.request_for(
            AUTHORIZE_URL, token="cookie-token", auth=f"{scheme} header-token"
        )

        assert self.plugin.extractCredentials(request) == {}

    @pytest.mark.parametrize(
        "auth", ["Basic c29tZW9uZTpzb21ldGhpbmc=", "Digest username=someone"]
    )
    def test_another_scheme_does_not_hide_the_cookie(self, auth: str):
        """plone.restapi reads only Bearer. A browser resending a proxy's
        cached Basic credentials must not make a signed-in visitor
        anonymous here."""
        request = self.request_for(AUTHORIZE_URL, token="cookie-token", auth=auth)

        assert self.plugin.extractCredentials(request)["token"] == "cookie-token"


class TestAuthentication(SessionCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.plugin = portal.acl_users[PLUGIN_ID]
        api.user.create(
            email="carol@example.org", username="carol", password="s3cret!x"
        )

    def test_a_valid_token_authenticates_its_user(self):
        token = self.token_for("carol")

        assert self.plugin.authenticateCredentials({
            "extractor": PLUGIN_ID,
            "token": token,
        }) == ("carol", "carol")

    def test_another_plugins_credentials_are_ignored(self):
        """PAS offers every extractor's credentials to every authenticator."""
        assert (
            self.plugin.authenticateCredentials({
                "extractor": "jwt_auth",
                "token": self.token_for("carol"),
            })
            is None
        )

    def test_a_forged_token_is_refused(self):
        """Decoding is plone.restapi's, so this asserts that we did not
        accidentally trust the payload without it."""
        assert (
            self.plugin.authenticateCredentials({
                "extractor": PLUGIN_ID,
                "token": "not.a.token",
            })
            is None
        )

    def test_a_token_for_a_departed_user_is_refused(self):
        """The token outlived the user. Authenticating them anyway would put
        a principal on the request that no roles plugin has heard of."""
        token = self.token_for("carol")
        # Removing a user is a manager's action, and ``mark.portal`` applies
        # profiles as whoever is logged in. Adopted here rather than granted
        # for the class: this is the only test that needs it.
        with api.env.adopt_roles(["Manager"]):
            api.user.delete(username="carol")

        assert (
            self.plugin.authenticateCredentials({
                "extractor": PLUGIN_ID,
                "token": token,
            })
            is None
        )

    def test_a_site_without_the_jwt_plugin_has_nothing_to_read(self):
        """Not an error: a site with no plone.restapi JWT plugin simply has
        no Volto session to find."""
        self.portal.acl_users._delObject("jwt_auth")

        assert (
            self.plugin.authenticateCredentials({
                "extractor": PLUGIN_ID,
                "token": "anything",
            })
            is None
        )


class TestThroughPAS(SessionCase):
    """The plugin as PAS reaches it, beside the site's other extractors."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.acl_users = portal.acl_users
        api.user.create(
            email="carol@example.org", username="carol", password="s3cret!x"
        )
        api.user.create(email="dave@example.org", username="dave", password="s3cret!y")

    def user_ids(self, request: object) -> list[str]:
        """Resolve a request to user ids, in the order PAS would try them.

        :param request: The prepared request.
        :returns: The user ids PAS authenticated.
        """
        found = self.acl_users._extractUserIds(request, self.acl_users.plugins)
        return [user_id for user_id, _login in found]

    @staticmethod
    def basic(login: str, password: str) -> str:
        """Build a Basic ``Authorization`` value.

        :param login: The login to present.
        :param password: The password to present.
        :returns: The header value.
        """
        return "Basic " + base64.b64encode(f"{login}:{password}".encode()).decode()

    def test_a_proxys_basic_credentials_leave_the_session_signed_in(self):
        """The loop reported on id.plone.org: a browser resending Basic
        credentials that belong to a proxy, not to Plone, was anonymous at
        the authorization endpoint."""
        request = self.request_for(
            AUTHORIZE_URL,
            token=self.token_for("carol"),
            auth=self.basic("someone", "something"),
        )

        assert self.user_ids(request) == ["carol"]

    def test_basic_credentials_for_a_plone_user_still_come_first(self):
        """Letting the cookie through beside a Basic header must not let it
        decide a request that named a real principal."""
        request = self.request_for(
            AUTHORIZE_URL,
            token=self.token_for("carol"),
            auth=self.basic("dave", "s3cret!y"),
        )

        assert self.user_ids(request)[0] == "dave"


class TestInstallation:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.acl_users = portal.acl_users

    def test_the_plugin_is_installed_with_the_server_layer(self):
        """It exists for the authorization endpoint, so it arrives with the
        layer that creates one."""
        assert isinstance(self.acl_users[PLUGIN_ID], IdentityAuthorizeSessionPlugin)

    @pytest.mark.parametrize(
        "interface_name", ["IExtractionPlugin", "IAuthenticationPlugin"]
    )
    def test_the_plugin_is_activated(self, interface_name: str):
        active = [
            info["id"]
            for info in self.acl_users.plugins.listPluginTypeInfo()
            if info["id"] == interface_name
        ]

        assert active, f"{interface_name} is not a known plugin type"
        interface = next(
            info["interface"]
            for info in self.acl_users.plugins.listPluginTypeInfo()
            if info["id"] == interface_name
        )
        assert PLUGIN_ID in self.acl_users.plugins.listPluginIds(interface)

    def test_installing_twice_changes_nothing(self):
        """Re-applying the profile is an ordinary thing to do."""
        before = self.acl_users[PLUGIN_ID]

        install_session_plugin(self.acl_users)

        assert self.acl_users[PLUGIN_ID].getId() == before.getId()

    def test_uninstalling_removes_it(self):
        uninstall_session_plugin(self.acl_users)

        assert PLUGIN_ID not in self.acl_users

    def test_uninstalling_deactivates_every_interface(self):
        """Every one, not only the two install activates: a site that
        switched another on by hand must not be left with a registration
        pointing at an object that is gone."""
        uninstall_session_plugin(self.acl_users)

        registered = [
            info["id"]
            for info in self.acl_users.plugins.listPluginTypeInfo()
            if PLUGIN_ID in self.acl_users.plugins.listPluginIds(info["interface"])
        ]

        assert registered == []

    def test_uninstalling_twice_is_not_an_error(self):
        uninstall_session_plugin(self.acl_users)

        uninstall_session_plugin(self.acl_users)

        assert PLUGIN_ID not in self.acl_users
