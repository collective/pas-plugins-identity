`UserProfile` and `UserGroup` keep a version history.

A Profile is the record of a person, and "who changed this, to what, and when" is a question sites ask about people more often than about pages. Both types now carry the `plone.versioning` behavior and a `repositorytool.xml` policy — two independent pieces of configuration, only one of which is visible on the FTI. A type with the behavior and no policy entry looks versioned everywhere a person can see and keeps no history at all, so the tests assert `getVersionableContentTypes()` rather than the behavior list.

**This reopened a question the package had already answered, and the answer had to change.** The optional password behavior keeps its hash in an annotation rather than in a Dexterity field, and three places in the source explained why in the same terms: a field is serialized by `plone.restapi`, exported by GenericSetup, indexable, and snapshotted by versioning, so an annotation is invisible to all four.

Three of those four are true. CMFEditions deep-copies `__annotations__` into a snapshot, so a versionable Profile would have carried every superseded hash in `portal_repository` — a password change that no longer retired the old credential, accumulating somewhere nobody looks, with nothing to say so. That is worse than the field would have been, because a field at least announces itself.

So the install handler registers a CMFEditions modifier that keeps the credential out of the snapshot on the way in and restores the working copy's on the way out. Skipping alone would have meant reverting a Profile silently cleared its password, which is an account lockout decided in version history. The uninstall handler removes the modifier again.

The tests include the mutation: switching the modifier off and proving the old hash comes back, because a regression test that passes with the fix removed is not evidence of anything. @ericof
