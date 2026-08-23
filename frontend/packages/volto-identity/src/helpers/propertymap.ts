/**
 * Conversion between the stored property map and the rows an editor shows.
 *
 * The backend stores a mapping of claim path to user field, which is the
 * shape that reads well as a registry record. An editor cannot work in that
 * shape: a row the operator has just added has no claim yet, so it has no
 * key, and every unfinished row would collapse onto the same one.
 *
 * Rows therefore carry an `@id`. That is Volto's `ObjectListWidget`
 * contract -- it keys its drag list on `o['@id']` and renders nothing for a
 * row without one -- and it is what lets two unfinished rows coexist.
 * @module helpers/propertymap
 */

/** One row of the mapping editor. */
export interface PropertyMapRow {
  '@id': string;
  claim: string;
  field: string;
}

/**
 * Mint an id for a row.
 *
 * @returns A value unique among the rows on the page.
 */
function rowId(): string {
  const maybe = globalThis.crypto as { randomUUID?: () => string } | undefined;
  if (maybe?.randomUUID) {
    return maybe.randomUUID();
  }
  // Only reached on a runtime without webcrypto; uniqueness within one
  // editing session is all this needs.
  return `row-${Math.random().toString(36).slice(2)}`;
}

/**
 * Turn a stored map into editor rows.
 *
 * @param map Claim path to user field.
 * @returns One row per entry, in the map's own order.
 */
export function toRows(
  map: Record<string, string> | undefined,
): PropertyMapRow[] {
  return Object.entries(map ?? {}).map(([claim, field]) => ({
    '@id': rowId(),
    claim,
    field,
  }));
}

/**
 * Return a blank row, as the editor's Add button produces.
 *
 * @returns An empty row with its own id.
 */
export function blankRow(): PropertyMapRow {
  return { '@id': rowId(), claim: '', field: '' };
}

/**
 * Turn editor rows back into a stored map.
 *
 * Rows missing either half are dropped: they are a row the operator started
 * and has not finished, not a mapping. This is why rows are held as state
 * rather than derived from the map -- a blank row must survive on screen
 * while being absent from what gets saved. A repeated claim keeps the last
 * row, which is what the object it becomes would do anyway.
 *
 * @param rows Rows from the editor.
 * @returns Claim path to user field.
 */
export function fromRows(
  rows: PropertyMapRow[] | undefined,
): Record<string, string> {
  const map: Record<string, string> = {};
  for (const row of rows ?? []) {
    const claim = (row?.claim ?? '').trim();
    const field = (row?.field ?? '').trim();
    if (claim && field) {
      map[claim] = field;
    }
  }
  return map;
}
