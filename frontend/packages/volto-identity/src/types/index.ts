/**
 * The package's types, in two halves.
 *
 * `api.ts`
 *     What each endpoint answers with. One interface per payload, named for
 *     the thing it describes rather than for the route.
 *
 * `content.ts`
 *     The two content types as Volto receives them, tied to `@plone/types`
 *     where they agree with an ordinary Plone object and documenting each
 *     place they do not.
 *
 * This file re-exports both, so `from '../types'` keeps resolving for
 * everything that already imports it.
 * @module types
 */

export * from './api';
export * from './content';
