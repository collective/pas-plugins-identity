"""Integration tests for linking an email address to an existing account.

The same token machinery as magic-link login, aimed at a different outcome:
the holder of the mailbox is not signed in as a result, they are *added* to
the account that asked. What separates the two is the token's purpose, and
most of what follows is about keeping them separated -- a confirmation link
that could sign somebody in would be a takeover, not a feature.
"""

from .. import body
from . import ADDRESS
from . import token_from
from pas.plugins.identity.core.audit import LINK_COLLISION
from pas.plugins.identity.core.audit import LINK_REFUSED
from pas.plugins.identity.core.audit import MAGIC_LINK_SENT
from pas.plugins.identity.core.flows import magiclink
from pas.plugins.identity.core.interfaces import FlowError
from pas.plugins.identity.core.services.identities.get import IdentitiesGet
from pas.plugins.identity.core.services.identities.post import IdentitiesPost
from pas.plugins.identity.core.services.magiclink.confirm import MagicLinkConfirm
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from plone import api
from plone.app.testing import login
from plone.app.testing import logout

import pytest


class EmailLinkCase:
    """Drives the two halves of the email-linking flow."""

    def claim_address(self, address: str = ADDRESS) -> None:
        """Put an address on the caller's own profile.

        The precondition for verifying one. A magic link proves control of
        whatever was typed, so ``POST @identities`` will only send one to an
        address already named on the profile -- otherwise the endpoint
        verifies any mailbox, and a verified address is what
        ``auto_link_by_email`` attaches a new provider account to.

        :param address: The address to claim.
        """
        from pas.plugins.identity.core.subscribers import get_profile
        from zope.lifecycleevent import modified

        profile = get_profile(self.member)
        profile.emails = (*profile.emails, address)
        modified(profile)

    def start_link(self, **payload) -> dict:
        """POST a linking start to ``@identities``.

        :param payload: The JSON body.
        :returns: The service's reply.
        """
        body(self.request, payload)
        return IdentitiesPost(self.portal, self.request).reply()

    def confirm(self, **payload) -> dict:
        """POST to ``@magic-link-confirm``.

        :param payload: The JSON body.
        :returns: The service's reply.
        """
        body(self.request, payload)
        return MagicLinkConfirm(self.portal, self.request).reply()

    def listing(self) -> dict:
        """GET the caller's identities.

        :returns: The service's reply.
        """
        return IdentitiesGet(self.portal, self.request).reply()

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


class TestStartingALink(EmailLinkCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, member, email_configured, mailbox, log) -> None:
        self.portal = portal
        self.request = request_
        self.member = member
        self.mailbox = mailbox
        self.log = log
        self.claim_address()

    def test_answers_a_send_rather_than_an_authorize_url(self):
        """The defect this whole flow exists to fix: the email provider has
        no authorization endpoint, so a client asking to link it used to get
        a 502 describing an outage that was not happening."""
        result = self.start_link(provider="email", email=ADDRESS)

        assert self.status() == 200
        assert result == {"provider": "email", "sent": True}

    def test_sends_one_message_to_the_address(self):
        """The address named, not the one ``email`` currently resolves to:
        proving control of a mailbox is the entire point, and a profile with
        several addresses has several to prove."""
        self.claim_address("other@plone.org")

        self.start_link(provider="email", email="other@plone.org")

        messages = self.mailbox()
        assert len(messages) == 1
        assert "other@plone.org" in messages[0]["To"]

    def test_an_address_that_is_not_yours_is_refused(self):
        """What replaced the free-text box on the identities page. A magic
        link proves control of whatever was typed, so an unguarded endpoint
        verifies *any* mailbox -- and a verified address is what
        ``auto_link_by_email`` attaches a new provider account to."""
        result = self.start_link(provider="email", email="stranger@plone.org")

        assert self.status() == 400
        assert result["error"]["type"] == "Not one of your addresses"
        assert self.mailbox() == []

    def test_the_mail_names_the_account(self):
        """Unlike the login mail, which cannot: this one only ever goes to
        somebody already signed in, so a recipient who did not ask for it can
        be told whose account was involved."""
        self.start_link(provider="email", email=ADDRESS)

        message = self.mailbox()[0]
        assert message["Subject"] == "Confirm your email address"
        assert self.member in message.get_content()

    def test_the_token_is_minted_for_linking(self):
        """Purpose and account both ride in the token."""
        self.start_link(provider="email", email=ADDRESS)

        claims = magiclink.verify(token_from(self.mailbox()), (magiclink.PURPOSE_LINK,))

        assert claims["purpose"] == magiclink.PURPOSE_LINK
        assert claims["link_for"] == self.member
        assert claims["sub"] == ADDRESS

    def test_the_token_cannot_be_used_to_log_in(self):
        """The guard the whole design rests on. A confirmation link that
        redeemed as a login would hand the account to whoever holds the
        mailbox -- which is the takeover this flow is supposed to prevent."""
        self.start_link(provider="email", email=ADDRESS)
        token = token_from(self.mailbox())

        with pytest.raises(FlowError):
            magiclink.verify(token)

    def test_an_address_is_required(self):
        """A provider with no authorization endpoint needs somewhere to send
        the link, and there is no sensible default -- least of all the
        address already on the account, which is the one *not* being
        proven."""
        result = self.start_link(provider="email")

        assert self.status() == 400
        assert result["error"]["type"] == "Missing parameters"

    def test_a_malformed_address_is_refused(self):
        """Refused before anything is mailed."""
        self.start_link(provider="email", email="not-an-address")

        assert self.status() == 400
        assert self.mailbox() == []

    def test_anonymous_cannot_start_one(self):
        """There is no account to link to."""
        logout()

        result = self.start_link(provider="email", email=ADDRESS)

        assert self.status() == 401
        assert result["error"]["type"] == "Not authenticated"
        assert self.mailbox() == []

    def test_sending_is_rate_limited(self):
        """The endpoint mails an arbitrary address on request, so it is an
        open relay without this. Authenticated callers are not exempt: an
        account is cheap and the mailbox being flooded belongs to somebody
        else."""
        for _ in range(5):
            self.start_link(provider="email", email=ADDRESS)

        result = self.start_link(provider="email", email=ADDRESS)

        assert self.status() == 429
        assert result["error"]["type"] == "Too many requests"
        assert len(self.mailbox()) == 5

    def test_the_send_is_audited_against_the_account(self):
        """Attributed, unlike a login send, which has nobody to attribute
        it to."""
        self.start_link(provider="email", email=ADDRESS)

        assert [e for e in self.log.entries() if e.event == MAGIC_LINK_SENT]


