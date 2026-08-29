"""This package federating with itself.

Two Plone sites in containers, sharing no process and no code path at runtime.
Site A is ``core + profile + server`` and is an OpenID Connect provider; site B
is ``core`` with the generic OIDC driver pointed at nothing but A's issuer URL.
A user who exists only on A signs in on B.

Everything here is driven over HTTP, the way a browser would: the test reads
the redirect and posts the code, because the frontend route the provider
redirects to is a Volto route and nothing serves it in a headless stack.

This is the test that found the two defects the fixes in this commit address.
Neither was visible from either side alone: the server accepted client
credentials only in the form while advertising nothing else, and the client
sent them only in an ``Authorization`` header while reading nothing. Each was
self-consistent, and together they could not complete a login.
"""

from bs4 import BeautifulSoup
from identitydemo import settings
from urllib.parse import parse_qs
from urllib.parse import urljoin
from urllib.parse import urlparse

import base64
import json
import pytest
import requests


pytestmark = pytest.mark.docker

#: Headers for the relying party's REST API.
JSON_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

#: Plone's login form. Named because the page also carries the search form,
#: and taking the first form on the page posts a search.
LOGIN_FORM_ID = "LoginForm"


def _form_fields(form) -> dict:
    """Return a form's inputs as a payload.

    :param form: A BeautifulSoup form element.
    :returns: Mapping of field name to value.
    """
    return {
        field.get("name"): field.get("value") or ""
        for field in form.find_all("input")
        if field.get("name")
    }


def _claims(token: str) -> dict:
    """Decode a JWT payload without verifying it.

    The relying party's own signature is not what this test is about, and
    verifying it would need a key only that site has.

    :param token: A JWT.
    :returns: The claims.
    """
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


