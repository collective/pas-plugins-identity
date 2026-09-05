---
myst:
  html_meta:
    "description": "Query the authentication audit log, tune its retention, and send entries to a SIEM."
    "property=og:description": "Query the authentication audit log, tune its retention, and send entries to a SIEM."
    "property=og:title": "How to read the audit log"
---

(how-to-read-the-audit-log)=

# How to read the audit log

This guide shows you how to query the audit log, change what it keeps, and send its entries somewhere else.

For the full list of endpoints, settings, and recorded fields, see {doc}`/reference/audit-log`.

## Read your own entries

```text
GET @audit-log
```

Any authenticated user can do this, and it returns only their own entries.

## Read somebody else's entries

```text
GET @audit-log?userid=<id>
```

This requires the `Manage portal` permission.

## Investigate an attack

```text
GET @audit-log?scope=site
```

This returns everything, including the refusals that could not be attributed to anybody.
It requires `Manage portal`.

Use it when you are looking at the site rather than at a person.
It is the only view that shows refusals with no user id attached, which is where a credential-stuffing run shows up.

## Diagnose a failed sign-in

Read the log before you read the source.

Failures are recorded as carefully as successes.
An unknown identity, a sign-in denied by a provider's allowed-groups gate, and a link collision are three different entries, and telling them apart is most of what the log is for.

## Turn on IP and user-agent recording

IP address and user agent are not recorded unless you switch them on, with the `audit_record_pii` registry setting.

```{warning}
Enabling `audit_record_pii` stores personal data.
Under the GDPR and the LGPD that is a processing decision with consequences: a lawful basis, a retention period you can justify, and an answer for a subject access request.
The default is off so that the decision is one you make rather than one you inherit.
```

## Change how much is kept

Two registry settings bound the log:

-   `audit_max_entries`, 500 per user by default
-   `audit_max_days`, 180 by default

The log is bounded per user and purged on write, so it cannot grow without limit and there is no cron job to forget to install.

## Send entries to a SIEM

A site records to every destination its `audit_sinks` setting names, and ships three: `plugin` for the bounded log inside the plugin, `log` for one line per event, and `sql` for a row per event in a relational database.
Adding a destination does not replace the others.

To send entries somewhere else again, register a *named* `IAuditSink` utility and add its name to the setting:

```xml
<utility
    name="syslog"
    factory=".sinks.SyslogAuditSink"
    provides="pas.plugins.identity.core.interfaces.IAuditSink"
    />
```

Provide `IAuditSource` too if your destination can be read back; a sink that only writes is fine, and the control panel then answers from whichever configured destination can.

Recording is driven by events, so your sink sees everything any code fires, including your own.
See {doc}`/reference/events`.
