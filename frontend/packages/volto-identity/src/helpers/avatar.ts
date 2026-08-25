/**
 * Standing in for a portrait nobody uploaded.
 *
 * Volto draws a camera icon when a user has no portrait, which is the same
 * picture for everybody: it says "no image here" rather than "this is you".
 * Initials on a colour derived from the userid are recognisable at a glance
 * and stay put -- the same person gets the same colour on every visit, on
 * every device, without anything being stored.
 * @module helpers/avatar
 */

/**
 * The palette initials are drawn on.
 *
 * Chosen for contrast against white text rather than for variety: every one
 * of these clears WCAG AA at the size the avatar renders. Ten is enough that
 * two people in a room rarely collide and few enough that each stays
 * distinct -- a larger palette mostly adds colours that look alike.
 */
export const AVATAR_COLORS = [
  '#0083be',
  '#005d7a',
  '#8b2f8b',
  '#a13d63',
  '#b5451b',
  '#7a5c00',
  '#2d6a4f',
  '#1b5e8b',
  '#5f3dc4',
  '#8a3324',
] as const;

/**
 * Return the initials to draw for a user.
 *
 * @param name The user's full name, or their login when they have no name.
 * @returns One or two uppercase letters, or an empty string when the name
 *   carries no letter at all.
 */
export function initialsFor(name: string | undefined | null): string {
  const words = (name ?? '')
    .trim()
    .split(/\s+/)
    .filter((word) => /\p{L}/u.test(word));
  if (words.length === 0) {
    return '';
  }
  // First and last rather than the first two: "Érico de Andrei" reads as ÉA,
  // and a middle name should not push the surname out.
  const letters =
    words.length === 1
      ? [...words[0]].filter((c) => /\p{L}/u.test(c)).slice(0, 2)
      : [firstLetter(words[0]), firstLetter(words[words.length - 1])];
  return letters.join('').toLocaleUpperCase();
}

/**
 * Return the first letter of a word, skipping anything that is not one.
 *
 * @param word The word.
 * @returns The letter, or an empty string.
 */
function firstLetter(word: string): string {
  return [...word].find((c) => /\p{L}/u.test(c)) ?? '';
}

/**
 * Return the colour a user's initials are drawn on.
 *
 * Derived from the userid rather than the name, so somebody correcting the
 * spelling of their own name does not change colour.
 *
 * @param userid The canonical Plone userid.
 * @returns One of :data:`AVATAR_COLORS`.
 */
export function colorFor(userid: string | undefined | null): string {
  const seed = userid ?? '';
  let hash = 0;
  for (const char of seed) {
    // Ordinary string hash. It needs to be stable and spread, not secure --
    // this picks a colour, and knowing how it picks reveals nothing.
    hash = (hash * 31 + char.codePointAt(0)!) % 0xffffffff;
  }
  return AVATAR_COLORS[hash % AVATAR_COLORS.length];
}
