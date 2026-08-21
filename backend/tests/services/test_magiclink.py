"""Integration tests for magic-link login (Gate 3, S5/S2/S4).

Mail is captured in process by ``collective.MockMailHost``, so the whole
round trip -- request a link, read it out of the message, redeem it -- runs
without a mail server anywhere.
"""

from .conftest import body
from datetime import datetime
from datetime import timedelta
from datetime import UTC
from pas.plugins.identity.core.audit import MAGIC_LINK_CONFIRMED
from pas.plugins.identity.core.audit import MAGIC_LINK_REFUSED
from pas.plugins.identity.core.audit import MAGIC_LINK_SENT
from pas.plugins.identity.core.controlpanel import get_providers
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.flows import magiclink
from pas.plugins.identity.core.services.magiclink import MagicLinkConfirm
from pas.plugins.identity.core.services.magiclink import MagicLinkSend
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from plone import api
from urllib.parse import parse_qs
from urllib.parse import urlparse

import email
import pytest


#: The address the tests log in as.
ADDRESS = "erico@plone.org"

#: The email provider record.
EMAIL_PROVIDER_RECORD = {
    "id": "email",
    "driver": "email",
    "title": "Email",
    "enabled": True,
    "config": {"token_ttl": 900, "rate_limit_per_hour": 5},
}


@pytest.fixture()
def email_configured(portal, configured):
    """Add the email provider alongside the Dex fixture."""
    set_providers([
        *get_providers(),
        ProviderConfig.deserialize(EMAIL_PROVIDER_RECORD),
    ])


@pytest.fixture()
def mailbox(portal):
    """Return a reader over the captured mail, emptied first."""
    mailhost = api.portal.get_tool("MailHost")
    mailhost.reset()

    def read() -> list:
        """Return the captured messages, parsed.

        :returns: Parsed messages, oldest first.
        """
        return [
            email.message_from_bytes(raw, policy=email.policy.default)
            for raw in mailhost.messages
        ]

    return read


def send(portal, request_, **payload) -> dict:
    """POST a magic-link request.

    :param portal: The Plone site.
    :param request_: The current request.
    :param payload: The JSON body.
    :returns: The service's reply.
    """
    body(request_, payload)
    return MagicLinkSend(portal, request_).reply()


def confirm(portal, request_, **payload) -> dict:
    """POST a magic-link confirmation.

    :param portal: The Plone site.
    :param request_: The current request.
    :param payload: The JSON body.
    :returns: The service's reply.
    """
    body(request_, payload)
    return MagicLinkConfirm(portal, request_).reply()


def token_from(messages) -> str:
    """Pull the magic-link token out of a captured message.

    :param messages: Parsed messages.
    :returns: The token.
    """
    text = messages[-1].get_content()
    url = next(word for word in text.split() if "magic_link=" in word)
    return parse_qs(urlparse(url).query)["magic_link"][0]


class TestSending:
    def test_sends_a_message(self, portal, request_, email_configured, mailbox):
        """The whole point: an email arrives."""
        result = send(portal, request_, email=ADDRESS)

        assert result == {"sent": True}
        assert len(mailbox()) == 1

    def test_message_is_addressed_to_the_caller(
        self, portal, request_, email_configured, mailbox
    ):
        """And to the address that was asked for."""
        send(portal, request_, email=ADDRESS)

        assert ADDRESS in mailbox()[0]["To"]

    def test_message_carries_a_usable_link(
        self, portal, request_, email_configured, mailbox
    ):
        """The link points at the configured callback route."""
        send(portal, request_, email=ADDRESS)

        text = mailbox()[0].get_content()
        assert "magic_link=" in text
        assert magiclink.verify(token_from(mailbox()))["sub"] == ADDRESS

    def test_unknown_address_answers_identically(
        self, portal, request_, email_configured, mailbox
    ):
        """No account enumeration: a stranger's address looks the same as a
        member's, from the outside."""
        known = send(portal, request_, email=ADDRESS)
        stranger = send(portal, request_, email="nobody@example.com")

        assert known == stranger == {"sent": True}

    def test_address_is_required(self, portal, request_, email_configured):
        """A send to nowhere is not a request."""
        send(portal, request_)

        assert request_.response.getStatus() == 400

    def test_obvious_nonsense_is_refused(self, portal, request_, email_configured):
        """Not validation for its own sake -- it keeps the rate-limit buckets
        from filling with junk keys."""
        send(portal, request_, email="not-an-address")

        assert request_.response.getStatus() == 400

    def test_without_the_provider_it_is_unavailable(self, portal, request_, configured):
        """A site that has not enabled magic-link login says so."""
        send(portal, request_, email=ADDRESS)

        assert request_.response.getStatus() == 404

    def test_send_is_audited(self, portal, request_, email_configured, log, mailbox):
        """An operator can see that links are going out."""
        send(portal, request_, email=ADDRESS)

        assert log.entries()[0].event == MAGIC_LINK_SENT

    def test_audit_does_not_record_the_address(
        self, portal, request_, email_configured, log, mailbox
    ):
        """D7 -- who asked for a link is personal data, and the entry is
        useful without it."""
        send(portal, request_, email=ADDRESS)

        assert ADDRESS not in str(log.entries()[0].serialize())