class TestFederatedLogin:
    @pytest.fixture(autouse=True)
    def _setup(self, federation_stack):
        self.urls = federation_stack
        self.session = requests.Session()

    def _start_login(self) -> str:
        response = self.session.get(
            f"{self.urls['rp']}/@login-providers/{settings.DEMO_PROVIDER_ID}",
            headers=JSON_HEADERS,
            timeout=30,
        )
        assert response.status_code == 200, response.text
        return response.json()["authorize_url"]

    def _sign_in(self, authorize_url: str):
        """Sign in at the provider and return where the authorize request got
        to: either the consent screen, or the redirect back to the relying
        party when consent for this user and client is already recorded."""
        page = self.session.get(authorize_url, timeout=30)
        form = BeautifulSoup(page.text, "html.parser").find("form", id=LOGIN_FORM_ID)
        assert form is not None, "The provider did not serve a login form"

        payload = _form_fields(form)
        payload["__ac_name"] = settings.DEMO_USER_ID
        payload["__ac_password"] = settings.DEMO_USER_PASSWORD
        payload["buttons.login"] = "Log in"
        return self.session.post(
            urljoin(page.url, form.get("action") or page.url),
            data=payload,
            timeout=30,
        )

    def _authenticate_at_the_provider(self, authorize_url: str) -> str:
        """Sign in on the provider and return the URL it redirects back to.

        Consent is recorded per user and per client, so only the first flow
        in a session sees the screen. Every later one is redirected straight
        back, which is the behaviour :meth:`test_consent_is_remembered`
        asserts and which this has to tolerate to be re-runnable at all.
        """
        landed = self._sign_in(authorize_url)

        form = BeautifulSoup(landed.text, "html.parser").find("form")
        if form is None or "code=" in landed.url:
            # Consent was already given; requests followed the redirect to the
            # frontend route, which nothing serves. The code is on its URL.
            assert "code=" in landed.url, landed.url
            return landed.url

        granted = self.session.post(
            urljoin(landed.url, form.get("action") or landed.url),
            data={**_form_fields(form), "consent": "allow"},
            timeout=30,
            allow_redirects=False,
        )
        assert granted.status_code == 302, granted.text
        return granted.headers["Location"]

    def _redeem(self, redirect: str) -> dict:
        """Redeem the code exactly as the Volto callback route does.

        Deliberately sends no ``provider``. The redirect carries ``code`` and
        ``state`` and nothing else, so the frontend has none to send -- and
        this test supplying one by hand is how it managed to pass while every
        real browser login answered 400.
        """
        query = parse_qs(urlparse(redirect).query)
        response = self.session.post(
            f"{self.urls['rp']}/@identity-callback",
            headers=JSON_HEADERS,
            data=json.dumps({
                "code": query["code"][0],
                "state": query["state"][0],
            }),
            timeout=60,
        )
        assert response.status_code == 200, response.text
        return response.json()

    def test_discovery_is_all_the_relying_party_was_given(self):
        """The provider was configured with an issuer URL and a client
        credential, and nothing else: no endpoints, no keys. Everything the
        flow needs came out of the discovery document."""
        document = requests.get(
            f"{self.urls['idp']}/.well-known/openid-configuration", timeout=30
        ).json()

        assert document["issuer"] == settings.IDP_PUBLIC_URL
        for endpoint in (
            "authorization_endpoint",
            "token_endpoint",
            "jwks_uri",
            "userinfo_endpoint",
        ):
            assert document[endpoint].startswith(settings.IDP_PUBLIC_URL)

    def test_the_provider_advertises_basic_client_authentication(self):
        """RFC 6749 §2.3.1 requires the token endpoint to accept it, and an
        off-the-shelf relying party will try it first. Asserted against a
        running server rather than against the function that builds the
        document."""
        document = requests.get(
            f"{self.urls['idp']}/.well-known/openid-configuration", timeout=30
        ).json()

        assert (
            "client_secret_basic" in document["token_endpoint_auth_methods_supported"]
        )

    def test_the_relying_party_offers_the_provider(self):
        response = self.session.get(
            f"{self.urls['rp']}/@login-providers", headers=JSON_HEADERS, timeout=30
        )

        offered = {item["id"] for item in response.json()["items"]}

        assert settings.DEMO_PROVIDER_ID in offered

    def test_the_authorize_url_is_built_from_the_provider_metadata(self):
        authorize_url = self._start_login()
        query = parse_qs(urlparse(authorize_url).query)

        assert authorize_url.startswith(settings.IDP_PUBLIC_URL)
        assert query["client_id"] == [settings.DEMO_CLIENT_ID]
        assert query["redirect_uri"] == [settings.DEMO_REDIRECT_URI]
        # Both are what make the flow safe to run in a browser, and both are
        # this package's own doing rather than the provider's.
        assert query["code_challenge_method"] == ["S256"]
        assert "nonce" in query

    def test_an_anonymous_visitor_is_challenged_rather_than_refused(self):
        """A relying party sending a user who is not signed in at the
        provider must get a login page, not ``error=login_required`` with the
        browser handed straight back."""
        page = self.session.get(self._start_login(), timeout=30)

        assert page.status_code == 200
        assert "login" in urlparse(page.url).path
        assert BeautifulSoup(page.text, "html.parser").find("form", id=LOGIN_FORM_ID)

    def test_a_user_who_exists_only_on_the_provider_can_sign_in(self):
        """The gate. Nothing created this user on the relying party; the
        relying party learned of them through the flow."""
        redirect = self._authenticate_at_the_provider(self._start_login())

        assert redirect.startswith(settings.DEMO_REDIRECT_URI)

        body = self._redeem(redirect)

        assert "token" in body

    def test_the_relying_party_provisions_the_federated_user(self):
        body = self._redeem(self._authenticate_at_the_provider(self._start_login()))
        claims = _claims(body["token"])

        user = self.session.get(
            f"{self.urls['rp']}/@users/{claims['sub']}",
            headers={**JSON_HEADERS, "Authorization": f"Bearer {body['token']}"},
            timeout=30,
        )

        assert user.status_code == 200
        assert user.json()["email"] == settings.DEMO_USER_EMAIL
        assert user.json()["fullname"] == settings.DEMO_USER_FULLNAME

    @pytest.mark.xfail(
        reason=(
            "The demo asks for username-derived userids and this asserts the "
            "default. Érico's call which of the two to change; see the "
            "docstring."
        ),
        strict=True,
    )
    def test_the_local_userid_is_not_the_providers_subject(self):
        """The relying party mints its own opaque id. Reusing the provider's
        subject would leak it into every URL that names a user, and would tie
        the account to one provider for good.

        **Known red, and not by this branch.** ``7e22204`` set
        ``userid_source`` to ``username`` on the demo relying party, for
        legibility -- so it mints ``dana`` rather than a uuid. The demo user's
        userid at the provider is also ``dana``, so the two are
        indistinguishable in this stack and the assertion cannot hold.

        Nothing noticed because this suite is docker-marked and the repository
        has no remote, so it has never run in CI.

        Two ways out, and they are different decisions rather than a fix:
        point the demo's ``userid_source`` back at ``uuid`` and lose the
        legible userids, or drop this assertion and cover the default
        elsewhere. Marked ``strict`` so that whichever is chosen, this stops
        being a silent pass.
        """
        body = self._redeem(self._authenticate_at_the_provider(self._start_login()))
        claims = _claims(body["token"])

        assert claims["sub"] != settings.DEMO_USER_ID
        assert settings.DEMO_USER_ID not in claims["sub"]

    def test_consent_is_remembered(self):
        """The first authorization asks; a second one for the same user and
        client does not. The session is still signed in at the provider by
        then, so this asserts the whole authorize request completing with no
        interaction at all -- no login form and no consent screen."""
        self._redeem(self._authenticate_at_the_provider(self._start_login()))

        landed = self.session.get(self._start_login(), timeout=30)

        assert "code=" in landed.url
        assert (
            BeautifulSoup(landed.text, "html.parser").find("form", id=LOGIN_FORM_ID)
            is None
        )
