/**
 * What this add-on's blocks store.
 * @module types/blocks
 */

/** What a sign-in block stores, as its sidebar edits it. */
export interface SignInBlockData {
  '@type': string;
  /**
   * The welcome message, as plain text.
   *
   * `{username}` and `{fullname}` are replaced with the signed-in user's.
   * Left out, the block uses its translated default.
   */
  greeting?: string;
  /** Whether to link to the user's Profile. Left out means shown. */
  showProfile?: boolean;
  /** Whether to show their preferred address. Left out means shown. */
  showEmail?: boolean;
  /** Whether to name what they signed in with. Left out means shown. */
  showProvider?: boolean;
  /** Whether to say when they last signed in. Left out means shown. */
  showLastLogin?: boolean;
  /** In the editor only: show what an anonymous visitor sees instead. */
  previewAnonymous?: boolean;
}
