Added an optional behavior keeping a user's password on their own content object, off by default.

Without it a new user's password goes to `source_users`, which is where Plone has always kept one. Turning it on gives a site whose users are content a single object per person holding everything about them, and makes Profile workflow into account suspension: a `deactivated` Profile stops authenticating, which `source_users` cannot do at all.

The hash is an annotation, not a Dexterity field. A field is serialized by `plone.restapi`, exported by GenericSetup, indexable, and snapshotted by versioning — four separate paths that each fail by disclosing the credential, and each of which would have to be remembered independently. An annotation is invisible to all four without anything being excluded anywhere. Hashing is `AccessControl.AuthEncoding`, so the stored form is one the rest of the stack already understands. Copying a Profile clears it, because copy and paste is a normal thing to do to content and must not hand the copy somebody else's credential.

Core does the authenticating, through a new `ICredentialStorage` contract the behavior provides. The `[content]` layer serves properties, enumeration and groups and never becomes a way to log in — the plugin that authenticates a userid is the one `@users` reports as its source, and an optional property store must not change a site's answer to where an account came from.

Nothing is migrated. A user whose credential is already in `source_users` keeps it, and turning this on changes where the *next* password is written rather than moving existing ones behind an operator's back. @ericof
