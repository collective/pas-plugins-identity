/**
 * The types both frontends share, in two parts.
 *
 * `api.ts`
 *     What each endpoint answers with. One interface per payload, named for
 *     the thing it describes rather than for the route.
 *
 * `blocks.ts`
 *     What the add-on's blocks store.
 * @module types
 */

export * from './api';
export * from './blocks';
