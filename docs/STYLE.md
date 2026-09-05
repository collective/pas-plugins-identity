# Documentation style

House rules for `docs/docs/`. They describe what the pages already do, so a new
page that follows them will not look like a visitor.

This file is a working document and is not published.

## Diátaxis, and picking the right quadrant

Every page belongs to exactly one of four directories, and the directory is a
promise about what the page does.

| Directory | Does | Never |
|---|---|---|
| `tutorials/` | Walks a beginner through a working result, start to finish | Offers choices, or explains why |
| `how-to-guides/` | Gets a competent reader to one outcome | Teaches, or catalogues options |
| `reference/` | Describes the machinery, exhaustively | Argues, persuades, or instructs |
| `concepts/` | Explains why it is built this way | Tells anybody what to type |

If a page is doing two of those, it is two pages.

## The rules that are not negotiable

1. **The code is the source of truth.** Every factual claim comes from reading
   the source, not from memory, not from a sibling page, and not from what the
   provider's own documentation says. Where a page states something a reader
   might want to check, cite the file it came from in an HTML comment:

   ```markdown
   <!-- source: backend/src/pas/plugins/identity/core/drivers/settings.py -->
   ```

   Put the comment under the heading of the section it supports, not at the top
   of the page.

2. **No "should" language.** "This should work", "it should be possible",
   "you should see" are all a way of writing something down without having
   checked it. Either it does, and you say so, or you have not run it, and you
   say *that*.

3. **Rationale lives in `concepts/`.** A reference page that starts explaining
   why is leaking. Move the paragraph, link to it, and leave the fact behind.

4. **Every page ends with `## Related` or `## Next steps`.** A reader who
   finished a page and has nowhere to go has been dropped.

5. **Diagrams are text.** Mermaid, in a `{mermaid}` block. No images of
   diagrams, ever, because nobody can fix a typo in a PNG.

6. **Screenshots are generated.** Never hand-captured. See
   `docs/screenshots/README.md`. A page that references a screenshot that does
   not exist yet gets a placeholder from `scripts/generate_placeholders.py`.

## Shape, per quadrant

### How-to guides

- Numbered, imperative steps. "Open the control panel", not "you can open the
  control panel".
- One outcome per guide, named in the first sentence.
- A `## Verify` section at the end, saying what the reader should be able to see.
- Provider recipes additionally carry `## Known quirks`.

### Reference

- Tables, not prose, wherever the content is a set of things with the same
  shape: fields, settings, endpoints, events, states.
- A definition list is a table that has not been written yet. Convert it.
- Exhaustive beats readable. If a schema has twelve fields, the table has twelve
  rows.

### Concepts

- Prose. Headings that make a claim (`Membership lives on the member`), not
  headings that name a topic (`Membership`).
- May be argued. This is the only place that may.

### Tutorials

- One narrative, no branches, no "if you prefer".
- State what the reader will see, including harmless noise they would otherwise
  worry about.
- End with `## What you built`.

## Mechanics

| Thing | Rule |
|---|---|
| Em dash | `—`, **unspaced**. `Microsoft.Dashes` rejects a spaced one. |
| Type names in tables | In backticks: `` `Bool` ``, not `Bool`. Vale reads the bare word as a misspelling, and the backticks are more correct anyway. |
| Cross-references | MyST roles: `` {doc}`/reference/settings` ``. Never a bare markdown link to another page. |
| UI labels | `` {guilabel}`Save` ``. Menu paths: `` {menuselection}`Site Setup --> Identity` ``. |
| Anchors | `(kebab-case-label)=` above the heading, only where something links to it. |
| Front matter | Every page has `html_meta` with `description`, `property=og:description` and `property=og:title`. |
| Nested fences | Use four backticks outside, three inside. A three-inside-three swallows the rest of the page. |
| Line length | Wrap at 80 where you are writing new prose. Do not reflow a file you are only patching. |

## Vale

`make vale` must exit clean. Warnings and suggestions are advisory; **errors are
not**.

When Vale rejects a word:

1. **Reword first.** Most `Microsoft.*` errors are a sentence that reads better
   the other way round.
2. Add to `styles/config/vocabularies/Plone/accept.txt` only for genuine
   technical vocabulary — a class name, a protocol term, a Plone-specific word.
   Entries are regular expressions, so `reindex(es|ed|ing)?` covers a family.
3. Never widen `.vale.ini` to silence a rule. The one exception in there is
   `TokenIgnores` for MyST anchor targets, which are markup rather than prose.

Vale does not read inside MyST directive blocks, so a `{note}` is unchecked. Do
not use that as a hiding place.

## Building

| Command | Does |
|---|---|
| `make -C docs html` | Build once |
| `make -C docs livehtml` | Serve on <http://127.0.0.1:8050> with live reload |
| `make docs-build` | Build with `-W`, which is what CI runs |
| `make -C docs vale` | Style check |
| `make -C docs linkcheck` | External links |

A build that emits a warning fails CI. After renaming or deleting a page, remove
`docs/_build/doctrees` before trusting a clean result: stale doctrees report
duplicate labels that no longer exist, and hide real ones.
