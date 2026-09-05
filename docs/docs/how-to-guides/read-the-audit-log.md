---
myst:
  html_meta:
    "description": "Query the authentication audit log, tune its retention, and send entries to a SIEM."
    "property=og:description": "Query the authentication audit log, tune its retention, and send entries to a SIEM."
    "property=og:title": "How to read the audit log"
---

(how-to-read-the-audit-log)=

# How to read the audit log

Query the audit log, change what it keeps, and send its entries somewhere else.

For every endpoint, setting and recorded field, see {doc}`/reference/audit-log`.

## Read entries

| Goal | Request | Requires |
|---|---|---|
| Your own entries | `GET @audit-log` | any authenticated user |
| One person's entries | `GET @audit-log?userid=<id>` | `Manage portal` |
| Everything, including unattributed refusals | `GET @audit-log?scope=site` | `Manage portal` |

Use `scope=site` when you are looking at the site rather than at a person. It is
the only view that shows refusals with no user id attached, which is where a
credential-stuffing run shows up.

## Diagnose a failed sign-in

1. Read the log before you read the source. Failures are recorded as carefully as
   successes.
2. Find the entry's event name.
3. Look it up in {doc}`troubleshoot`, which is organized by exactly these.

An unknown identity, a sign-in denied by a group restriction, and a link
collision are three different entries, and telling them apart is most of what the
log is for.

## Turn on IP and user-agent recording

IP address and user agent are not recorded unless you switch them on.

1. Open the **Identity providers** control panel.
2. Switch on {guilabel}`Record personally identifiable information`, the
   `audit_record_pii` registry setting.

```{warning}
Enabling `audit_record_pii` stores personal data.

Under the GDPR and the LGPD that is a processing decision with consequences: a
lawful basis, a retention period you can justify, and an answer for a subject
access request. The default is off so that the decision is one you make rather
than one you inherit.
```

## Change how much is kept

Two registry settings bound the log:

| Setting | Default |
|---|---|
| `audit_max_entries` | 500 per user |
| `audit_max_days` | 180 |

The log is bounded per user and purged on write, so it cannot grow without limit
and there is no cron job to forget to install.

## Send entries somewhere else

A site records to every destination its `audit_sinks` setting names, in order.
Three ship:

| Sink | Readable | What it does |
|---|---|---|
| `plugin` | yes | The bounded log inside the plugin. The default. |
| `log` | **no** | One line per event to the `pas.plugins.identity.audit` logger. |
| `sql` | yes | A row per event in a relational database. Needs the `[sql]` extra. |

Adding a destination does not replace the others.

### Add the log sink

1. Open the **Identity providers** control panel.
2. Add `log` to {guilabel}`Audit sinks`, keeping `plugin`.
3. Save.

Events now appear on the `pas.plugins.identity.audit` logger as well, one line
each, at info for a success and warning for a refusal. Route that logger wherever
your log shipping already goes.

### Add the SQL sink

1. Install the `[sql]` extra and restart.
2. Set `IDENTITY_AUDIT_DSN` in the backend's environment.
3. Add `sql` to {guilabel}`Audit sinks`.

The DSN is an environment variable rather than a registry setting because it
carries a password, and the registry is exported by GenericSetup and readable
through the control panel.

### Write your own

Register a **named** `IAuditSink` utility and add its name to the setting:

```xml
<utility
    name="syslog"
    factory=".sinks.SyslogAuditSink"
    provides="pas.plugins.identity.core.interfaces.IAuditSink"
    />
```

Provide `IAuditSource` too if your destination can be read back. A sink that only
writes is fine: reads go to the first configured sink that can answer them, and
when none can, `@audit-log` says so rather than returning an empty list that
reads as nothing having happened.

Recording is driven by events, so your sink sees everything any code fires,
including your own. See {doc}`/reference/events`.

## Verify

- `GET @audit-log` returns your own entries.
- After a sign-in, an `authenticated` entry appears.
- After adding a sink, the same event appears in both destinations.

A sink whose extra was uninstalled since it was configured is logged and stepped
over rather than allowed to fail the sign-in it was auditing.

## Next steps

- {doc}`/reference/audit-log`—every event name and field
- {doc}`troubleshoot`—the symptom-by-symptom table
- {doc}`/concepts/threat-model`—what the log is and is not evidence of
