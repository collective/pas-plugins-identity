"""Integration tests for magic-link login.

Mail is captured in process by ``collective.MockMailHost``, so the whole
round trip -- request a link, read it out of the message, redeem it -- runs
without a mail server anywhere.

Linking an address to an account that is already signed in is the same token
machinery pointed at a different outcome, and lives in
``test_email_linking.py``.
"""

from .. import body
from . import ADDRESS
from . import token_from
from datetime import datetime
from datetime import timedelta
from datetime import UTC
from pas.plugins.identity.core.audit import MAGIC_LINK_CONFIRMED
from pas.plugins.identity.core.audit import MAGIC_LINK_REFUSED
from pas.plugins.identity.core.audit import MAGIC_LINK_SENT
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.flows import magiclink
from pas.plugins.identity.core.services.magiclink.confirm import MagicLinkConfirm
from pas.plugins.identity.core.services.magiclink.post import MagicLinkSend
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from plone import api

import pytest


class MagicLinkCase:
    """Drives the two halves of the magic-link flow."""

    def send(self, **payload) -> dict:
        """POST to ``@magic-link``.

        :param payload: The JSON body.
        :returns: The service's reply.
        """
        body(self.request, payload)
        return MagicLinkSend(self.portal, self.request).reply()

    def confirm(self, **payload) -> dict:
        """POST to ``@magic-link-confirm``.

        :param payload: The JSON body.
        :returns: The service's reply.
        """
        body(self.request, payload)
        return MagicLinkConfirm(self.portal, self.request).reply()

    def status(self) -> int:
        """Return the status the service answered with.

        :returns: The HTTP status.
        """
        return self.request.response.getStatus()


class TestSending(MagicLinkCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, email_configured, mailbox) -> None:
        self.portal = portal
        self.request = request_
        self.mailbox = mailbox

    def test_sends_a_message(self):
        """The whole point: an email arrives."""
        result = self.send(email=ADDRESS)

        assert result == {"sent": True}
        assert len(self.mailbox()) == 1

    def test_message_is_addressed_to_the_caller(self):
        """And to the address that was asked for."""
        self.send(email=ADDRESS)

        assert ADDRESS in self.mailbox()[0]["To"]

    def test_message_carries_a_usable_link(self):
        """The link points at the configured callback route."""
        self.send(email=ADDRESS)

        text = self.mailbox()[0].get_content()
        assert "magic_link=" in text
        assert magiclink.verify(token_from(self.mailbox()))["sub"] == ADDRESS

    def test_unknown_address_answers_identically(self):
        """No account enumeration: a stranger's address looks the same as a
        member's, from the outside."""
        known = self.send(email=ADDRESS)
        stranger = self.send(email="nobody@example.com")

        assert known == stranger == {"sent": True}

    def test_address_is_required(self):
        """A send to nowhere is not a request."""
        self.send()

        assert self.status() == 400

    def test_obvious_nonsense_is_refused(self):
        """Not validation for its own sake -- it keeps the rate-limit buckets
        from filling with junk keys."""
        self.send(email="not-an-address")

        assert self.status() == 400

    def test_send_is_audited(self, log):
        """An operator can see that links are going out."""
        self.send(email=ADDRESS)

        assert log.entries()[0].event == MAGIC_LINK_SENT

    def test_audit_does_not_record_the_address(self, log):
        """Who asked for a link is personal data, and the entry is
        useful without it."""
        self.send(email=ADDRESS)

        assert ADDRESS not in str(log.entries()[0].serialize())


