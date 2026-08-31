"""Issuing an access token writes nothing to the ZODB.

The claim the self-encoded token design was chosen for, and the reason
authorization codes and refresh tokens -- which genuinely must be single-use
-- are the only things the ``[server]`` layer persists. If minting an access
token wrote, a site serving API traffic would be committing a transaction per
request, and the token endpoint's write frequency would follow *API call*
frequency rather than *human login* frequency.

Measured, not asserted, in the same shape as the profile catalog's
zero-wake test:

* a **write counter** patched over ``ZODB.Connection.register``, the single
  funnel every object marked changed goes through;
* a **self-check** proving the counter registers a real write, without which
  a count of zero would prove only that the patch was in the wrong place;
* a **scaling check**, because "zero" is a claim about the shape of the cost
  and one request cannot show a shape.

The assertion turned out to be stronger than the claim needed. It is not that this
layer's stores are untouched while something else writes -- a token request
registers *nothing at all*, so there is no transaction to commit. The counter
is therefore unfiltered: naming the classes to watch for would have meant
guessing which ones, and the first guess was wrong (writes land on the
stores' internal BTrees, not on the store objects), which is a good reason
not to guess at all.
"""

from . import ISSUER
from . import PROFILE_ID
from . import SERVICE_USER
from pas.plugins.identity.server.browser.token import TokenView
from pas.plugins.identity.server.grants.tokens import ISSUER_RECORD
from pas.plugins.identity.server.pas import PLUGIN_ID
from plone import api

import json
import pytest
import transaction
import ZODB.Connection


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


#: How many tokens to mint when checking that the cost does not scale.
BATCH = 20


@pytest.fixture
def writes(monkeypatch):
    """Count objects marked changed, by class name.

    ``Connection.register`` is where every object joins the transaction as
    modified, so patching it catches a write however it was triggered.

    :param monkeypatch: pytest's patcher.
    :returns: A list that accumulates class names as objects are registered.
    """
    recorded: list[str] = []
    original = ZODB.Connection.Connection.register

    def counting_register(self, obj):
        """Record the write and delegate.

        :param self: The ZODB connection.
        :param obj: The object being marked changed.
        """
        recorded.append(type(obj).__name__)
        return original(self, obj)

    monkeypatch.setattr(ZODB.Connection.Connection, "register", counting_register)
    return recorded


@pytest.fixture
def service_client(portal, add_client):
    """A client that can mint tokens with no human involved."""
    api.portal.set_registry_record(ISSUER_RECORD, ISSUER)
    with api.env.adopt_roles(["Manager"]):
        api.user.create(
            email="svc@example.org",
            username=SERVICE_USER,
            password="not-used-by-this-grant",
        )
    _client, secret = add_client(
        "indexer",
        grant_types=["client_credentials"],
        scope="read",
        public=False,
        service_user=SERVICE_USER,
    )
    # Without this the measurement is worthless, and silently so. An object
    # created in the current transaction has no oid yet, so changing it joins
    # the transaction through ``Connection.add`` rather than
    # ``Connection.register`` -- the counter below sees nothing, every
    # assertion of "no writes" passes, and none of them mean anything. The
    # savepoint gives the stores oids, which is the state they are in during
    # any real request. The self-check class exists because this is exactly
    # the kind of mistake a green test suite hides.
    transaction.savepoint(optimistic=True)
    return secret


def mint(portal, secret: str) -> dict:
    """Run one client-credentials token request.

    :param portal: The Plone site.
    :param secret: The client secret.
    :returns: The decoded response body.
    """
    request = portal.REQUEST
    request.form.clear()
    request.form.update({
        "grant_type": "client_credentials",
        "client_id": "indexer",
        "client_secret": secret,
    })
    request.environ["REQUEST_METHOD"] = "POST"
    return json.loads(TokenView(portal, request)())


class TestTheCounterItself:
    """Without this, a count of zero proves only that nothing was patched."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, service_client, writes) -> None:
        self.portal = portal
        self.writes = writes

    def test_it_sees_a_write_this_layer_makes(self):
        """Issuing an authorization *code* does write -- that is the whole
        reason codes are the thing this layer persists."""
        api.portal.get_tool("acl_users")[PLUGIN_ID].codes.issue(
            "indexer", SERVICE_USER, "https://app.example.org/cb"
        )

        assert self.writes

    def test_it_sees_a_refresh_token_write(self):
        """The other persistent store, for the same reason."""
        api.portal.get_tool("acl_users")[PLUGIN_ID].refresh.issue(
            "indexer", SERVICE_USER
        )

        assert self.writes


class TestAccessTokensWriteNothing:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, service_client, writes) -> None:
        self.portal = portal
        self.secret = service_client
        self.writes = writes

    def test_the_request_actually_produced_a_token(self):
        """Guarding the measurement: a refused request writes nothing either,
        and would make every assertion below pass for the wrong reason."""
        assert mint(self.portal, self.secret)["access_token"]

    def test_one_issuance_writes_nothing(self):
        mint(self.portal, self.secret)

        assert self.writes == []

    def test_many_issuances_write_nothing(self):
        """The claim in one line. Twenty tokens, no transaction to commit."""
        for _ in range(BATCH):
            mint(self.portal, self.secret)

        assert self.writes == []

    def test_the_cost_does_not_scale_with_issuance(self):
        """The shape of the claim rather than its value. Even if some
        unrelated part of Plone wrote once during the first request, the
        twentieth must not add to it -- that is the difference between a
        constant and a per-call cost."""
        mint(self.portal, self.secret)
        after_one = len(self.writes)

        for _ in range(BATCH):
            mint(self.portal, self.secret)

        assert len(self.writes) == after_one
