---
myst:
  html_meta:
    "description": "Run a site with pas.plugins.identity: troubleshoot sign-in, read the audit log, review accounts, and move principals."
    "property=og:description": "Run a site with pas.plugins.identity: troubleshoot sign-in, read the audit log, review accounts, and move principals."
    "property=og:title": "Operate a site"
---

# Operate a site

Keep a running site healthy, and find out what happened when it was not.

| Guide | Does |
|---|---|
| {doc}`troubleshoot` | Finds the cause of a failed sign-in, by symptom |
| {doc}`read-the-audit-log` | Queries the audit log, tunes its retention, and sends entries to a SIEM |
| {doc}`review-a-user-account` | Shows which providers a user signs in with, when they last authenticated, and which of their addresses are verified |
| {doc}`enable-back-channel-logout` | Lets a provider end somebody's sessions here when they sign out there |
| {doc}`export-and-import-principals` | Moves users, groups, and identities between sites, as JSON |

## Related

- {doc}`/reference/audit-log`—every audit event and its fields
- {doc}`/reference/settings`—every setting, and where it lives

```{toctree}
:maxdepth: 1
:hidden: true

troubleshoot
read-the-audit-log
review-a-user-account
enable-back-channel-logout
export-and-import-principals
```