class TestRateLimiting(MagicLinkCase):
    """The send endpoint is the one an attacker can make Plone send
    mail from."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, email_configured, mailbox) -> None:
        self.portal = portal
        self.request = request_
        self.mailbox = mailbox

    def test_per_address_limit_trips(self):
        """Five links an hour for one address, then no more."""
        for _ in range(5):
            self.send(email=ADDRESS)

        self.send(email=ADDRESS)

        assert self.status() == 429
        assert len(self.mailbox()) == 5

    def test_limit_is_per_address(self):
        """One address being throttled does not throttle another."""
        for _ in range(5):
            self.send(email=ADDRESS)

        self.send(email="someone-else@plone.org")

        assert self.status() == 200

    def test_per_ip_limit_trips(self):
        """An attacker enumerating mailboxes uses a fresh address every time
        and would never trip the per-address counter."""
        self.request.environ["REMOTE_ADDR"] = "203.0.113.7"

        for index in range(magiclink.DEFAULT_IP_RATE_LIMIT):
            self.send(email=f"user{index}@plone.org")

        self.send(email="one-more@plone.org")

        assert self.status() == 429

    def test_refusal_is_audited(self, log):
        """Being throttled is worth seeing; it is also not an oracle, since
        it says nothing about whether the address exists."""
        for _ in range(6):
            self.send(email=ADDRESS)

        refusals = [e for e in log.entries() if e.event == MAGIC_LINK_REFUSED]
        assert refusals and refusals[0].detail["reason"] == "rate limited"

    def test_window_expires(self):
        """The limit is a rate, not a quota: it recovers."""
        store = api.portal.get_tool("acl_users")["identity"].magic_links
        for _ in range(5):
            self.send(email=ADDRESS)
        stale = datetime.now(UTC) - magiclink.RATE_WINDOW - timedelta(minutes=1)
        store._requests[f"address:{ADDRESS}"] = [stale] * 5

        self.send(email=ADDRESS)

        assert self.status() == 200


class TestConfirming(MagicLinkCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, email_configured, mailbox) -> None:
        self.portal = portal
        self.request = request_
        self.mailbox = mailbox

    @pytest.fixture
    def token(self) -> str:
        """Request a link and return its token."""
        self.send(email=ADDRESS)
        return token_from(self.mailbox())

    def test_round_trip_yields_a_token(self, token):
        """The whole flow: request a link, click it, be logged in."""
        result = self.confirm(token=token)

        assert result["token"]

    def test_creates_the_identity(self, token):
        """The address becomes an identity this site verified itself."""
        self.confirm(token=token)

        plugin = api.portal.get_tool("acl_users")["identity"]
        assert plugin.store.userid_for(EMAIL_PROVIDER, ADDRESS) is not None

    def test_second_login_is_the_same_user(self):
        """A returning human keeps their userid."""
        plugin = api.portal.get_tool("acl_users")["identity"]
        self.send(email=ADDRESS)
        self.confirm(token=token_from(self.mailbox()))
        first = plugin.store.userid_for(EMAIL_PROVIDER, ADDRESS)

        self.send(email=ADDRESS)
        self.confirm(token=token_from(self.mailbox()))

        assert plugin.store.userid_for(EMAIL_PROVIDER, ADDRESS) == first

    def test_confirm_is_audited(self, token, log):
        """Against the userid it resolved to."""
        self.confirm(token=token)

        assert log.entries()[0].event == MAGIC_LINK_CONFIRMED

    def test_token_is_single_use(self, token):
        """A link forwarded, or sitting in a shared inbox, is worth one
        login and not a permanent key."""
        self.confirm(token=token)

        self.confirm(token=token)

        assert self.status() == 401

    def test_reuse_is_audited(self, token, log):
        """And the second click leaves a trace."""
        self.confirm(token=token)
        self.confirm(token=token)

        refusals = [e for e in log.entries() if e.event == MAGIC_LINK_REFUSED]
        assert refusals[0].detail["reason"] == "Magic link has already been used"

    def test_expired_token_is_refused(self):
        """The TTL is enforced by authlib, not by hope."""
        token, _ = magiclink.issue(ADDRESS, ttl=1)
        claims = magiclink.verify(token)
        assert claims["exp"] - claims["iat"] == 1
        # Rather than sleep, mint one that was already expired when issued.
        from authlib.jose import JsonWebToken

        now = datetime.now(UTC)
        stale = (
            JsonWebToken([magiclink.ALGORITHM])
            .encode(
                {"alg": magiclink.ALGORITHM},
                {
                    "sub": ADDRESS,
                    "jti": "stale",
                    "iat": int((now - timedelta(hours=2)).timestamp()),
                    "exp": int((now - timedelta(hours=1)).timestamp()),
                    "purpose": "magic-link",
                },
                magiclink.signing_keys()[0],
            )
            .decode("utf-8")
        )

        self.confirm(token=stale)

        assert self.status() == 401

    def test_forged_token_is_refused(self):
        """Signed by somebody else is not signed."""
        from authlib.jose import JsonWebToken

        forged = (
            JsonWebToken([magiclink.ALGORITHM])
            .encode(
                {"alg": magiclink.ALGORITHM},
                {
                    "sub": "attacker@evil.example",
                    "jti": "forged",
                    "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
                    "purpose": "magic-link",
                },
                b"not-our-key-at-all-not-even-close",
            )
            .decode("utf-8")
        )

        self.confirm(token=forged)

        assert self.status() == 401

    def test_token_for_another_purpose_is_refused(self):
        """A correctly signed token minted for something else must not be
        usable as a login."""
        from authlib.jose import JsonWebToken

        other = (
            JsonWebToken([magiclink.ALGORITHM])
            .encode(
                {"alg": magiclink.ALGORITHM},
                {
                    "sub": ADDRESS,
                    "jti": "other",
                    "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
                    "purpose": "something-else",
                },
                magiclink.signing_keys()[0],
            )
            .decode("utf-8")
        )

        self.confirm(token=other)

        assert self.status() == 401

    def test_token_is_required(self):
        """A confirmation without a token is not a request."""
        self.confirm()

        assert self.status() == 400

    def test_refusals_read_identically(self, token):
        """Expired, forged, reused and wrong-purpose all look the same from
        outside; the audit log carries the difference."""
        self.confirm(token=token)
        first = self.confirm(token=token)
        second = self.confirm(token="not-even-a-token")

        assert first == second


class TestSatisfiesTheUnlinkGuard(MagicLinkCase):
    """A verified email identity is one of the ways out."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, email_configured, mailbox) -> None:
        self.portal = portal
        self.request = request_
        self.mailbox = mailbox

    def test_email_identity_permits_unlinking_the_provider(self):
        """An OIDC-only account that adds a magic-link identity can then drop
        the provider without being locked out."""
        plugin = api.portal.get_tool("acl_users")["identity"]
        userid, _ = plugin.authenticateCredentials({
            "extractor": "pas.plugins.identity",
            "provider": "dex",
            "subject": "CgVlcmljbxIFbG9jYWw",
            "claims": {"email": ADDRESS, "email_verified": True},
        })
        assert plugin.can_unlink(userid, "dex", "CgVlcmljbxIFbG9jYWw") is False

        plugin.link(userid, EMAIL_PROVIDER, ADDRESS, {"email": ADDRESS})

        assert plugin.can_unlink(userid, "dex", "CgVlcmljbxIFbG9jYWw") is True
        assert plugin.has_verified_email(userid) is True


