"""``@magic-link`` and ``@magic-link-confirm``.

``POST @magic-link`` with ``{"email": "..."}``
    Sends a login link, and answers the same way whether or not the address
    is known. Anything else turns the endpoint into a way to ask Plone which
    addresses have accounts.

``POST @magic-link-confirm`` with ``{"token": "..."}``
    Validates the token, burns it, and either answers with a ``jwt_auth``
    token or attaches the address to the caller's account -- whichever the
    token was minted for.

The identity this proves is ``("email", <address>)``, and it is verified by
construction: the only way to hold the token is to have received the mail.
That is what lets it satisfy the unlink guard, and it is *not* the same thing
as a provider claiming ``email_verified`` about the same address.

Sending lives here rather than in ``post.py`` because two endpoints mail a
link now -- ``@magic-link`` to sign somebody in, ``@identities`` to confirm a
mailbox for somebody already signed in -- and the rate limiting is the part
that must not diverge. Without it this package is an open relay aimed at
anybody's inbox, and a second send path that forgot to count would be exactly
that, however careful the first one is.
"""

from email.message import EmailMessage
from pas.plugins.identity.core.controlpanel import enabled_providers
from pas.plugins.identity.core.controlpanel import get_callback_url
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.flows import magiclink
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from plone import api
from urllib.parse import urlencode
from ZPublisher.HTTPRequest import HTTPRequest


#: Subject line of the login mail.
SUBJECT = "Your sign-in link"

#: The mail body. Deliberately plain: an HTML mail with a disguised link is
#: the shape of a phishing message, and this one asks somebody to click.
BODY = """\
Someone asked to sign in to {site} as {address}.

Use this link within {minutes} minutes:

{url}

The link works once. If you did not ask for it, ignore this message -- it
cannot be used unless it is clicked, and nobody else received it.
"""

#: Subject line of the address-confirmation mail.
LINK_SUBJECT = "Confirm your email address"

#: The confirmation body. It names the account, which the login mail cannot:
#: this one is only ever sent to somebody who is already signed in, so there
#: is no address to enumerate and a recipient who did not ask for it needs to
#: know whose account was involved.
LINK_BODY = """\
Someone signed in to {site} as {userid} asked to add {address} as a way to
sign in.

Use this link within {minutes} minutes:

{url}

The link works once, and only in the session that asked for it. If you did
not ask for this, ignore this message -- nothing has been added to the
account.
"""


def get_provider_config() -> ProviderConfig | None:
    """Return the configured email provider, if there is one.

    :returns: The provider, or ``None`` when magic-link login is not enabled.
    """
    for provider in enabled_providers():
        if provider.driver_id == EMAIL_PROVIDER:
            return provider
    return None


def client_ip(request: HTTPRequest) -> str:
    """Return the caller's address for rate-limiting purposes.

    Not stored anywhere: this is a bucket key, and the bucket is swept an
    hour later. Recording it in the audit log is a separate, opt-in decision.

    :param request: The current request.
    :returns: The client IP, or an empty string when there is none.
    """
    return (
        (request.get("HTTP_X_FORWARDED_FOR") or request.get("REMOTE_ADDR") or "")
        .split(",")[0]
        .strip()
    )


def check_rate_limits(config: JSONDict, address: str, request: HTTPRequest) -> None:
    """Count one send against both buckets, refusing over either limit.

    :param config: The email provider's configuration.
    :param address: The address being mailed.
    :param request: The current request, for the IP bucket.
    :raises RateLimited: When either bucket is over its limit.
    """
    store = api.portal.get_tool("acl_users")[PLUGIN_ID].magic_links
    store.check_and_record(
        f"address:{address}",
        int(config.get("rate_limit_per_hour") or magiclink.DEFAULT_RATE_LIMIT),
    )
    store.check_and_record(
        f"ip:{client_ip(request)}",
        int(config.get("ip_rate_limit_per_hour") or magiclink.DEFAULT_IP_RATE_LIMIT),
    )


def send_link(address: str, token: str, ttl: int, userid: str | None = None) -> None:
    """Post a magic link.

    :param address: Where to send it.
    :param token: The magic-link token.
    :param ttl: Lifetime in seconds, for the human-readable text.
    :param userid: The account the address is being added to, when this is a
        confirmation rather than a login.
    """
    portal = api.portal.get()
    url = f"{get_callback_url()}?{urlencode({'magic_link': token})}"
    subject = SUBJECT if userid is None else LINK_SUBJECT
    template = BODY if userid is None else LINK_BODY
    message = EmailMessage()
    message["Subject"] = subject
    message["To"] = address
    message.set_content(
        template.format(
            site=portal.Title(),
            address=address,
            userid=userid,
            minutes=max(1, ttl // 60),
            url=url,
        )
    )
    api.portal.send_email(
        recipient=address,
        subject=subject,
        body=message.get_content(),
    )
