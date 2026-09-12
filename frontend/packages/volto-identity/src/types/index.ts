/**
 * The package's types, in four parts.
 *
 * `api.ts`
 *     What each endpoint answers with. One interface per payload, named for
 *     the thing it describes rather than for the route.
 *
 * `blocks.ts`
 *     What the add-on's blocks store.
 *
 * `content.ts`
 *     The two content types as Volto receives them, tied to `@plone/types`
 *     where they agree with an ordinary Plone object and documenting each
 *     place they do not.
 *
 * `settings.ts`
 *     The add-on's own frontend settings, `config.settings.identity`, and the
 *     `@plone/types` augmentation that puts them there.
 *
 * This file re-exports all four, so `from '../types'` keeps resolving for
 * everything that already imports it.
 * @module types
 */

export * from './api';
export * from './blocks';
export * from './content';
export * from './settings';
