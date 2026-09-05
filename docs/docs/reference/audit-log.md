---
myst:
  html_meta:
    "description": "Audit log event names, endpoints, recorded fields, retention settings, and the sink interfaces."
    "property=og:description": "Audit log event names, endpoints, recorded fields, retention settings, and the sink interfaces."
    "property=og:title": "The audit log"
---

(reference-audit-log)=

# The audit log

<!-- source: backend/src/pas/plugins/identity/core/audit/ -->

The package records every authentication event it fires, along with the refusals
that fire no event at all.

```{important}
This is an authentication event log, not a session ledger. It tells you that
somebody signed in at a time, from a provider, successfully or not. It does not
tell you whether they are still signed in, and it does not record what they did
afterward.
```

For how to query it, see {doc}`/how-to-guides/read-the-audit-log`.

## Event names

Stable strings, so a consumer can filter on them.

### Successes

| Event | Recorded when |
|---|---|
| `authenticated` | An external authentication succeeded. Detail carries `subject`, `is_new_user`, `is_new_identity`. |
| `identity-linked` | An identity was attached to an existing account. Detail carries `subject`. |
| `identity-unlinked` | An identity was detached. Detail carries `subject`. |
| `email-verified` | An address was proven. Detail carries `address`—**stored regardless of the PII flag**, because an entry that will not say which address was verified is useless. |
| `claims-refreshed` | Stored claims were refreshed on a later login. The claims themselves are not recorded. |
| `magic-link-sent` | A single-use link was sent. |
| `magic-link-confirmed` | A link was redeemed. |

### Refusals

| Event | Recorded when |
|---|---|
| `flow-refused` | The credential did not check out: an unusable `state`, a replayed code, a rejected `id_token`, or a provider that cannot start the flow. |
| `payload-rejected` | The provider answered, and its payload could not be read. Answers `502`. |
| `signin-refused` | The provider authenticated the person and **this site's policy** refused them: outside every allowed group, or a new account at a provider not allowed to create one. |
| `link-refused` | A linking flow was completed by a different session than the one that started it. Answers `403`. |
| `link-collision` | The identity is already linked to a different userid. Answers `409`. Two people are never merged into one account. |
| `magic-link-refused` | A magic-link send or redemption was refused. |

`flow-refused` and `signin-refused` are deliberately distinct. A run of the first
is somebody failing to authenticate; a run of the second is your own
configuration.

## Endpoints

| Endpoint | Returns | Requires |
|---|---|---|
| `GET @audit-log` | The caller's own entries. | authenticated |
| `GET @audit-log?userid=<id>` | One user's entries. | `Manage portal` |
| `GET @audit-log?scope=site` | Every entry, including refusals attributed to nobody. | `Manage portal` |

The default is deliberately the narrow one: a log that shows the whole site to
whoever asks is a list of who has accounts and when they last signed in.

When nothing configured can be read back, `@audit-log` answers `"scope": "none"`
rather than an empty list.

## What an entry holds

| Field | Always? |
|---|---|
| Event name | yes |
| Provider id | yes |
| Timestamp | yes |
| Success | yes |
| Detail | per event, as tabulated above |
| IP address, user agent | **only when `audit_record_pii` is on** |

The log never records credentials, tokens, or client secrets.

A refusal that could not be attributed to anybody is stored against an internal
unattributed key and is visible only under `scope=site`.

## Settings

| Setting | Default | Effect |
|---|---|---|
| `audit_record_pii` | `False` | Records IP address and user agent. |
| `audit_max_entries` | `500` | Entries kept per user. |
| `audit_max_days` | `180` | Age at which an entry is discarded. |
| `audit_sinks` | `('plugin',)` | Destinations, in order. |

The log is bounded per user and purged on write, so it cannot grow without limit
and there is no cron job to forget to install.

```{warning}
Enabling `audit_record_pii` stores personal data. Under the GDPR and the LGPD
that is a processing decision with consequences: a lawful basis, a retention
period you can justify, and an answer for a subject access request. The default
is off so the decision is one you make rather than one you inherit.
```

## Sinks

A site records to every destination `audit_sinks` names, in the order it names
them. Three ship.

| Sink | Writes to | Needs | Readable back? |
|---|---|---|---|
| `plugin` | The bounded per-user store inside the PAS plugin | nothing | yes |
| `log` | One line per event on the `pas.plugins.identity.audit` logger | nothing | **no** |
| `sql` | A row per event in a relational database | the `[sql]` extra and `IDENTITY_AUDIT_DSN` | yes |

Every destination listed gets every event. One that fails, or whose extra has
been uninstalled since it was configured, is logged and stepped over rather than
allowed to fail the sign-in it was auditing.

```{note}
The setting is a `Choice` over the sinks registered on the site, so a name that
does not exist cannot be stored. Installing an extra is what makes its sink
choosable; naming it is what starts recording to it.
```

### Writing and reading are two interfaces

| Interface | Method | Promised by |
|---|---|---|
| `IAuditSink` | `record` | every destination |
| `IAuditSource` | `entries` | only a destination that can answer for what it holds |

The `log` sink provides the first and not the second: a log file is somewhere
records go, not somewhere a Plone site can query. It has no `entries` at all,
rather than one returning an empty list every caller would read as nothing having
happened.

Reads answer from the **first configured sink that provides `IAuditSource`**. So
the order in `audit_sinks` decides which store the control panel and `@audit-log`
show, and a site recording to both a database and the plugin log chooses by
listing one first.

### Writing your own

Register a named utility. Provide `IAuditSource` as well if your destination can
answer for what it holds.

```xml
<utility
    name="syslog"
    factory=".sinks.SyslogAuditSink"
    provides="pas.plugins.identity.core.interfaces.IAuditSink"
    />
```

Then add `syslog` to `audit_sinks`. Registering the utility installs it; naming
it in the setting starts using it.

Recording is driven by events, so a sink sees everything any code fires,
including yours.

## Related

- {doc}`/how-to-guides/read-the-audit-log`—querying it
- {doc}`events`—what fires these entries
- {doc}`settings`—the four records above
- {doc}`endpoints`—`@audit-log`
