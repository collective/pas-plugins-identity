Moved provider avatar syncing into core, so it works without the `[profile]` layer. Portraits go to `portal_memberdata` -- the same place a portrait uploaded through user preferences goes -- and always did: the Dexterity `Profile` type has no image field, so nothing about this was ever specific to that layer. It only lived there.

The fetch now happens on sign-in rather than through the profile subscriber, and the change detection comes from the identity record's own claims snapshot instead of state kept on a Profile: the avatar is fetched when the provider changes the URL, not on every login, and a URL that failed is not retried until a different one arrives. Every guard is unchanged -- HTTPS only, short timeout, size capped off the stream, content type checked, failures swallowed -- and it is still **off by default**, for the reason in that module's docstring: `picture_url` is a claim, so enabling it makes the login path fetch an address the user may control.

The registry record moves with it, from `pas.plugins.identity.profile_sync_portraits` to `pas.plugins.identity.sync_portraits`, since core cannot read a record only an optional layer installs.

A property map that names `portrait` no longer writes to it. A portrait is an image in member storage rather than a property, so writing a claim through `setMemberProperties` would have stored the URL string itself. @ericof
