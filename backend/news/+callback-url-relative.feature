The login callback URL now accepts a path, and defaults to `/login-identity`.

A path is resolved against the portal URL, which under Volto is the origin the browser already uses; `/login-identity` is the route this package's own add-on registers, so a site that installs both halves needs no configuration at all. An absolute URL is still taken verbatim, for the deployment the setting was written for: the frontend and the backend need not share an origin, and no portal URL can describe one Plone is never reached on. A value that is neither is refused with a message naming the record, rather than becoming an opaque rejection from the provider.

Previously the record shipped empty and every sign-in failed at the last step with `No login callback URL is configured` -- a message only the backend log shows. @ericof
