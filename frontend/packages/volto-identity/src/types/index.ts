/**
 * The package's types.
 *
 * The payloads of each endpoint and what the blocks store live in
 * `@plone-collective/identity-core`, which both frontends share. This file
 * re-exports them, beside the two parts that are Volto's own.
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
 * Re-exporting everything keeps `from '../types'` resolving for everything
 * that already imports it.
 * @module types
 */

export type * from '@plone-collective/identity-core';
export * from './content';
export * from './settings';
