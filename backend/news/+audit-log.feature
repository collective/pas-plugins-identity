Added the audit log: a bounded per-user record of authentication events, stored inside the PAS plugin and purged on write against registry-configured limits for entry count and age. Successes are recorded from the event contract, so anything that fires an event is audited whoever fired it; refused callbacks are recorded by the callback service in an unattributed bucket, because being refused is precisely what leaves them with no userid.

The IP address and user agent are personal data and are stored only when `pas.plugins.identity.audit_record_pii` is switched on, which it is not by default. Credentials, tokens and authorization codes are never recorded at all. The sink is a utility, so a deployment can send entries somewhere else.

`GET @audit-log` reads it. The default scope is the caller's own authentication events; reading another user's, or the site-wide log including the refusals that could not be attributed to anybody, needs `Manage portal`. @ericof
