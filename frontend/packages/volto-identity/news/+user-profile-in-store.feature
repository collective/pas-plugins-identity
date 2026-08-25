Kept the signed-in user in the store, and added a "My profile" entry to the user menu pointing at their Profile.

Volto fetches the current user only when the personal-tools menu opens, and clears it around itself, so nothing outside that menu could rely on knowing who is signed in. A component mounted on every route now reads `@users/<userid>` once per user — the same endpoint Plone already serves, carrying the `identities`, `source` and `profile_url` this package's serializer adds to it.

The menu entry appears only where it leads somewhere: on a site running the `[profile]` layer, for a user first login has minted a Profile for. It sits beside Volto's own "Profile" link rather than replacing it — that one opens `/personal-information`, the form for editing your own member fields, which is a different thing from the Profile content object this add-on files you under. @ericof
