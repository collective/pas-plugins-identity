/**
 * Conversion between the stored group map and the rows an editor shows.
 *
 * The mechanics are shared with the property map and live in
 * {@link module:helpers/rowmap}; what belongs here is only the names this
 * mapping's two halves go by.
 *
 * The provider side is free text: it is whatever the far end's directory
 * happens to call a group, which this site cannot enumerate. The local side
 * is a pick from this site's groups, served by the backend, and the API
 * refuses a group that does not exist. Only a profile's import may name one,
 * because it may ship a map before the group it points at.
 * @module helpers/groupmap
 */

import { rowConverters } from './rowmap';

/** One row of the group mapping editor. */
export interface GroupMapRow {
  '@id': string;
  group: string;
  local: string;
}

const converters = rowConverters<GroupMapRow>('group', 'local');

/**
 * Turn a stored group map into editor rows.
 *
 * @param map Provider-side group name to local group id.
 * @returns One row per entry, in the map's own order.
 */
export function toGroupRows(
  map: Record<string, string> | undefined,
): GroupMapRow[] {
  return converters.toRows(map);
}

/**
 * Turn editor rows back into a stored group map.
 *
 * @param rows Rows from the editor.
 * @returns Provider-side group name to local group id.
 */
export function fromGroupRows(
  rows: GroupMapRow[] | undefined,
): Record<string, string> {
  return converters.fromRows(rows);
}
