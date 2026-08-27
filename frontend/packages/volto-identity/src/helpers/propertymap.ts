/**
 * Conversion between the stored property map and the rows an editor shows.
 *
 * The mechanics are shared with the group map and live in
 * {@link module:helpers/rowmap}; what belongs here is only the names this
 * mapping's two halves go by.
 * @module helpers/propertymap
 */

import { rowConverters } from './rowmap';

/** One row of the mapping editor. */
export interface PropertyMapRow {
  '@id': string;
  claim: string;
  field: string;
}

const converters = rowConverters<PropertyMapRow>('claim', 'field');

/**
 * Turn a stored map into editor rows.
 *
 * @param map Claim path to user field.
 * @returns One row per entry, in the map's own order.
 */
export function toRows(
  map: Record<string, string> | undefined,
): PropertyMapRow[] {
  return converters.toRows(map);
}

/**
 * Turn editor rows back into a stored map.
 *
 * @param rows Rows from the editor.
 * @returns Claim path to user field.
 */
export function fromRows(
  rows: PropertyMapRow[] | undefined,
): Record<string, string> {
  return converters.fromRows(rows);
}