class TestAutoLinkByEmail(MagicLinkCase):
    """The attack this exists to prevent, and the case it enables."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, email_configured, mailbox) -> None:
        self.portal = portal
        self.request = request_
        self.mailbox = mailbox

    @pytest.fixture
    def existing(self) -> str:
        """Create an account via magic link and return its userid."""
        self.send(email=ADDRESS)
        self.confirm(token=token_from(self.mailbox()))
        return api.portal.get_tool("acl_users")["identity"].store.userid_for(
            EMAIL_PROVIDER, ADDRESS
        )

    def _login(self, claims: dict, subject: str = "provider-subject") -> str:
        """Authenticate an external identity and return its userid.

        :param claims: Claims the provider asserts.
        :param subject: Provider-side subject.
        :returns: The resolved userid.
        """
        plugin = api.portal.get_tool("acl_users")["identity"]
        userid, _ = plugin.authenticateCredentials({
            "extractor": "pas.plugins.identity",
            "provider": "dex",
            "subject": subject,
            "claims": claims,
        })
        return userid

    def _set_auto_link(self, value: bool) -> None:
        """Switch auto-link on or off for the Dex provider.

        :param value: The setting.
        """
        providers = get_providers()
        for provider in providers:
            if provider.provider_id == "dex":
                provider.config = {**provider.config, "auto_link_by_email": value}
        set_providers(providers)

    def test_off_by_default(self, existing):
        """A matching verified address does *not* attach unless the
        operator asked for it."""
        userid = self._login({"email": ADDRESS, "email_verified": True})

        assert userid != existing

    def test_opt_in_attaches_to_the_verified_account(self, existing):
        """With it on, the same human keeps one account."""
        self._set_auto_link(True)

        userid = self._login({"email": ADDRESS, "email_verified": True})

        assert userid == existing

    def test_unverified_claim_cannot_attach(self, existing):
        """The attack: a provider account registered with somebody else's
        address, which the provider has *not* verified."""
        self._set_auto_link(True)

        userid = self._login({"email": ADDRESS, "email_verified": False})

        assert userid != existing

    def test_absent_verified_flag_cannot_attach(self, existing):
        """A provider that simply does not say is not saying yes."""
        self._set_auto_link(True)

        userid = self._login({"email": ADDRESS})

        assert userid != existing

    @pytest.mark.parametrize("value", ["true", 1, "True", "yes"])
    def test_truthy_is_not_true(self, existing, value):
        """Only a literal ``True`` counts, exactly as in the driver layer."""
        self._set_auto_link(True)

        userid = self._login({"email": ADDRESS, "email_verified": value})

        assert userid != existing

    def test_matches_only_our_own_verified_identities(self, existing):
        """The match is against an address *this site* proved with a
        magic link, never against another provider's assertion."""
        self._set_auto_link(True)
        plugin = api.portal.get_tool("acl_users")["identity"]
        # A second provider claiming the address, but no email identity.
        other = plugin.store.userid_for(EMAIL_PROVIDER, "nobody@plone.org")
        assert other is None

        userid = self._login(
            {"email": "nobody@plone.org", "email_verified": True},
            subject="another-subject",
        )

        assert plugin.store.userid_for("dex", "another-subject") == userid
        assert userid != existing

    def test_attached_identity_is_new_but_user_is_not(self, existing):
        """The event must not claim a userid was minted when one was adopted."""
        from pas.plugins.identity.core.events import IExternalIdentityAuthenticated
        from zope.component import adapter
        from zope.component import getGlobalSiteManager
        from zope.interface import Interface

        self._set_auto_link(True)
        seen = []

        @adapter(Interface)
        def recorder(event):
            if IExternalIdentityAuthenticated.providedBy(event):
                seen.append(event)

        gsm = getGlobalSiteManager()
        gsm.registerHandler(recorder)
        try:
            self._login({"email": ADDRESS, "email_verified": True})
        finally:
            gsm.unregisterHandler(recorder)

        assert seen[0].is_new_user is False
        assert seen[0].is_new_identity is True


class TestWithoutTheEmailProvider(MagicLinkCase):
    """A site that never enabled magic-link login says so, on both halves."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, configured) -> None:
        self.portal = portal
        self.request = request_

    def test_sending_is_unavailable(self):
        """There is nothing to send from."""
        self.send(email=ADDRESS)

        assert self.status() == 404

    def test_confirming_is_unavailable(self):
        """And nothing that could have issued a token."""
        self.confirm(token="anything")

        assert self.status() == 404