class TestRateLimiting:
    """S5 -- the send endpoint is the one an attacker can make Plone send
    mail from."""

    def test_per_address_limit_trips(self, portal, request_, email_configured, mailbox):
        """Five links an hour for one address, then no more."""
        for _ in range(5):
            send(portal, request_, email=ADDRESS)

        send(portal, request_, email=ADDRESS)

        assert request_.response.getStatus() == 429
        assert len(mailbox()) == 5

    def test_limit_is_per_address(self, portal, request_, email_configured, mailbox):
        """One address being throttled does not throttle another."""
        for _ in range(5):
            send(portal, request_, email=ADDRESS)

        send(portal, request_, email="someone-else@plone.org")

        assert request_.response.getStatus() == 200

    def test_per_ip_limit_trips(self, portal, request_, email_configured, mailbox):
        """An attacker enumerating mailboxes uses a fresh address every time
        and would never trip the per-address counter."""
        request_.environ["REMOTE_ADDR"] = "203.0.113.7"

        for index in range(magiclink.DEFAULT_IP_RATE_LIMIT):
            send(portal, request_, email=f"user{index}@plone.org")

        send(portal, request_, email="one-more@plone.org")

        assert request_.response.getStatus() == 429

    def test_refusal_is_audited(self, portal, request_, email_configured, log):
        """Being throttled is worth seeing; it is also not an oracle, since
        it says nothing about whether the address exists."""
        for _ in range(6):
            send(portal, request_, email=ADDRESS)

        refusals = [e for e in log.entries() if e.event == MAGIC_LINK_REFUSED]
        assert refusals and refusals[0].detail["reason"] == "rate limited"

    def test_window_expires(self, portal, request_, email_configured, mailbox):
        """The limit is a rate, not a quota: it recovers."""
        store = api.portal.get_tool("acl_users")["identity"].magic_links
        for _ in range(5):
            send(portal, request_, email=ADDRESS)
        stale = datetime.now(UTC) - magiclink.RATE_WINDOW - timedelta(minutes=1)
        store._requests[f"address:{ADDRESS}"] = [stale] * 5

        send(portal, request_, email=ADDRESS)

        assert request_.response.getStatus() == 200


