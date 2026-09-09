/**
 * Conversion between the stored group map and the rows an editor shows.
 *
 * The mechanics are shared with the property map and live in
 * {@link module:helpers/rowmap}; what belongs here is only the names this
 * mapping's two halves go by.
 *
 * Both halves are free text, and only one of them has to be. The provider
 * side is whatever the far end's directory happens to call a group, which
 * this site cannot enumerate. The local side names a group here, and a row
 * naming one that does not exist grants nothing -- the backend skips it and
 * logs -- but a profile may legitimately ship a map before the group it
 * points at, so the field stays text rather than a `Choice` that would refuse
 * the import. Compare the property map, whose target is four fields this
 * package knows by name and is a picker.
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
