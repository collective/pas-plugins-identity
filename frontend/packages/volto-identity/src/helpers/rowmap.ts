/**
 * Conversion between a stored `{key: value}` map and the rows an editor shows.
 *
 * The backend stores mappings as objects, which is the shape that reads well
 * as a registry record. An editor cannot work in that shape: a row the
 * operator has just added has no key yet, so every unfinished row would
 * collapse onto the same one.
 *
 * Rows therefore carry an `@id`. That is Volto's `ObjectListWidget`
 * contract -- it keys its drag list on `o['@id']` and renders nothing for a
 * row without one -- and it is what lets two unfinished rows coexist.
 *
 * Two mappings use this: the property map, whose halves are a claim and a
 * user field, and the group map, whose halves are a provider group and a
 * local one. Only the field names differ, so the field names are the
 * parameter and everything else is shared.
 * @module helpers/rowmap
 */

/**
 * The least a row must be for the list widget to render it.
 *
 * The two halves are named by the caller, so they are not part of this type;
 * each mapping declares a row type of its own and passes it as `R` below.
 */
export interface MapRow {
  '@id': string;
}

/**
 * Mint an id for a row.
 *
 * @returns A value unique among the rows on the page.
 */
export function rowId(): string {
  const maybe = globalThis.crypto as { randomUUID?: () => string } | undefined;
  if (maybe?.randomUUID) {
    return maybe.randomUUID();
  }
  // Only reached on a runtime without webcrypto; uniqueness within one
  // editing session is all this needs.
  return `row-${Math.random().toString(36).slice(2)}`;
}

/** Converters between one stored map and its editor rows. */
export interface RowConverters<R extends MapRow> {
  toRows: (map: Record<string, string> | undefined) => R[];
  fromRows: (rows: R[] | undefined) => Record<string, string>;
}

/**
 * Build the converters for a mapping whose halves are named this way.
 *
 * The row type is the caller's, and the two casts below are where the
 * dynamic field names are reconciled with it. They are contained here on
 * purpose: each mapping's own module then has a fully typed pair of
 * functions and no cast of its own.
 *
 * @param keyField Name of the row field holding the map's key.
 * @param valueField Name of the row field holding the map's value.
 * @returns The pair of converters.
 */
export function rowConverters<R extends MapRow>(
  keyField: string,
  valueField: string,
): RowConverters<R> {
  return {
    /**
     * Turn a stored map into editor rows.
     *
     * @param map The stored mapping.
     * @returns One row per entry, in the map's own order.
     */
    toRows(map) {
      return Object.entries(map ?? {}).map(
        ([key, value]) =>
          ({
            '@id': rowId(),
            [keyField]: key,
            [valueField]: value,
          }) as unknown as R,
      );
    },

    /**
     * Turn editor rows back into a stored map.
     *
     * Rows missing either half are dropped: they are a row the operator
     * started and has not finished, not a mapping. This is why rows are held
     * as state rather than derived from the map -- a blank row must survive
     * on screen while being absent from what gets saved. A repeated key keeps
     * the last row, which is what the object it becomes would do anyway.
     *
     * @param rows Rows from the editor.
     * @returns The stored mapping.
     */
    fromRows(rows) {
      const map: Record<string, string> = {};
      for (const row of rows ?? []) {
        const halves = row as unknown as Record<string, string | undefined>;
        const key = (halves?.[keyField] ?? '').trim();
        const value = (halves?.[valueField] ?? '').trim();
        if (key && value) {
          map[key] = value;
        }
      }
      return map;
    },
  };
}