class TestConfirming:
    @pytest.fixture()
    def token(self, portal, request_, email_configured, mailbox) -> str:
        """Request a link and return its token."""
        send(portal, request_, email=ADDRESS)
        return token_from(mailbox())

    def test_round_trip_yields_a_token(self, portal, request_, token):
        """The Gate 3 check: request a link, click it, be logged in."""
        result = confirm(portal, request_, token=token)

        assert result["token"]

    def test_creates_the_identity(self, portal, request_, token):
        """The address becomes an identity this site verified itself."""
        confirm(portal, request_, token=token)

        plugin = api.portal.get_tool("acl_users")["identity"]
        assert plugin.store.userid_for(EMAIL_PROVIDER, ADDRESS) is not None

    def test_second_login_is_the_same_user(
        self, portal, request_, email_configured, mailbox
    ):
        """I1 -- a returning human keeps their userid."""
        plugin = api.portal.get_tool("acl_users")["identity"]
        send(portal, request_, email=ADDRESS)
        confirm(portal, request_, token=token_from(mailbox()))
        first = plugin.store.userid_for(EMAIL_PROVIDER, ADDRESS)

        send(portal, request_, email=ADDRESS)
        confirm(portal, request_, token=token_from(mailbox()))

        assert plugin.store.userid_for(EMAIL_PROVIDER, ADDRESS) == first

    def test_confirm_is_audited(self, portal, request_, token, log):
        """Against the userid it resolved to."""
        confirm(portal, request_, token=token)

        assert log.entries()[0].event == MAGIC_LINK_CONFIRMED

    def test_token_is_single_use(self, portal, request_, token):
        """S5 -- a link forwarded, or sitting in a shared inbox, is worth one
        login and not a permanent key."""
        confirm(portal, request_, token=token)

        confirm(portal, request_, token=token)

        assert request_.response.getStatus() == 401

    def test_reuse_is_audited(self, portal, request_, token, log):
        """And the second click leaves a trace."""
        confirm(portal, request_, token=token)
        confirm(portal, request_, token=token)

        refusals = [e for e in log.entries() if e.event == MAGIC_LINK_REFUSED]
        assert refusals[0].detail["reason"] == "Magic link has already been used"

    def test_expired_token_is_refused(self, portal, request_, email_configured):
        """S5 -- the TTL is enforced by authlib, not by hope."""
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

        confirm(portal, request_, token=stale)

        assert request_.response.getStatus() == 401

    def test_forged_token_is_refused(self, portal, request_, email_configured):
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

        confirm(portal, request_, token=forged)

        assert request_.response.getStatus() == 401

    def test_token_for_another_purpose_is_refused(
        self, portal, request_, email_configured
    ):
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

        confirm(portal, request_, token=other)

        assert request_.response.getStatus() == 401

    def test_token_is_required(self, portal, request_, email_configured):
        """A confirmation without a token is not a request."""
        confirm(portal, request_)

        assert request_.response.getStatus() == 400

    def test_without_the_provider_it_is_unavailable(self, portal, request_, configured):
        """Confirming on a site that disabled magic-link login."""
        confirm(portal, request_, token="anything")

        assert request_.response.getStatus() == 404

    def test_refusals_read_identically(self, portal, request_, token):
        """Expired, forged, reused and wrong-purpose all look the same from
        outside; the audit log carries the difference."""
        confirm(portal, request_, token=token)
        first = confirm(portal, request_, token=token)
        second = confirm(portal, request_, token="not-even-a-token")

        assert first == second


class TestSatisfiesTheUnlinkGuard:
    """S4 -- a verified email identity is one of the ways out."""

    def test_email_identity_permits_unlinking_the_provider(
        self, portal, request_, email_configured, mailbox
    ):
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


class TestAutoLinkByEmail:
    """S2 -- the attack this exists to prevent, and the case it enables."""

    @pytest.fixture()
    def existing(self, portal, request_, email_configured, mailbox) -> str:
        """Create an account via magic link and return its userid."""
        send(portal, request_, email=ADDRESS)
        confirm(portal, request_, token=token_from(mailbox()))
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

    def test_off_by_default(self, portal, existing):
        """S2 -- a matching verified address does *not* attach unless the
        operator asked for it."""
        userid = self._login({"email": ADDRESS, "email_verified": True})

        assert userid != existing

    def test_opt_in_attaches_to_the_verified_account(self, portal, existing):
        """With it on, the same human keeps one account."""
        self._set_auto_link(True)

        userid = self._login({"email": ADDRESS, "email_verified": True})

        assert userid == existing

    def test_unverified_claim_cannot_attach(self, portal, existing):
        """The S2 attack: a provider account registered with somebody else's
        address, which the provider has *not* verified."""
        self._set_auto_link(True)

        userid = self._login({"email": ADDRESS, "email_verified": False})

        assert userid != existing

    def test_absent_verified_flag_cannot_attach(self, portal, existing):
        """A provider that simply does not say is not saying yes."""
        self._set_auto_link(True)

        userid = self._login({"email": ADDRESS})

        assert userid != existing

    @pytest.mark.parametrize("value", ["true", 1, "True", "yes"])
    def test_truthy_is_not_true(self, portal, existing, value):
        """Only a literal ``True`` counts, exactly as in the driver layer."""
        self._set_auto_link(True)

        userid = self._login({"email": ADDRESS, "email_verified": value})

        assert userid != existing

    def test_matches_only_our_own_verified_identities(self, portal, existing):
        """S2 -- the match is against an address *this site* proved with a
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

    def test_attached_identity_is_new_but_user_is_not(self, portal, existing):
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
