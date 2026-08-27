"""The authorization endpoint.

A browser view rather than a plone.restapi service, because this endpoint is
not consumed by the frontend: it is where a relying party sends a *browser*,
and what it returns is a redirect. The rest of this package's HTTP surface
answers JSON to Volto; this one answers 302 to whatever OAuth client the site
has been configured for.

The error handling is the part worth reading. RFC 6749 splits failures in two,
and the split is a security boundary rather than a nicety:

* If the client id or the redirect URI cannot be trusted, the error is shown
  *here*. Redirecting would mean sending the error -- and whatever the caller
  put in ``state`` -- to a URI this server has not verified, which is an open
  redirect wearing a specification as a hat.
* Every other failure goes back to the registered redirect URI as
  ``error=...``, because by then the destination is known-good and the client
  is the thing that needs to hear about it.

The consent screen sits at the end of that validation, not the start of it. A
user should never be shown a form asking them to approve a request that was
going to be refused anyway -- and a form rendered before the redirect URI is
verified would be a phishing page this server hosts on the client's behalf.
Consent is remembered per user and client, so the prompt appears once and on
any later request for a scope not already agreed to.
"""

from AccessControl import Unauthorized
from pas.plugins.identity.core.interfaces import IProfileSupport
from pas.plugins.identity.server.clients import get_client
from pas.plugins.identity.server.codes import ChallengeError
from pas.plugins.identity.server.codes import check_challenge
from pas.plugins.identity.server.consent_screen import consent_screen_url
from pas.plugins.identity.server.discovery import AUTHORIZE_VIEW
from pas.plugins.identity.server.pas import PLUGIN_ID
from plone import api
from plone.protect.authenticator import AuthenticatorView
from plone.protect.authenticator import createToken
from plone.protect.interfaces import IDisableCSRFProtection
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from urllib.parse import urlencode
from zExceptions import Forbidden
from zope.component import queryUtility
from zope.interface import alsoProvides

import html


#: The only response type this server supports. Implicit and hybrid flows are
#: out: OAuth 2.1 removes the implicit grant, and this server has no reason to
#: put a token in a URL fragment.
RESPONSE_TYPE = "code"

#: Request parameters the consent form posts back, so the authorization
#: request survives the round trip without any server-side state.
CARRIED_PARAMS = (
    "response_type",
    "client_id",
    "redirect_uri",
    "scope",
    "state",
    "code_challenge",
    "code_challenge_method",
    "nonce",
)

#: The form value that means yes. Anything else -- "deny", a missing value, a
#: button a future template adds -- is a refusal. Consent is the thing that
#: has to be given explicitly, so it is the only value spelled out.
CONSENT_ALLOW = "allow"

#: The OIDC ``prompt`` value that forbids any interaction with the end user.
#: Supported now rather than with the rest of OIDC because it is what keeps
#: ``login_required`` and ``consent_required`` meaningful: without it, an
#: authorization server that redirects to a login page has no way to be asked
#: *not* to, and those two error codes become unreachable.
PROMPT_NONE = "none"

#: Query parameter carrying the request to resume once a profile is finished.
#:
#: Deliberately **not** ``return_url``. That name belongs to Volto: its edit
#: form reads it and pushes it through the router after a save, and an
#: absolute URL pushed that way is resolved against the current path -- so
#: handing it this request produced a navigation to
#: ``/profiles/<id>/http:/id.localhost/@@oauth-authorize`` and two 404s in
#: front of the user before the real redirect caught up. The frontend reads
#: this name instead and navigates properly.
RESUME_PARAM = "identity_resume"

#: Returned by the consent check when the user has not been asked yet. A
#: sentinel rather than ``None`` because ``None`` is already a perfectly good
#: answer to "did they agree", and confusing "no" with "not yet" here would
#: mean silently denying every first-time authorization.
CONSENT_PENDING = object()


