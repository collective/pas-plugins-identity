Pointed the users control panel's {guilabel}`Edit` action at a user's Profile, when they have one.

Volto's action opens a modal bound to `@userschema`, which writes through `portal_memberdata` — for a user whose fields live in a Profile that is the wrong form on the wrong store: it shows only the fields that schema names, nothing the Profile type added, and it edits a place nothing reads for that user. Edit is now a link to their Profile's own edit form. Everyone else is untouched: no `profile_url`, no change, so the site's own `admin` and every user on a site without the `[content]` extra still get the modal. @ericof

The shadowed components moved out of `src/customizations/` while this landed: `PersonalTools`, `Toolbar` and the new `RenderUsers` are components under `src/components/` with their tests and stories beside them, and each customization file is now the docstring saying why the shadowing exists plus a one-line re-export.
