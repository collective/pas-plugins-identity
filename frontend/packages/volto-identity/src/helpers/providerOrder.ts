/**
 * The order of the providers control panel's list.
 *
 * Dragging a row changes where every provider sits, and the list shows the new
 * order before the backend has stored it. Both halves are plain functions over
 * ids, so neither depends on the drag code that calls them.
 * @module helpers/providerOrder
 */
import type { DropPosition } from './orderedList';

/**
 * The provider ids after some have been dropped next to another.
 *
 * Shaped like the reorder event of react-aria's `useDragAndDrop`: the ids
 * dragged, the id they were dropped next to, and which side of it.
 *
 * @param ids Every provider's id, in the order the list shows them.
 * @param moved The ids dragged, in any order; they keep the list's order.
 * @param target The id they were dropped next to.
 * @param position Which side of the target. `on` is read as `before`.
 * @returns The new order, or `null` when the drop changes nothing: dropped
 *   where it started, dropped on itself, or naming an id the list does not
 *   have.
 */
export function reorderedIds(
  ids: string[],
  moved: string[],
  target: string,
  position: DropPosition,
): string[] | null {
  const dragged = new Set(moved);
  if (dragged.has(target) || !ids.includes(target)) {
    return null;
  }
  const movedIds = ids.filter((id) => dragged.has(id));
  if (!movedIds.length) {
    return null;
  }
  const remaining = ids.filter((id) => !dragged.has(id));
  const at = remaining.indexOf(target) + (position === 'after' ? 1 : 0);
  const next = [...remaining.slice(0, at), ...movedIds, ...remaining.slice(at)];
  return next.every((id, index) => id === ids[index]) ? null : next;
}

/**
 * The providers, in an order taken earlier.
 *
 * @param providers The providers as last listed.
 * @param order Provider ids, in the order to show them.
 * @returns The providers the order names, in its order, then any it does not
 *   name in the order they were listed: a provider added since the order was
 *   taken is shown rather than lost. An id naming no provider is skipped.
 */
export function inOrder<T extends { id: string }>(
  providers: T[],
  order: string[],
): T[] {
  const byId = new Map(providers.map((provider) => [provider.id, provider]));
  const named = [...new Set(order)]
    .map((id) => byId.get(id))
    .filter((provider): provider is T => provider !== undefined);
  const rest = providers.filter((provider) => !order.includes(provider.id));
  return [...named, ...rest];
}