class TestRedeemingALink(EmailLinkCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, member, email_configured, mailbox, log) -> None:
        self.portal = portal
        self.request = request_
        self.member = member
        self.mailbox = mailbox
        self.log = log
        self.claim_address()

    def token_for(self, address: str = ADDRESS) -> str:
        """Start a link and return the token that was mailed.

        :param address: The address to prove.
        :returns: The token.
        """
        self.start_link(provider="email", email=address)
        return token_from(self.mailbox())

    def test_attaches_the_address_to_the_caller(self):
        """The whole point."""
        result = self.confirm(token=self.token_for())

        assert self.status() == 200
        assert result == {"linked": {"provider": EMAIL_PROVIDER, "subject": ADDRESS}}

    def test_the_identity_shows_up_in_the_listing(self):
        """Through the store, like any other identity -- not a special case
        the identities page would have to know about."""
        self.confirm(token=self.token_for())

        items = self.listing()["items"]

        linked = next(i for i in items if i["provider"] == EMAIL_PROVIDER)
        assert linked["subject"] == ADDRESS

    def test_no_token_is_issued(self):
        """Redeeming this proves a mailbox; it does not start a session. The
        caller already had one, and answering with a fresh JWT would be a way
        to escalate a stolen link into a login."""
        result = self.confirm(token=self.token_for())

        assert "token" not in result

    def test_another_user_cannot_complete_it(self):
        """A forwarded link, or one clicked in a browser signed in as
        somebody else, adds nothing to anybody."""
        token = self.token_for()
        with api.env.adopt_roles(["Manager"]):
            api.user.create(
                email="other@plone.org", username="other", password="s3cr3t-other"
            )
        login(self.portal, "other")

        result = self.confirm(token=token)

        assert self.status() == 403
        assert result["error"]["type"] == "Link refused"
        assert self.plugin().store.userid_for(EMAIL_PROVIDER, ADDRESS) is None

    def test_anonymous_cannot_complete_it(self):
        """Same refusal: the link names an account, and nobody is that
        account here."""
        token = self.token_for()
        logout()

        self.confirm(token=token)

        assert self.status() == 403
        assert self.plugin().store.userid_for(EMAIL_PROVIDER, ADDRESS) is None

    def test_a_refused_link_is_still_spent(self):
        """Burning happens before the session is checked. A link the wrong
        person clicked has been seen by the wrong person, and handing the
        right one a working retry would reward the forward."""
        token = self.token_for()
        logout()
        self.confirm(token=token)

        login(self.portal, "member")
        self.confirm(token=token)

        assert self.status() == 401
        assert self.plugin().store.userid_for(EMAIL_PROVIDER, ADDRESS) is None

    def test_a_refusal_is_audited(self):
        """An operator looking at a run of these is looking at somebody
        working through forwarded links."""
        token = self.token_for()
        logout()

        self.confirm(token=token)

        assert [e for e in self.log.entries() if e.event == LINK_REFUSED]

    def test_an_address_owned_by_someone_else_collides(self):
        """Never merge two people into one account."""
        with api.env.adopt_roles(["Manager"]):
            other = api.user.create(
                email="other@plone.org", username="other", password="s3cr3t-other"
            )
        self.plugin().link(other.getId(), EMAIL_PROVIDER, ADDRESS, {})

        result = self.confirm(token=self.token_for())

        assert self.status() == 409
        assert result["error"]["type"] == "Identity already linked"
        assert self.plugin().store.userid_for(EMAIL_PROVIDER, ADDRESS) == other.getId()

    def test_a_collision_is_audited(self):
        """With the subject, which is what an operator needs to see who
        already owns it."""
        with api.env.adopt_roles(["Manager"]):
            other = api.user.create(
                email="other@plone.org", username="other", password="s3cr3t-other"
            )
        self.plugin().link(other.getId(), EMAIL_PROVIDER, ADDRESS, {})

        self.confirm(token=self.token_for())

        assert [e for e in self.log.entries() if e.event == LINK_COLLISION]

    def test_the_link_works_only_once(self):
        """Single use, as for a login link."""
        token = self.token_for()
        self.confirm(token=token)

        self.confirm(token=token)

        assert self.status() == 401
