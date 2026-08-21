# Human actions

Things this package needs that only a person can do. Each one is blocking
something, and each says what.

---

## Before anything is pushed

### Decide whether there is a remote

**Blocks: every gate being GREEN.**

A gate is GREEN when it has passed CI twice consecutively. There is no remote
configured, deliberately — so the CI matrix, the extras jobs, the clean-install
check, the docs build and the Dex flow tests have **never run on a runner**.
Everything in this repository is verified locally only.

Nothing here can change that. Adding the remote and pushing is a decision about
when this becomes public.

Expect first-run surprises in `extras`, `clean_install` and the Dex jobs
specifically: those three have the most environment in them and the least
local coverage of the environment they will actually meet.

---

## Before any public release

### Replace the security reporting address

**Blocks: `SECURITY.md` being true.**

`SECURITY.md` and `docs/security.md` both carry `security@example.org` as a
placeholder, marked TODO. A security policy that names an address nobody reads
is worse than no policy, because it looks like a channel.

### Verify or drop C9

**Blocks: nothing. Affects: how the README positions this package.**

C9 is the claim that `Products.membrane`'s user-properties plugin wakes content
objects. It was asserted from memory in a docstring during Gate 6b and has been
withdrawn — see `DECISIONS.md`. Neither the code nor the documentation makes
the claim now.

If it should be made, somebody has to read membrane's `userproperties` plugin
and measure it. Until then the README says only what this package's own tests
prove.

### Run the OpenID conformance suite

**Blocks: the `[server]` extra being deployable.**

S8 requires it and it is not something a test suite substitutes for. Not
relevant until the server track ships.

---

## Deployment decisions

### Provider avatars

Off by default. Turning them on makes the login path fetch a URL the user may
control. `docs/profiles.md` explains the exposure and the guards. This is a
deployment decision with a security consequence, not a preference.

### Audit log PII

IP address and user agent are not recorded unless switched on. Enabling it
stores personal data, which under the GDPR and the LGPD needs a lawful basis, a
justifiable retention period, and an answer for a subject access request.

### Provider credentials

Client secrets are omitted from GenericSetup export by design, so an export is
not enough to rebuild a working site. The secrets have to travel by whatever
means your deployment already uses for secrets.

---

## Open questions for the maintainer

### Gate 7 scope

The Gate 7 spike is written up in `DECISIONS.md`. Three forks came out of it
that are scope decisions rather than technical ones:

1. **Test dependencies.** Migration fixtures need `pas.plugins.authomatic` and
   `pas.plugins.oidc` installed in the test extra. That is two more packages in
   the CI matrix, both of which pull their own dependencies.

2. **A per-provider subject claim.** Sites that changed oidc's
   `user_property_as_userid` away from `sub` cannot be migrated correctly
   without it, because the `sub` was never stored. Adding it changes a core
   driver signature that Gate 1 code and tests depend on.

3. **The authomatic-compatible callback route (C8).** Feasible, and it is what
   makes the migration zero-touch for provider redirect URIs. It is also a
   second entry point into the flow with its own security surface.
