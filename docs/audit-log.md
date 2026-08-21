# The audit log

Every authentication event this package fires is recorded, along with the
refusals that fire no event at all.

:::{important}
This is an **authentication event log, not a session ledger**. It tells you
that somebody signed in at a time, from a provider, successfully or not. It
does not tell you whether they are still signed in, and it does not record
what they did afterwards. If you need either, you need something else.
:::

## Reading it

`GET @audit-log`
: Your own entries.

`GET @audit-log?userid=<id>`
: Somebody else's. Requires `Manage portal`.

`GET @audit-log?scope=site`
: Everything, including the refusals that could not be attributed to anybody
  — the view an operator investigating an attack wants. Requires
  `Manage portal`.

The default is deliberately the narrow one. A log that shows the whole site to
whoever asks is a list of who has accounts and when they last signed in.

## What is recorded

Event type, provider, timestamp, and whether it succeeded. Failures are
recorded as carefully as successes: an unknown identity, a login denied by a
provider's allowed-groups gate, and a link collision are three different
entries, and telling them apart is most of what the log is for.

Never recorded: credentials, tokens, or client secrets.

## Privacy and retention

IP address and user agent are **not** recorded unless you switch them on.

| Setting | Default |
| --- | --- |
| `audit_record_pii` | `False` |
| `audit_max_entries` | 500 per user |
| `audit_max_days` | 180 |

The log is bounded per user and purged on write, so it cannot grow without
limit and there is no cron job to forget to install.

:::{note}
Enabling `audit_record_pii` stores personal data. Under the GDPR and the LGPD
that is a processing decision with consequences — a lawful basis, a retention
period you can justify, and an answer for a subject access request. The
default is off so that the decision is one you make rather than one you
inherit.
:::

## Sending entries somewhere else

The default sink writes into a bounded per-user log inside the plugin. A
deployment that wants entries in a SIEM registers its own `IAuditSink`
utility, overriding the default:

```xml
<utility
    factory=".sinks.SyslogAuditSink"
    provides="pas.plugins.identity.core.interfaces.IAuditSink"
    />
```

Because recording is driven by {doc}`events`, a sink sees everything any code
fires — including yours.
