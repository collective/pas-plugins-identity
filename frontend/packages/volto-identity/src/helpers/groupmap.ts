/**
 * Conversion between the stored group map and the rows an editor shows.
 *
 * The mechanics are shared with the property map and live in
 * {@link module:helpers/rowmap}; what belongs here is only the names this
 * mapping's two halves go by.
 *
 * The halves are not symmetric, and the widget reflects that. The provider
 * side is free text, because it is whatever the far end's directory happens
 * to call a group and this site has no way to enumerate it. The local side is
 * a vocabulary, because a group that does not exist here grants nothing --
 * the backend skips it and logs -- and a picker is how that stops being a
 * typo nobody notices.
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
