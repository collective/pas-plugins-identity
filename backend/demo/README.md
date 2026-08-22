# identitydemo

The federation demo for `pas.plugins.identity`: two Plone sites, one of them
acting as the OAuth server for the other.

**This package is never published.** It carries a client secret and a user
password as literals in `settings.py`, both of which are in a public git
repository and therefore worthless as secrets. Both GenericSetup profiles
refuse to install unless `IDENTITY_DEMO` is set in the environment.

## Why it lives here rather than in `src/pas`

The wheel ships `src/pas` and nothing else, so a sibling package costs the
published add-on nothing. Keeping the demo out of `src/pas` is what stops
`pip install pas.plugins.identity` from carrying example content, fixed
credentials and a pair of profiles that should never appear in a real site's
`portal_setup`.

It is installed editable into the backend's own `.venv` by `make install-demo`,
which means one virtualenv, one ruff configuration and one mypy configuration —
the ones in `backend/pyproject.toml` already apply to these files.

It is *not* an `mx.ini` source, which was the first design. `Dockerfile` copies
the whole tree and runs mxdev over it, so a source section there would install
the demo into the production image and put these profiles in the `portal_setup`
of every deployment. The install is explicit at each of the two places that
want it: `make install-demo` and `Dockerfile.demo`.

The distribution name matches the import package exactly. `plone.autoinclude`
derives a module name from the distribution, so `identity-demo` would have it
looking for `identity_demo` and failing Zope startup.

uv workspaces would have been the obvious way to arrange this, and are the
wrong one: they are part of uv's managed-project interface, and this
repository sets `managed = false` and installs through mxdev against the
Plone constraints, as every backend in this family does.

## The two profiles

| Profile | Site | What it does |
|---|---|---|
| `identitydemo:idp` | A, `id.localhost` | Applies `core`, `profile` and `server`; registers the `demo-rp` client and the demo user. |
| `identitydemo:rp` | B, `plone.localhost` | Applies `core`; registers an `oidc-generic` provider pointed at A's issuer. |

One package and one Docker image, run twice under different `APPLY_PROFILES`.
The two sites differ in configuration, not in code.

## Running it

```bash
IDENTITY_DEMO=1 docker compose -f tests/federation/docker-compose.yml up
```

The issuer is published in A's discovery document, so A has to be reachable
under the same URL from the browser and from B's container. That is what the
`extra_hosts` entry on `rp` is for; it is also the first thing to check when
the flow half works.
