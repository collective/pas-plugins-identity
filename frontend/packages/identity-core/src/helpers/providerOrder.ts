/**
 * The order of the providers control panel's list.
 *
 * Dragging a row changes where every provider sits, and the list shows the new
 * order before the backend has stored it. Both halves are plain functions over
 * ids, so neither depends on the drag library that calls them.
 * @module helpers/providerOrder
 */

/**
 * The provider ids after one has been dropped in another's place.
 *
 * @param ids Every provider's id, in the order the list shows them.
 * @param moved The id that was dragged.
 * @param target The id whose place it was dropped in, or `null` when it was
 *   dropped outside the list.
 * @returns The new order, or `null` when the drop changes nothing: dropped
 *   where it started, dropped outside the list, or naming an id the list does
 *   not have.
 */
export function movedIds(
  ids: string[],
  moved: string,
  target: string | null,
): string[] | null {
  const from = ids.indexOf(moved);
  const to = target === null ? -1 : ids.indexOf(target);
  if (from < 0 || to < 0 || from === to) {
    return null;
  }
  const next = [...ids];
  next.splice(from, 1);
  next.splice(to, 0, moved);
  return next;
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
