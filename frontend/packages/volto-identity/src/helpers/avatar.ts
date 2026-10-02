/**
 * Standing in for a portrait nobody uploaded, with this project's palette.
 *
 * The drawing rules live in `identity-core`. This module supplies the one
 * thing they need from Volto: the palette a project configured as
 * `config.settings.identity.avatarColors`.
 * @module helpers/avatar
 */
import config from '@plone/volto/registry';
import {
  colorFor as colorFromPalette,
  paletteOrDefault,
} from '@plone-collective/identity-core';

export {
  DEFAULT_AVATAR_COLORS,
  initialsFor,
} from '@plone-collective/identity-core';

/**
 * Return the palette initials are drawn on.
 *
 * @returns The configured palette, or the shipped one.
 */
export function avatarColors(): readonly string[] {
  return paletteOrDefault(config.settings.identity?.avatarColors);
}

/**
 * Return the colour a user's initials are drawn on, from this project's palette.
 *
 * @param userid The canonical Plone userid.
 * @returns One of the colours of :func:`avatarColors`.
 */
export function colorFor(userid: string | undefined | null): string {
  return colorFromPalette(userid, avatarColors());
}
