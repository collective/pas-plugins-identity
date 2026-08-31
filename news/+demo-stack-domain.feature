The demo stack's two hostnames follow `DEMO_STACK_DOMAIN`, defaulting to `localhost`.

`id.localhost` and `plone.localhost` were written out eighteen times — Traefik's routing rules, the virtual-host rewrites that tell Zope what URL it is answering, the network aliases that make one hostname resolve in the browser and in a container, the issuer, and the redirect URI. Changing the domain meant changing all of them consistently, and the failure mode for missing one is an issuer that does not match itself.

Google will not register a redirect URI on a `.localhost` host, which is what makes this more than tidiness: pointing `id.` and `plone.` at 127.0.0.1 in `/etc/hosts` and exporting `DEMO_STACK_DOMAIN` is now enough to run the whole demo under a domain a real provider will accept. The default is unchanged, so `make demo-stack-start` needs no DNS and no hosts file. @ericof
