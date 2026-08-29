`GET @user-account/<userid>` answers two questions an administrator could not ask before.

*Which providers has this person configured?* `@users/<id>` does carry `identities`, but as bare provider ids and subjects. This names each provider, carries its icon and colours so a panel can show the same button the person signs in with, and reports whether the provider is still configured and still enabled -- three states rather than two, because an identity against a provider somebody has since turned off looks like a broken login and reads like nothing.

*When did this person last authenticate?* Nothing in Plone records it. This package's audit log does, for every route in -- a federated sign-in, a magic link and an ordinary password login all record `authenticated` -- so the answer existed and had never been reachable per user. The endpoint reports it alongside the most recent events, so a panel can show how somebody got in and not only when.

It also carries the profile's addresses and which of them this site has verified, because a verified address is what `auto_link_by_email` attaches a new provider account to: an administrator looking at one is looking at the other.

One user at a time, deliberately. The audit log is bounded per user rather than globally, so folding either answer into the `@users` listing would read one bounded log per row on every page of it. `Manage users` throughout, with one exception: a caller asking about themselves, since the same facts are already theirs through `@identities` and `@audit-log` and refusing here would only mean the frontend needing two code paths to draw one panel.
