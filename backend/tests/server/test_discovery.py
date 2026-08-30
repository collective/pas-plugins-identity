"""Discovery, the JWKS, and the id_token.

The discovery document is the one thing an integrator is promised they can
point a client at and have everything else follow. So these tests are mostly
about it being *true*: every endpoint it advertises exists, every algorithm it
lists is the one actually used, and the issuer it reports is the one a client
compared against to get here.
"""

from . import PROFILE_ID
from pas.plugins.identity.server.browser.discovery import DiscoveryView
from pas.plugins.identity.server.browser.discovery import JSONView
from pas.plugins.identity.server.browser.discovery import JWKSView
from pas.plugins.identity.server.browser.discovery import WellKnownView
from pas.plugins.identity.server.discovery import DISCOVERY_DOCUMENT
from pas.plugins.identity.server.discovery import metadata
from pas.plugins.identity.server.grants.tokens import ISSUER_RECORD
from pas.plugins.identity.server.grants.tokens import mint_id_token
from pas.plugins.identity.server.utils.keys import ALGORITHM
from pas.plugins.identity.server.utils.keys import get_keys
from pas.plugins.identity.server.utils.keys import rotate_keys
from plone import api
from zExceptions import NotFound

import base64
import json
import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])

ISSUER = "https://id.example.org"


@pytest.fixture
def issuer(portal):
    """Configure the issuer, without which nothing describes itself."""
    api.portal.set_registry_record(ISSUER_RECORD, ISSUER)
    return ISSUER


def render(view_class, portal):
    """Render a JSON view and return ``(status, body)``.

    :param view_class: The view to construct.
    :param portal: The Plone site.
    :returns: Status code and decoded JSON body.
    """
    request = portal.REQUEST
    body = view_class(portal, request)()
    return request.response.getStatus(), json.loads(body)


class TestTheDocument:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, issuer) -> None:
        self.portal = portal
        self.doc = metadata()

    def test_the_issuer_is_the_configured_one(self):
        """A client compares this to the URL it fetched the document from,
        byte for byte, and refuses the document if they differ."""
        assert self.doc["issuer"] == ISSUER

    def test_every_endpoint_is_under_the_issuer(self):
        """Not under the portal URL. A proxy, a virtual host or a trailing
        slash would otherwise be enough to send a client somewhere its own
        issuer check then rejects."""
        for key in (
            "authorization_endpoint",
            "token_endpoint",
            "userinfo_endpoint",
            "jwks_uri",
        ):
            assert self.doc[key].startswith(ISSUER), key

    def test_it_advertises_the_algorithm_actually_used(self):
        assert self.doc["id_token_signing_alg_values_supported"] == [ALGORITHM]

    def test_it_advertises_only_s256(self):
        """`plain` is in RFC 7636 and worth nothing: it puts the verifier in
        the authorization request, which is what PKCE protects."""
        assert self.doc["code_challenge_methods_supported"] == ["S256"]

    def test_it_advertises_the_grants_the_token_endpoint_serves(self):
        from pas.plugins.identity.server.browser.token import GRANT_TYPES

        assert set(self.doc["grant_types_supported"]) == set(GRANT_TYPES)

    def test_it_advertises_the_scopes_the_claims_module_knows(self):
        from pas.plugins.identity.server.claims import SCOPE_CLAIMS

        assert set(self.doc["scopes_supported"]) == {"openid", *SCOPE_CLAIMS}

    def test_only_the_code_flow_is_offered(self):
        """OAuth 2.1 removes the implicit grant and this server has no reason
        to put a token in a URL fragment."""
        assert self.doc["response_types_supported"] == ["code"]

    def test_subjects_are_public(self):
        """`sub` is the Plone userid and every relying party sees the same
        one. Pairwise subjects would need a per-client mapping this server
        does not keep."""
        assert self.doc["subject_types_supported"] == ["public"]

    def test_it_is_byte_stable(self):
        """A client that caches the document and diffs it on change should
        see a change only when one happened."""
        assert json.dumps(metadata()) == json.dumps(metadata())


class TestServingIt:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_the_document_is_served(self, issuer):
        status, body = render(DiscoveryView, self.portal)

        assert status == 200
        assert body["issuer"] == ISSUER

    def test_an_unconfigured_server_says_so(self):
        """503 and a named error rather than a traceback. This is a site that
        has not finished being set up, and saying that is the difference
        between a five-minute fix and a bug report against this package."""
        status, body = render(DiscoveryView, self.portal)

        assert status == 503
        assert body["error"] == "server_not_configured"

    def test_well_known_traverses_to_the_document(self, issuer):
        """The path has a slash in it, so a view cannot be registered under
        the whole name; `.well-known` is the view and the document is
        traversed into it."""
        view = WellKnownView(self.portal, self.portal.REQUEST).publishTraverse(
            self.portal.REQUEST, DISCOVERY_DOCUMENT
        )

        assert isinstance(view, DiscoveryView)

    def test_an_unknown_well_known_document_is_not_found(self):
        """A 404 rather than an empty document: a client that asked for
        something else should discover that plainly."""
        view = WellKnownView(self.portal, self.portal.REQUEST)

        with pytest.raises(NotFound):
            view.publishTraverse(self.portal.REQUEST, "host-meta")

    def test_the_well_known_directory_is_not_a_document(self):
        view = WellKnownView(self.portal, self.portal.REQUEST)

        with pytest.raises(NotFound):
            view()


class TestTheJSONBase:
    """The shared base both published documents are rendered by."""

    def test_it_has_no_document_of_its_own(self, portal):
        """A subclass that forgets to say what it publishes fails loudly
        rather than serving an empty body that reads like a configuration
        problem somewhere else."""
        with pytest.raises(NotImplementedError):
            JSONView(portal, portal.REQUEST).document()


class TestTheJWKS:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, issuer) -> None:
        self.portal = portal

    def test_it_publishes_a_key(self):
        _status, body = render(JWKSView, self.portal)

        assert len(body["keys"]) == 1

    def test_it_publishes_no_private_material(self):
        """The whole point of the asymmetric ring: a relying party verifies
        with this and must never be handed anything it could sign with."""
        _status, body = render(JWKSView, self.portal)

        for private in ("d", "p", "q", "dp", "dq", "qi"):
            assert private not in body["keys"][0], private

    def test_every_key_in_the_ring_is_published(self):
        """A relying party holding a token minted before the last rotation
        still has to be able to verify it, and finds the key by `kid`."""
        rotate_keys()

        _status, body = render(JWKSView, self.portal)

        assert len(body["keys"]) == len(get_keys()) == 2

    def test_the_signing_key_is_findable_by_kid(self):
        """The link between a token's header and this document. Without it a
        relying party has to try every key, and with a rotated ring that is
        how intermittent verification failures start."""
        token = mint_id_token("app", "alice")
        encoded = token.split(".")[0]
        header = json.loads(
            base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        )

        _status, body = render(JWKSView, self.portal)

        assert header["kid"] in {key["kid"] for key in body["keys"]}
