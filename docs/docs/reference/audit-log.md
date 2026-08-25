---
myst:
  html_meta:
    "description": "Audit log endpoints, recorded fields, retention settings, and the sink interface."
    "property=og:description": "Audit log endpoints, recorded fields, retention settings, and the sink interface."
    "property=og:title": "The audit log"
---

(reference-audit-log)=

# The audit log

The package records every authentication event it fires, along with the refusals that fire no event at all.

```{important}
This is an authentication event log, not a session ledger.
It tells you that somebody signed in at a time, from a provider, successfully or not.
It does not tell you whether they are still signed in, and it does not record what they did afterward.
If you need either, you need something else.
```

For how to query it, see {doc}`/how-to-guides/read-the-audit-log`.

## Endpoints

| Endpoint | Returns | Permission |
| --- | --- | --- |
| `GET @audit-log` | Your own entries. | Authenticated |
| `GET @audit-log?userid=<id>` | One user's entries. | `Manage portal` |
| `GET @audit-log?scope=site` | Every entry, including refusals attributed to nobody. | `Manage portal` |

The default is deliberately the narrow one.
A log that shows the whole site to whoever asks is a list of who has accounts and when they last signed in.

## Recorded fields

Every entry records the event type, the provider, the timestamp, and whether the attempt succeeded.

Failures are recorded as carefully as successes.
An unknown identity, a sign-in denied by a provider's allowed-groups gate, and a link collision are three different entries, and telling them apart is most of what the log is for.

The log never records credentials, tokens, or client secrets.

IP address and user agent are recorded only when `audit_record_pii` is on.

## Settings

| Setting | Default | Effect |
| --- | --- | --- |
| `audit_record_pii` | `False` | Records IP address and user agent. |
| `audit_max_entries` | `500` | Entries kept per user. |
| `audit_max_days` | `180` | Age at which an entry is discarded. |

The log is bounded per user and purged on write, so it cannot grow without limit and there is no cron job to forget to install.

```{warning}
Enabling `audit_record_pii` stores personal data.
Under the GDPR and the LGPD that is a processing decision with consequences: a lawful basis, a retention period you can justify, and an answer for a subject access request.
The default is off so that the decision is one you make rather than one you inherit.
```

## The sink interface

The default sink writes into a bounded per-user log inside the plugin.

A deployment that wants entries elsewhere registers its own `IAuditSink` utility, which overrides the default:

```xml
<utility
    factory=".sinks.SyslogAuditSink"
    provides="pas.plugins.identity.core.interfaces.IAuditSink"
    />
```

Recording is driven by events, so a sink sees everything any code fires, including yours.
See {doc}`events`.
