"""The userinfo endpoint.

Where a relying party asks who the access token speaks for.

This view validates the Bearer token itself rather than relying on the PAS
plugin that would also authenticate it, and the reason is the change that
landed alongside: an unauthenticated request to a protected Plone view now
gets a *login page*, because that is what an authorization server owes a
browser. A relying party's back-channel GET is not a browser and cannot read
an HTML login form; RFC 6750 says it should get ``401`` with a
``WWW-Authenticate: Bearer`` header naming the problem. So this endpoint is
public, and does its own checking.

The token's scope decides what comes back. A token minted without the
``openid`` scope gets ``sub`` and nothing else -- it is a token for reaching
an API as somebody, not a token for learning who they are.
"""

from pas.plugins.identity.server.claims import claims_for
from pas.plugins.identity.server.controlpanel.clients import get_client
from pas.plugins.identity.server.grants.tokens import decode_access_token
from pas.plugins.identity.server.grants.tokens import TOKEN_TYPE
from pas.plugins.identity.server.grants.tokens import TokenError
from Products.Five.browser import BrowserView

import json


#: The scheme this endpoint accepts, lowercased for a case-insensitive
#: comparison: RFC 7235 makes the scheme token case-insensitive.
BEARER_PREFIX = f"{TOKEN_TYPE} ".lower()


class UserInfoView(BrowserView):
    """Return the claims an access token releases."""

    def _token(self) -> str:
        """Return the Bearer token presented with the request.

        Read off ``request._auth`` because ZPublisher moves the
        ``Authorization`` header there during request construction and takes
        it out of the environment.

        :returns: The token, or the empty string when none was presented.
        """
        header = getattr(self.request, "_auth", None) or ""
        if not header.lower().startswith(BEARER_PREFIX):
            return ""
        return header[len(BEARER_PREFIX) :].strip()

    def __call__(self) -> str:
        """Answer with the claims, or refuse.

        :returns: A JSON body.
        """
        response = self.request.response
        response.setHeader("Content-Type", "application/json")
        # The answer is about one person and one token. A shared cache
        # holding it would hand one relying party another's user.
        response.setHeader("Cache-Control", "no-store")

        token = self._token()
        if not token:
            return self._refuse(response, 401, "invalid_request")

        try:
            claims = decode_access_token(token)
        except TokenError:
            return self._refuse(response, 401, "invalid_token")

        client = get_client(claims.get("aud", ""))
        if client is None or not client.enabled:
            # The same audience check the Bearer plugin makes. With no
            # denylist (D3), unregistering a client is this server's only
            # revocation, and it has to apply here too or userinfo becomes
            # the one endpoint a withdrawn client keeps reaching.
            return self._refuse(response, 401, "invalid_token")

        return json.dumps(claims_for(claims["sub"], claims.get("scope", "")))

    def _refuse(self, response, status: int, error: str) -> str:
        """Refuse the request the way RFC 6750 asks.

        :param response: The HTTP response.
        :param status: HTTP status code.
        :param error: The RFC 6750 error code.
        :returns: The JSON body.
        """
        response.setStatus(status)
        # No error_description, and one code for every rejection: an expired
        # token, a forged one and one issued to a client since removed are
        # indistinguishable from out here, exactly as at the token endpoint.
        response.setHeader("WWW-Authenticate", f'{TOKEN_TYPE} error="{error}"')
        return json.dumps({"error": error})
