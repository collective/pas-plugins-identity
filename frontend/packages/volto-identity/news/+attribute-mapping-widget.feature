Added the attribute-mapping editor to the providers control panel, built on Volto's `ObjectListWidget` — its DataGridField equivalent — so the rows get drag reordering, add and remove, and schema-driven widgets for free.

The user-field column is a vocabulary rather than free text: it reads `pas.plugins.identity.UserFields` from the backend, which is the site's live member schema, so a field added in the **User Schema** control panel appears here with no frontend change. The claim column stays free text, because no vocabulary can know what a given provider calls its claims.

Rows are held as state rather than derived from the stored map. A row the operator has just added has no claim yet and is therefore not a mapping — deriving would make it vanish the instant it appeared. They also carry an `@id`, which is `ObjectListWidget`'s contract: it keys its drag list on that field and renders nothing at all, silently, for a row without one. @ericof
