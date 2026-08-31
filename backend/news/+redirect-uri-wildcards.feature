A client's redirect URIs may carry a wildcard, in two positions.

Registering every host a site answers on, one at a time, is the thing this avoids. `https://*.example.org/callback` stands for exactly one further label — `app.example.org`, and deliberately not `a.b.example.org` nor the bare `example.org`. `https://example.org/*` stands for any path on that host, and any query string with it. The two combine.

A registration without a `*` is unchanged: compared as a string and nothing else, because matching a redirect URI is what binds an authorization code to the client it was issued for. No prefix matching, no ignoring the query string, no treating a trailing slash as equivalent.

The refusals are the more important half. A `*` is rejected in a port, a user name, a query string, in the middle of a label such as `https://a*.example.org`, in the middle of a path, and directly under a public suffix such as `https://*.com` — which would hand every site with such a name a valid redirect target. The scheme and the port are never widened, so a wildcard registration cannot be downgraded to plain HTTP.

This is a deliberate widening, and the documentation says so plainly: every name a wildcard covers is somewhere this server will send a browser carrying an authorization code, so a subdomain that is taken over, forgotten, or serving somebody else's content is a valid target for as long as the registration stands. Érico asked for it knowing that, because listing hosts one by one is its own kind of mistake. @ericof
