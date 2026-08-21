"""REST API services for the login flow (Gate 1).

The flow is driven by the frontend, not by the backend:

1. Volto GETs ``@login-providers`` to render the login buttons.
2. Clicking one GETs ``@login-providers/<id>``, which starts the flow and
   answers with the URL to send the browser to.
3. The provider redirects back to a **route in Volto** -- the configured
   callback URL -- which reads ``code`` and ``state`` off the query string.
4. Volto POSTs those to ``@identity-callback``, which finishes the flow and
   answers with a ``jwt_auth`` token.

Step 3 is why the redirect URI is configuration and not something derived
from the portal URL: the frontend and the backend need not share an origin,
and providers match the registered redirect URI exactly.
"""