class AuthorizationError(Exception):
    """A failure that must be reported to the client, not to the browser.

    :ivar error: The RFC 6749 error code.
    :ivar description: A human-readable explanation, safe to hand back.
    """

    def __init__(self, error: str, description: str) -> None:
        """Record an error to redirect back to the client.

        :param error: The RFC 6749 error code.
        :param description: A human-readable explanation. Required: an error
            code on its own tells a client integrator nothing, and every
            failure here has something specific to say.
        """
        super().__init__(description)
        self.error = error
        self.description = description


class AuthorizeView(BrowserView):
    """Issue an authorization code to a registered client."""

    consent_form = ViewPageTemplateFile("templates/consent.pt")

    #: The client this request is for, once it has been verified. The consent
    #: template reads it; nothing before the verification does.
    client = None

    def _param(self, name: str) -> str:
        """Return a request parameter as a stripped string.

        :param name: Parameter name.
        :returns: The value, or the empty string when absent.
        """
        return (self.request.form.get(name) or "").strip()

    def __call__(self) -> str:
        """Handle an authorization request.

        :returns: An error page when the client or redirect URI cannot be
            trusted, the consent form when the user has not answered yet, and
            otherwise the empty string, having set a redirect.
        """
        # This endpoint is reached by a cross-site redirect by design, so
        # plone.protect's automatic CSRF handling must not rewrite it into a
        # confirmation page. Nothing here writes on GET except the code store,
        # which is the whole point of the endpoint.
        alsoProvides(self.request, IDisableCSRFProtection)

        client_id = self._param("client_id")
        redirect_uri = self._param("redirect_uri")

        client = get_client(client_id)
        if client is None or not client.enabled:
            return self._refuse(
                "Unknown client",
                f"No enabled client is registered as {client_id!r}.",
            )
        if not client.check_redirect_uri(redirect_uri):
            return self._refuse(
                "Unregistered redirect URI",
                "The redirect_uri does not exactly match one registered for "
                "this client.",
            )

        self.client = client
        state = self._param("state")
        try:
            location = self._authorize(client, redirect_uri)
        except AuthorizationError as exc:
            params = {"error": exc.error, "error_description": exc.description}
            if state:
                params["state"] = state
            location = f"{redirect_uri}?{urlencode(params)}"
        else:
            if location is None:
                # The user is being asked. Nothing has been issued, nothing
                # has been recorded, and the client hears from us when they
                # answer.
                elsewhere = consent_screen_url()
                if not elsewhere:
                    return self.consent_form()
                # A frontend renders the question instead, in the site's own
                # look. The request travels in the query string exactly as it
                # travels through the hidden fields of the form below, and
                # the answer comes back to this same endpoint: whichever
                # screen asked, the decision is made in one place and every
                # check runs again on the way out.
                self.request.response.redirect(
                    f"{elsewhere}?{urlencode(self.carried_params())}",
                    status=302,
                )
                return ""

        self.request.response.redirect(location, status=302)
        return ""

    def _authorize(self, client, redirect_uri: str) -> str:
        """Validate the rest of the request and issue a code.

        :param client: The registered client.
        :param redirect_uri: The verified redirect URI.
        :returns: The URL to redirect the browser to, or ``None`` when the
            user still has to be asked and the consent form should be
            rendered instead. That URL is usually the client's redirect URI,
            and is the user's own profile when the request cannot proceed
            until they have finished it.
        :raises AuthorizationError: For any failure the client should be told
            about at its redirect URI.
        :raises Unauthorized: When the end user is not signed in and the
            client has not forbidden interaction. Plone's challenge machinery
            takes it from there.
        """
        challenge, scope = self._check_request(client)
        quiet = self._param("prompt") == PROMPT_NONE

        user = api.user.get_current()
        if api.user.is_anonymous():
            if quiet:
                raise AuthorizationError(
                    "login_required",
                    "The end user is not authenticated at the authorization "
                    "server, and prompt=none forbids asking them.",
                )
            # Anything else means: go and log them in. Raising Unauthorized
            # hands that to Plone's own challenge machinery rather than
            # reimplementing it -- which matters, because the stock challenge
            # carries the query string into `came_from` and sanitises it to a
            # local URL. This whole request *is* its query string, and
            # sanitising a return URL is exactly the thing not to write twice.
            raise Unauthorized(
                "The end user must authenticate before authorizing a client."
            )

        # Before consent, not after. A site that requires an email address
        # should not release claims about a user who has not given one, and an
        # identity provider is where that insistence belongs -- the relying
        # party cannot enforce it and should not have to.
        #
        # Asked through the utility core declares, so this layer never imports
        # the one that owns the idea. No utility, or no answer, means nothing
        # here is incomplete.
        support = queryUtility(IProfileSupport)
        elsewhere = (
            support.incomplete_profile_url(user.getId())
            if support is not None
            else None
        )
        if elsewhere:
            if quiet:
                raise AuthorizationError(
                    "interaction_required",
                    "The end user must complete their profile before this "
                    "request can be authorized, and prompt=none forbids "
                    "asking them.",
                )
            # Paused, exactly as it is while they sign in: the client is told
            # nothing yet and hears from us when the browser comes back. The
            # return trip is the whole request, carried the same way the
            # consent screen carries it.
            return f"{elsewhere}?{urlencode({RESUME_PARAM: self.request_url()})}"

        plugin = api.portal.get_tool("acl_users")[PLUGIN_ID]
        decision = self._consent_decision(plugin, user.getId(), client, scope)
        if decision is CONSENT_PENDING:
            if quiet:
                raise AuthorizationError(
                    "consent_required",
                    "The end user has not agreed to this request, and "
                    "prompt=none forbids asking them.",
                )
            # The caller gets the form instead of a redirect. Raising would
            # send an error to the client; returning None says "this request
            # has not finished yet, and the browser is being asked a
            # question".
            return None
        if not decision:
            raise AuthorizationError(
                "access_denied",
                "The end user refused the request.",
            )

        codes = plugin.codes
        code = codes.issue(
            client_id=client.client_id,
            subject=user.getId(),
            redirect_uri=redirect_uri,
            scope=scope,
            challenge=challenge,
            nonce=self._param("nonce"),
        )
        params = {"code": code}
        state = self._param("state")
        if state:
            # Echoed verbatim and never interpreted: it is the client's CSRF
            # token, and this server's only job is to hand it back unchanged.
            params["state"] = state
        return f"{redirect_uri}?{urlencode(params)}"

    def _check_request(self, client) -> tuple[str, str]:
        """Validate everything about the request that the client controls.

        Split out from :meth:`_authorize` because these are the checks that
        happen before any human is involved: nothing here reads a session,
        and every failure is something the client got wrong.

        :param client: The registered client.
        :returns: The PKCE challenge to record, and the requested scope.
        :raises AuthorizationError: For any failure the client should be told
            about at its redirect URI.
        """
        if self._param("response_type") != RESPONSE_TYPE:
            raise AuthorizationError(
                "unsupported_response_type",
                "Only the authorization code flow is supported.",
            )
        if not client.allows_grant("authorization_code"):
            raise AuthorizationError(
                "unauthorized_client",
                "This client is not registered for the authorization code grant.",
            )

        try:
            challenge = check_challenge(
                self._param("code_challenge"),
                self._param("code_challenge_method"),
                required=client.requires_pkce,
            )
        except ChallengeError as exc:
            raise AuthorizationError("invalid_request", str(exc)) from exc

        scope = self._param("scope")
        extra = set(scope.split()) - client.scopes()
        if extra:
            raise AuthorizationError(
                "invalid_scope",
                f"The client is not registered for: {' '.join(sorted(extra))}.",
            )
        return challenge, scope

    def _consent_decision(self, plugin, userid: str, client, scope: str):
        """Decide whether the user has agreed to this request.

        Three answers, and the middle one is why this is not a boolean. The
        user has agreed before and need not be asked; the user is answering
        right now; or the user has not been asked at all, which is
        :data:`CONSENT_PENDING`.

        :param plugin: The server PAS plugin, holding the consent store.
        :param userid: The authenticated user.
        :param client: The verified client.
        :param scope: The requested scope.
        :returns: ``True`` to proceed, ``False`` for a refusal, or
            :data:`CONSENT_PENDING` to render the form.
        :raises Forbidden: When a consent form comes back without a valid
            CSRF token. Silently treating that as a denial would be friendlier
            and wrong: a forged consent POST is an attempt to authorize an
            application in somebody else's name, and it should look like the
            attack it is rather than like the user clicking "no".
        """
        answer = self._param("consent")
        if not answer:
            if plugin.consent.granted(userid, client.client_id, scope):
                return True
            return CONSENT_PENDING

        if not AuthenticatorView(self.context, self.request).verify():
            raise Forbidden("The consent form's authenticator is invalid.")
        if answer != CONSENT_ALLOW:
            return False
        plugin.consent.record(userid, client.client_id, scope)
        return True

    # ------------------------------------------------------------------
    # Consent template
    # ------------------------------------------------------------------

    def client_title(self) -> str:
        """Return what to call the client on the consent screen.

        :returns: The registered title, falling back to the client id. A
            client registered without a title is still something the user has
            to be able to identify, and its id is what the operator typed.
        """
        return self.client.title or self.client.client_id

    def user_label(self) -> str:
        """Return how to name the signed-in user on the consent screen.

        Shown because the browser may hold a session the user forgot about,
        and agreeing on behalf of the wrong account is the mistake this
        screen exists to make visible.

        :returns: Their full name, or their userid when they have none.
        """
        user = api.user.get_current()
        return user.getProperty("fullname", "") or user.getId()

    def scope_list(self) -> list[str]:
        """Return the requested scopes, for display.

        :returns: The scopes in the order the client asked for them, which is
            the order it will have documented them in.
        """
        return self._param("scope").split()

    def form_action(self) -> str:
        """Return where the consent form posts back to.

        Itself: the second request re-runs every check the first one did, so
        a client disabled between the question and the answer is refused on
        the way out as surely as on the way in.

        :returns: The endpoint URL.
        """
        return f"{self.context.absolute_url()}/@@oauth-authorize"

    def request_url(self) -> str:
        """Return this authorization request, as a URL to come back to.

        Rebuilt from the carried parameters rather than read off the request,
        for the reason :meth:`carried_params` exists: the browser is going to
        be sent somewhere else and has to be able to resume *this* request,
        and a parameter dropped on the way is a different request.

        :returns: An absolute URL.
        """
        query = urlencode(self.carried_params())
        return f"{self.context.absolute_url()}/{AUTHORIZE_VIEW}?{query}"

    def carried_params(self) -> dict[str, str]:
        """Return the authorization request, for a round trip through a screen.

        :returns: One entry per parameter that was actually sent. Absent
            parameters are left absent rather than carried as empty: an empty
            ``code_challenge`` is not the same request as no
            ``code_challenge``, and PKCE turns on that difference.
        """
        return {name: self._param(name) for name in CARRIED_PARAMS if self._param(name)}

    def form_fields(self) -> list[dict]:
        """Return the authorization request, as hidden form fields.

        :returns: One mapping per carried parameter, in the shape the
            template's ``<input type="hidden">`` loop wants.
        """
        return [
            {"name": name, "value": value}
            for name, value in self.carried_params().items()
        ]

    def authenticator_token(self) -> str:
        """Return a CSRF token for the consent form.

        :returns: A plone.protect token, bound to the current user.
        """
        return createToken()

    def _refuse(self, title: str, detail: str) -> str:
        """Report a failure that must not be redirected anywhere.

        :param title: Short heading.
        :param detail: Explanation.
        :returns: A minimal HTML page.
        """
        self.request.response.setStatus(400)
        self.request.response.setHeader("Content-Type", "text/html; charset=utf-8")
        # Both halves are escaped: `detail` quotes the client_id the caller
        # sent, and this page is rendered precisely when that value is not
        # one this server has agreed to trust.
        title = html.escape(title)
        detail = html.escape(detail)
        return (
            "<!DOCTYPE html><html><head><title>Authorization request "
            f"refused</title></head><body><h1>{title}</h1><p>{detail}</p>"
            "<p>This error is shown here rather than sent back, because the "
            "request did not establish a destination this server trusts.</p>"
            "</body></html>"
        )
