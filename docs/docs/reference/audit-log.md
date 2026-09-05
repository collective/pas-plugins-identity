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

## Where entries are written

A site records to every destination `audit_sinks` names, in the order it names them.

| Setting | Default | Meaning |
| --- | --- | --- |
| `audit_sinks` | `('plugin',)` | The destinations, in order. |

Three sinks ship.

`plugin`
:   The bounded per-user log inside the PAS plugin, described above. The default, and the only one a site records to until it says otherwise.

`log`
:   Writes one line per event to the `pas.plugins.identity.audit` logger and nothing else. Available on a plain install.

`sql`
:   Writes a row per event to a relational database. Needs the `[sql]` extra and `IDENTITY_AUDIT_DSN`.

Every destination listed gets every event. One that fails, or whose extra has been uninstalled since it was configured, is logged and stepped over rather than allowed to fail the sign-in it was auditing.

```{note}
The setting is a `Choice` over the sinks registered on the site, so a name that does not exist cannot be stored.
Installing an extra is what makes its sink choosable; naming it is what starts recording to it.
```

## Reading, and why it is a separate interface

Writing and reading are two interfaces, because not every destination can do both.

`IAuditSink`
:   `record`. All a destination has to promise.

`IAuditSource`
:   `entries`. Only a destination that can answer questions about what it holds.

The `log` sink provides the first and not the second: a log file is somewhere records go, not somewhere a Plone site can query. It has no `entries` at all, rather than one returning an empty list that every caller would read as nothing having happened.

Reads answer from the **first configured sink that provides `IAuditSource`**. So the order in `audit_sinks` decides which store the control panel and `@audit-log` show, and a site recording to both a database and the plugin log chooses by listing one first.

When nothing configured can be read back, `@audit-log` answers `"scope": "none"` rather than an empty list.

## Writing your own sink

Register a named utility. Provide `IAuditSource` as well if your destination can answer for what it holds.

```xml
<utility
    name="syslog"
    factory=".sinks.SyslogAuditSink"
    provides="pas.plugins.identity.core.interfaces.IAuditSink"
    />
```

Then add `syslog` to `audit_sinks`. Registering the utility installs it; naming it in the setting starts using it.

Recording is driven by events, so a sink sees everything any code fires, including yours.
See {doc}`events`.
